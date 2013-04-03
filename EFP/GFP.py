import urllib, re, logging
from models import Invtypes, Invnames
from lxml import etree

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

	logger.debug("parse_xml_fit(): itemData.itemList: {0}".format(itemData.itemList))
	return itemData.itemList

def parse_eft_fit(fit_data):
	class itemData:
		itemList = dict()
		ship_name = ""

	for line in fit_data.splitlines():
		try:
			if line[0] == "[":
				if not re.search("^\[empty", line):
					itemData.ship_name = line.rstrip().split(",")[1][1:]
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

	logger.debug("parse_eft_fit(): itemData.itemList: {0}".format(itemData.itemList))
	return itemData.itemList

def parse_fit(fit_data):
	if re.search("^\<\?xml", fit_data):
		return parse_xml_fit(fit_data)
	else:
		return parse_eft_fit(fit_data)

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

	logger.debug("fetch_itemid(): itemDict: {0} badItemList: {1}".format(itemDict, badItemList))
	return itemDict, badItemList

def get_fit_price(form_data):
	itemList = parse_fit(form_data['fit'])
	itemDict, badItemList = fetch_itemid(itemList)
	systemID = invNames.get(itemname=form_data['system']).itemid

	for ship in itemDict:
		# It's easier to construct our own POST data than to use urlencode
		post_data="usesystem={0}&typeid={1}".format(str(systemID), "&typeid=".join(itemDict[ship]))
		url_data = "{0}/?{1}".format(url, post_data)
		logger.debug("data url: {0}".format(url_data))
		#try:
		#	tree = etree.parse(url_data)
		#except(etree.XMLSyntaxError):
		#	logger.error("XML misformed or something?")
		#	return None

		f = urllib.urlopen(url_data)
		tree = etree.fromstring(f.read())
		f.close()

		output = dict()
		#output[ship] = dict()
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
				output[ship].append({'name': itemName, 'quantity': itemQuantity, 'buy': add_commas(buy), 'sell': add_commas(sell)})
			
		output[ship].append({'name': None, 'quantity': None, 'buy': add_commas(buy_total), 'sell': add_commas(sell_total)})

		#if badItemList[ship]:
		#	for i in badItemList[ship]:
		#		output[ship]['badItemList'].append(i)

	logger.debug("output: {0} badItemList: {1}".format(output, badItemList))
	return output, badItemList
