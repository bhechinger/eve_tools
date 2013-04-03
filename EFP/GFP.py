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
		itemData.itemList[itemName] += inc
	except:
		itemData.itemList[itemName] = inc

def add_commas(foo):
	return "{0:,}".format(foo)

def parse_xml_fit(fit_data):
	class itemData:
		itemList = dict()

	try:
		root = etree.fromstring(fit_data)
	except(etree.ParseError):
		# parse error, figure out how to pass that back
		return None

	for ship in root:
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

	for line in fit_data.splitlines():
		try:
			if line[0] == "[":
				if not re.search("^\[empty", line):
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

def fetch_itemid(itemList):
	itemDict = dict()
	badItemList = set()

	for item in itemList:
		try:
			itemDict[str(invTypes.get(typename=item).typeid)] = item
		# need to figure out why this doesn't work:
		# Exception Value:	global name 'DoesNotExist' is not defined
		#except(Invtypes.DoesNotExist):
		except:
			badItemList.add(item)

	return itemDict, badItemList

def get_fit_price(form_data):
	itemList = parse_fit(form_data['fit'])
	itemDict, badItemList = fetch_itemid(itemList)
	systemID = invNames.get(itemname=form_data['system']).itemid

	# It's easier to construct our own POST data than to use urlencode
	post_data="usesystem={0}&typeid={1}".format(str(systemID), "&typeid=".join(itemDict))
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
	output['data'] = list()
	output['badItemList'] = list()
	buy_total = 0
	sell_total = 0

	for element in tree.iter():
		if element.tag == "type":
			itemName = itemDict[element.attrib['id']]
			itemQuantity = itemList[itemName]
			buy = float(element.xpath("buy/max")[0].text)
			sell = float(element.xpath("sell/min")[0].text)
			buy_subtotal = buy * itemQuantity
			sell_subtotal = sell * itemQuantity
			buy_total += buy_subtotal
			sell_total += sell_subtotal
			output['data'].append({'name': itemName, 'quantity': itemQuantity, 'buy': add_commas(buy), 'sell': add_commas(sell)})
			
	output['data'].append({'name': None, 'quantity': None, 'buy': add_commas(buy_total), 'sell': add_commas(sell_total)})

	if badItemList:
		for i in badItemList:
			output['badItemList'].append(i)

	return output
