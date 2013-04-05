import urllib, re, logging
from operator import itemgetter
from models import Invtypes, Invnames
from lxml import etree
from django.db import connections

url="http://api.eve-central.com/api/marketstat"
staticDB = 'eve_static'
logger = logging.getLogger(__name__)

invNames = Invnames.objects.using(staticDB)
invTypes = Invtypes.objects.using(staticDB)

def set_item_quantity(itemData, itemName, quantity):
	inc = 1
	if quantity:
		inc = quantity

	try:
		itemData.itemList[itemData.ship_name][itemName] += inc
	except:
		itemData.itemList[itemData.ship_name][itemName] = inc

def add_commas(foo):
	return "{0:,}".format(foo)

def parse_xml_fit(fit_data):
	class itemData:
		itemList = dict()
		ship_name = ""

	try:
		root = etree.fromstring(fit_data)
	except(etree.ParseError):
		# parse error, figure out how to pass that back
		return None

	for ship in root:
		itemData.ship_name = ship.attrib['name']
		itemData.itemList[itemData.ship_name] = dict()
		for fitting in ship:
			if fitting.tag != "description":
				if fitting.tag == "shipType":
					set_item_quantity(itemData, fitting.attrib['value'], None)
				elif fitting.tag == "hardware":
					if fitting.attrib['slot'] != "cargo":
						qty = None
						if fitting.attrib['slot'] == "drone bay":
							qty = int(fitting.attrib['qty'])
						set_item_quantity(itemData, fitting.attrib['type'], qty)

	return itemData.itemList

def parse_eft_fit(fit_data):
	class itemData:
		itemList = dict()
		ship_name = ""

	for line in fit_data.splitlines():
		try:
			if line[0] == "[":
				if not re.search("^\[empty", line):
					itemData.ship_name = line.rstrip().split(",")[1][1:-2]
					itemData.itemList[itemData.ship_name] = dict()
					set_item_quantity(itemData, line.rstrip().split(",")[0][1:], None)
			else:
				item = line.rstrip()
				if item:
					q = re.search(" x\d+$", item)
					if q:
						set_item_quantity(itemData, item[:q.start()], int(q.group(0)[2:]))
					else:
						set_item_quantity(itemData, item.split(",")[0], None)
		except:
			pass

	return itemData.itemList

def parse_fit(fit_data):
	if re.search("^\<\?xml", fit_data):
		return parse_xml_fit(fit_data)
	else:
		return parse_eft_fit(fit_data)

def get_slot(item):
	eve_static_cur = connections['eve_static'].cursor()
	eve_static_cur.execute("SELECT TRIM(effect.effectName) AS slot FROM invTypes AS type INNER JOIN dgmTypeEffects AS typeEffect ON type.typeID = typeEffect.typeID INNER JOIN dgmEffects AS effect ON typeEffect.effectID = effect.effectID WHERE effect.effectName IN ('loPower', 'medPower', 'hiPower', 'rigSlot', 'subSystem', 'targetAttack', 'massFactor', 'targetArmorRepair') AND type.typeName = %s;", [item])
	try:
		slot = eve_static_cur.fetchone()[0]
	except:
		return "Z Unknown"

	# slot mapping from the weirdness in the db to reality
	if slot == "loPower":
		slotname = "C Low Power"
	elif slot == "medPower":
		slotname = "B Medium Power"
	elif slot == "hiPower":
		slotname = "A High Power"
	elif slot == "rigSlot":
		slotname = "D Rig Slot"
	elif slot == "subSystem":
		slotname = "E Subsystem"
	elif slot == "targetAttack" or slot == "targetArmorRepair":
		slotname = "F Drone"
	elif slot == "massFactor":
		slotname = "G Hull"
	else:
		slotname = "Z Unknown"

	return slotname

def fetch_itemid(itemList):
	itemDict = dict()
	badItemList = dict()

	for ship in itemList:
		itemDict[ship] = dict()
		badItemList[ship] = set()
		for item in itemList[ship]:
			try:
				itemDict[ship][str(invTypes.get(typename=item).typeid)] = item
			# need to figure out why this doesn't work:
			# Exception Value:	global name 'DoesNotExist' is not defined
			#except(Invtypes.DoesNotExist):
			except:
				badItemList[ship].add(item)

	return itemDict, badItemList

def get_fit_price(form_data):
	if form_data['file']:
		fit_data = form_data['file'].read()
	else:
		if not form_data['fit']:
			return None, None, "No file uploaded and no data pasted!!!"
		fit_data = form_data['fit']

	systemID = invNames.get(itemname=form_data['system']).itemid
	itemList = parse_fit(fit_data)
	itemDict, badItemList = fetch_itemid(itemList)
	output = dict()

	for ship in itemDict:
		# It's easier to construct our own POST data than to use urlencode
		post_data="usesystem={0}&typeid={1}".format(str(systemID), "&typeid=".join(itemDict[ship]))
		url_data = "{0}/?{1}".format(url, post_data)
		#logger.debug("data url: {0}".format(url_data))
		#try:
		#	tree = etree.parse(url_data)
		#except(etree.XMLSyntaxError):
		#	logger.error("XML misformed or something?")
		#	return None

		f = urllib.urlopen(url_data)
		tree = etree.fromstring(f.read())
		f.close()

		output[ship] = list()
		buy_total = 0
		sell_total = 0

		for element in tree.iter():
			if element.tag == "type":
				itemName = itemDict[ship][element.attrib['id']]
				itemQuantity = itemList[ship][itemName]
				buy = float(element.xpath("buy/max")[0].text)
				sell = float(element.xpath("sell/min")[0].text)
				buy_subtotal = buy * itemQuantity
				sell_subtotal = sell * itemQuantity
				buy_total += buy_subtotal
				sell_total += sell_subtotal
				output[ship].append({'name': itemName, 'quantity': itemQuantity, 'slot': get_slot(itemName), 'buy': add_commas(buy), 'sell': add_commas(sell)})

		output[ship].sort(key=itemgetter('slot'))
		output[ship].append({'name': None, 'quantity': None, 'buy': add_commas(buy_total), 'sell': add_commas(sell_total)})

	#logger.debug("output: {0} badItemList: {1}".format(output, badItemList))
	return output, badItemList, None
