import urllib, xmltodict, re
from models import Invtypes, Invnames

staticDB = 'eve_static'

invNames = Invnames.objects.using(staticDB)
invTypes = Invtypes.objects.using(staticDB)

def set_item_quantity(itemName, quantity):
	global itemList

	inc = 1
	if quantity:
		inc = quantity

	try:
		if itemList[itemName]:
			itemList[itemName] += inc
	except:
		itemList[itemName] = inc

def add_commas(foo):
	return("{0:,}".format(foo))

def get_fit_price(form_data):
	global systemID, itemList, itemDict, badItemList

	itemList = dict()
	itemDict = dict()
	badItemList = set()
	fit_data = form_data['fit']
	systemID = invNames.get(itemname=form_data['system']).itemid

	for line in fit_data.splitlines():
		try:
			if line[0] == "[":
				re.IGNORECASE
				if not re.search("^\[empty", line):
					set_item_quantity(line.rstrip().split(",")[0][1:], None)
			else:
				if line.rstrip():
					q = re.search(" x\d+$", line)
					if q:
						set_item_quantity(line[:q.start()], int(q.group(0)[2:]))
					else:
						set_item_quantity(line.rstrip().split(",")[0], None)
		except:
			pass

	for item in itemList:
		try:
			itemDict[str(invTypes.get(typename=item).typeid)] = item
		except(DoesNotExist):
			badItemList.add(item)


	# It's easier to construct our own POST data than to use urlencode
	post_data="usesystem=" + str(systemID) + "&typeid=" + "&typeid=".join(itemDict)
	f = urllib.urlopen("http://api.eve-central.com/api/marketstat", post_data)
	doc = xmltodict.parse(f.read())

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
