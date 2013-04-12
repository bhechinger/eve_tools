import urllib, re, logging, pickle
from operator import itemgetter
from models import Invtypes, Invnames, Invcategories, Invgroups, Fitting
from lxml import etree
from django.db import connections
from django.core.exceptions import ObjectDoesNotExist

class GetFittingPrice:
	PRE=0
	POST=1
	url="http://api.eve-central.com/api/marketstat"
	logger = logging.getLogger(__name__)

	staticDB = 'eve_static'
	invNames = Invnames.objects.using(staticDB)
	invTypes = Invtypes.objects.using(staticDB)
	invCategories = Invcategories.objects.using(staticDB)
	invGroups = Invgroups.objects.using(staticDB)
	fitting = Fitting.objects

	ship_id = dict()
	fit_data = None
	ship_name = ""
	itemList = dict()
	itemDict = dict()
	badItemList = dict()
	output = dict()

	def set_item_quantity(self, itemName, quantity):
		inc = 1
		if quantity:
			inc = quantity

		try:
			self.itemList[self.ship_name][itemName] += inc
		except:
			self.itemList[self.ship_name][itemName] = inc

	def add_commas(self, foo):
		return "{0:,.2f}".format(foo)

	def parse_xml_fit(self):
		try:
			root = etree.fromstring(self.fit_data)
		except(etree.ParseError):
			# parse error, figure out how to pass that back
			return None

		for ship in root:
			self.ship_name = ship.attrib['name']
			self.itemList[self.ship_name] = dict()
			for fitting in ship:
				if fitting.tag != "description":
					if fitting.tag == "shipType":
						self.set_item_quantity(fitting.attrib['value'], None)
					elif fitting.tag == "hardware":
						if fitting.attrib['slot'] != "cargo":
							qty = None
							if fitting.attrib['slot'] == "drone bay":
								qty = int(fitting.attrib['qty'])
							self.set_item_quantity(fitting.attrib['type'], qty)

	def parse_eft_fit(self):
		for line in self.fit_data.splitlines():
			try:
				if line[0] == "[":
					if not re.search("^\[empty", line):
						self.ship_name = line.rstrip().split(",")[1][1:-2]
						self.itemList[self.ship_name] = dict()
						self.set_item_quantity(line.rstrip().split(",")[0][1:], None)
				else:
					item = line.rstrip()
					if item:
						q = re.search(" x\d+$", item)
						if q:
							self.set_item_quantity(item[:q.start()], int(q.group(0)[2:]))
						else:
							self.set_item_quantity(item.split(",")[0], None)
			except:
				pass

	def parse_fit(self):
		if re.search("^\<\?xml", self.fit_data):
			self.parse_xml_fit()
		else:
			self.parse_eft_fit()

	def get_slot(self, item):
		groupID = self.invTypes.get(typename=item).groupid
		categoryID = self.invGroups.get(groupid=int(groupID)).categoryid
		categoryName = self.invCategories.get(categoryid=int(categoryID)).categoryname

		if categoryName == 'Module':
			eve_static_cur = connections['eve_static'].cursor()
			eve_static_cur.execute("SELECT TRIM(effect.effectName) AS slot FROM invTypes AS type INNER JOIN dgmTypeEffects AS typeEffect ON type.typeID = typeEffect.typeID INNER JOIN dgmEffects AS effect ON typeEffect.effectID = effect.effectID WHERE effect.effectName IN ('loPower', 'medPower', 'hiPower', 'rigSlot') AND type.typeName = %s;", [item])
			try:
				slot = eve_static_cur.fetchone()[0]
			except:
				return "Z", "Unknown"

			if slot == "hiPower":
				slotorder = "A"
				slotname = "High Power"
			elif slot == "medPower":
				slotorder = "B"
				slotname = "Medium Power"
			elif slot == "loPower":
				slotorder = "C"
				slotname = "Low Power"
			elif slot == "rigSlot":
				slotorder = "D"
				slotname = "Rig Slot"
			else:
				slotorder = "Z"
				slotname = "Unknown"

		elif categoryName == 'Subsystem':
			slotorder = "E"
			slotname = "Subsystem"
		elif categoryName == 'Ship':
			slotorder = "F"
			slotname = "Ship"
		elif categoryName == 'Drone':
			slotorder = "G"
			slotname = "Drone"
		elif categoryName == 'Implant':
			slotorder = "H"
			slotname = "Implant"
		else:
			slotorder = "Z"
			slotname = "Unknown"

		return slotorder, slotname

	def fetch_itemid(self):
		for ship in self.itemList:
			self.itemDict[ship] = dict()
			self.badItemList[ship] = set()
			for item in self.itemList[ship]:
				try:
					self.itemDict[ship][str(self.invTypes.get(typename=item).typeid)] = item
				# need to figure out why this doesn't work:
				# Exception Value:	global name 'DoesNotExist' is not defined
				#except(Invtypes.DoesNotExist):
				except:
					self.badItemList[ship].add(item)

			itemList_pkl = pickle.dumps(self.itemList[ship])
			itemDict_pkl = pickle.dumps(self.itemDict[ship])
			new_ship = self.fitting.create(name=ship, item_list=itemList_pkl, item_dict=itemDict_pkl)
			new_ship.save()
			self.ship_id[ship] = new_ship.id

	def get_prices(self):
		for ship in self.itemDict:
			# It's easier to construct our own POST data than to use urlencode
			post_data="usesystem={0}&typeid={1}".format(str(self.systemID), "&typeid=".join(self.itemDict[ship]))
			url_data = "{0}/?{1}".format(self.url, post_data)
			#self.logger.debug("data url: {0}".format(url_data))
			#try:
			#	tree = etree.parse(url_data)
			#except(etree.XMLSyntaxError):
			#	self.logger.error("XML misformed or something?")
			#	return None

			f = urllib.urlopen(url_data)
			tree = etree.fromstring(f.read())
			f.close()

			self.output[ship] = list()
			buy_total = 0
			sell_total = 0

			for element in tree.iter():
				if element.tag == "type":
					itemName = self.itemDict[ship][element.attrib['id']]
					itemQuantity = self.itemList[ship][itemName]
					slotorder, slotname = self.get_slot(itemName)
					buy = float(element.xpath("buy/max")[0].text)
					sell = float(element.xpath("sell/min")[0].text)
					buy_subtotal = buy * itemQuantity
					sell_subtotal = sell * itemQuantity
					buy_total += buy_subtotal
					sell_total += sell_subtotal
					self.output[ship].append({'name': itemName, 'quantity': itemQuantity, 'slotorder': slotorder, 'slotname': slotname, 'buy': self.add_commas(buy), 'sell': self.add_commas(sell)})

			self.output[ship].sort(key=itemgetter('slotorder'))
			self.output[ship].append({'name': None, 'quantity': None, 'slotorder': None, 'slotname': None, 'buy': self.add_commas(buy_total), 'sell': self.add_commas(sell_total)})
			self.output[ship].append({'ship_id': self.ship_id[ship]})

	def get_fit_price(self, form_data):
		if form_data['file']:
			self.fit_data = form_data['file'].read()
		else:
			if not form_data['fit']:
				return None, None, "No file uploaded and no data pasted!!!"
			self.fit_data = form_data['fit']

		self.systemID = self.invNames.get(itemname=form_data['system']).itemid
		self.parse_fit()
		self.fetch_itemid()
		self.get_prices()
		return self.output, self.badItemList, None

	def get_from_db(self, ship_id, systemID):
		try:
			self.systemID = self.invNames.get(itemname=systemID).itemid
		except(ObjectDoesNotExist):
			return None, None, "Error: System '{0}' Not Found".format(systemID)

		ship = self.fitting.get(id=ship_id)
		self.ship_id[ship.name] = None
		self.itemDict[ship.name] = pickle.loads(ship.item_dict)
		self.itemList[ship.name] = pickle.loads(ship.item_list)
		self.get_prices()
		return self.output, self.badItemList, None

	def get_from_db_html(self, ship_ip, systemID):
		return self.get_from_db(ship_ip, systemID)

	def get_longest_string(self):
		name_length = 0
		slotname_length = 0
		sell_length = 0
		buy_length = 0
		quantity_length = 0

		for ship in self.output:
			for module in self.output[ship]:
				try:
					tmp_name_length = len(module['name'])
					if tmp_name_length > name_length:
						name_length = tmp_name_length
				except(TypeError, KeyError):
					pass

				try:
					tmp_slotname_length = len(module['slotname'])
					if tmp_slotname_length > slotname_length:
						slotname_length = tmp_slotname_length
				except(TypeError, KeyError):
					pass

				try:
					tmp_sell_length = len(module['sell'])
					if tmp_sell_length > sell_length:
						sell_length = tmp_sell_length
				except(TypeError, KeyError):
					pass

				try:
					tmp_buy_length = len(module['buy'])
					if tmp_buy_length > buy_length:
						buy_length = tmp_buy_length
				except(TypeError, KeyError):
					pass

				try:
					tmp_quantity_length = len(str(module['quantity']))
					if tmp_quantity_length > quantity_length:
						quentity_length = tmp_quantity_length
				except(TypeError, KeyError):
					pass

		return name_length, slotname_length, sell_length, buy_length, quantity_length

	def pad(self, input_string, length, side):
		if not input_string or input_string == "None":
			input_string = " "

		pad_string = " " * (length - len(input_string) + 2)
		if side == self.PRE:
			return "{0}{1}".format(pad_string, input_string)
		elif side == self.POST:
			return "{0}{1}".format(input_string, pad_string)
		else:
			self.logger.error("pad(): side unknown: {0}".format(side))
			return None

	def get_from_db_text(self, ship_ip, systemID):
		self.get_from_db(ship_ip, systemID)
		name_length, slotname_length, sell_length, buy_length, quantity_length = self.get_longest_string()
		for ship in self.output:
			text_output = "{0}\n\n".format(ship)
			slotname_header = self.pad("Slot", slotname_length, self.POST)
			name_header = self.pad("Name", name_length, self.POST)
			quantity_header = self.pad("Qty", quantity_length, self.POST)
			buy_header = self.pad("     Buy", buy_length, self.POST)
			sell_header = self.pad("     Sell", sell_length, self.POST)
			text_output += "{0} {1} {2} {3} {4}\n".format(slotname_header, name_header, quantity_header, buy_header, sell_header)
			for module in self.output[ship]:
				try:
					if module['ship_id']:
						continue
				except(KeyError):
					try:
						slotname = self.pad(module['slotname'], slotname_length, self.POST)
						name = self.pad(module['name'], name_length, self.POST)
						quantity = self.pad(str(module['quantity']), quantity_length, self.PRE)
						buy = self.pad(module['buy'], buy_length, self.PRE)
						sell = self.pad(module['sell'], sell_length, self.PRE)
						text_output += "{0} {1} {2} {3} {4}\n".format(slotname, name, quantity, buy, sell)
					except(KeyError):
						continue

		return text_output
