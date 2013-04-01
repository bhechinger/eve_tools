#!/usr/local/bin/python
import MySQLdb, urllib, xmltodict, re

db = MySQLdb.connect(host="zaphod", user="lockefox", passwd="LockeFox2012", db="eve_static")
cur = db.cursor() 

# Jita's system ID
systemID = 30000142

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

def get_fit_price(eft_data):
	global systemID, itemList, itemDict, badItemList

	itemList = dict()
	itemDict = dict()
	badItemList = set()

	for line in eft_data.splitlines():
		try:
			if line[0] == "[":
				re.IGNORECASE
				if not re.search("^\[empty", line):
					set_item_quantity(line.rstrip().split(",")[0].split("[")[1], None)
			else:
				if line.rstrip():
					if re.search(" x\d+$", line):
						set_item_quantity(line.rstrip().split(" x")[0], int(line.rstrip().split(" x")[1]))
					else:
						set_item_quantity(line.rstrip().split(",")[0], None)
		except:
			pass

	for item in itemList:
		cur.execute("SELECT typeID FROM invTypes WHERE typeName='{0}'".format(MySQLdb.escape_string(item)))
		try:
			itemDict[str(cur.fetchone()[0])] = item
		except(TypeError):
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
		buy = int(x['buy']['max'].split(".")[0]) * itemQuantity
		sell = int(x['sell']['min'].split(".")[0]) * itemQuantity
		output['data'].append({'name': itemName, 'quantity': itemQuantity, 'buy': add_commas(buy), 'sell': add_commas(sell)})
		buy_total += buy
		sell_total += sell

	output['data'].append({'name': None, 'quantity': None, 'buy': add_commas(buy_total), 'sell': add_commas(sell_total)})

	if badItemList:
		for i in badItemList:
			output['badItemList'].append(i)

	return(output)
