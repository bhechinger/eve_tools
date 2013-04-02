import urllib, xmltodict, re
from models import Invtypes, Invnames

url="http://api.eve-central.com/api/marketstat"
staticDB = 'eve_static'

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
	return("{0:,}".format(foo))

def parse_fit(fit_data):
	class itemData:
		itemList = dict()

	for line in fit_data.splitlines():
		try:
			if line[0] == "[":
				re.IGNORECASE
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

	#return g_itemList
	return itemData.itemList

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
	f = urllib.urlopen(url, post_data)
	doc = xmltodict.parse(f.read())
	f.close()

	output = dict()
	output['data'] = list()
	output['badItemList'] = list()
	buy_total = 0
	sell_total = 0
	for x in doc['evec_api']['marketstat']['type']:
		itemName = itemDict[x['@id']]
		itemQuantity = itemList[itemName]
		buy = int(x['buy']['max'].split(".")[0])
		sell = int(x['sell']['min'].split(".")[0])
		buy_subtotal = buy * itemQuantity
		sell_subtotal = sell * itemQuantity
		output['data'].append({'name': itemName, 'quantity': itemQuantity, 'buy': add_commas(buy), 'sell': add_commas(sell)})
		buy_total += buy_subtotal
		sell_total += sell_subtotal

	output['data'].append({'name': None, 'quantity': None, 'buy': add_commas(buy_total), 'sell': add_commas(sell_total)})

	if badItemList:
		for i in badItemList:
			output['badItemList'].append(i)

	return(output)
