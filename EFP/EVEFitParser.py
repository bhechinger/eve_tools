import re, logging, lxml

logger = logging.getLogger(__name__)

class _FitData:
	group = ""
	value = ""
	slot_num = None
	qty = None


class ShipFit:
	ship_name = ""
	badItemList = dict()
	fittings = dict()


class ShipFitting:
	ship_fit = ShipFit()

	_cur_slot = dict()
	_fit_data = None

	def __init__(self, fit_data):
		self._fit_data = fit_data

		if re.search("^\<\?xml", self._fit_data):
			self._parse_xml_fit()
		else:
			self._parse_eft_fit()

	def _init_data(self, ship_name):
		self.ship_fit.ship_name = ship_name
		self.ship_fit.badItemList[self.ship_fit.ship_name] = set()
		#
		# New data structure
		#
		self.ship_fit.fittings[self.ship_fit.ship_name] = dict()
		self.ship_fit.fittings[self.ship_fit.ship_name]["description"] = ""
		self.ship_fit.fittings[self.ship_fit.ship_name]["shipType"] = ""
		self.ship_fit.fittings[self.ship_fit.ship_name]["hi slot"] = {k : "" for k in range(8)}
		self.ship_fit.fittings[self.ship_fit.ship_name]["med slot"] = {k : "" for k in range(8)}
		self.ship_fit.fittings[self.ship_fit.ship_name]["low slot"] = {k : "" for k in range(8)}
		self.ship_fit.fittings[self.ship_fit.ship_name]["rig slot"] = {k : "" for k in range(3)}
		self.ship_fit.fittings[self.ship_fit.ship_name]["subsystem slot"] = {k : "" for k in range(5)}
		self.ship_fit.fittings[self.ship_fit.ship_name]["drone bay"] = dict()

		# These are used for the EFT parser but we'll initialize them here
		self._cur_slot["hi slot"] = 0
		self._cur_slot["med slot"] = 0
		self._cur_slot["low slot"] = 0
		self._cur_slot["rig slot"] = 0
		self._cur_slot["subsystem slot"] = 0

	def _populate_fittings(self, fit_data):
		try:
			if fit_data.group == "drone bay":
				self.ship_fit.fittings[self.ship_fit.ship_name][fit_data.group][fit_data.value] = fit_data.qty
			elif fit_data.group == "description" or fit_data.group == "shipType":
				self.ship_fit.fittings[self.ship_fit.ship_name][fit_data.group] = fit_data.value
			else:
				self.ship_fit.fittings[self.ship_fit.ship_name][fit_data.group][fit_data.slot_num] = fit_data.value
		except(TypeError):
			logger.debug("_populate_fittings(): fit_data.value is something odd")

	def _parse_xml_fit(self):
		try:
			root = lxml.etree.fromstring(self._fit_data)
		except(lxml.etree.ParseError):
			# parse error, figure out how to pass that back
			return None

		for ship in root:
			self._init_data(ship.attrib['name'])
			for fitting in ship:
				self._fit_data = _FitData()
				if fitting.tag == "description" or fitting.tag == "shipType":
					self._fit_data.group = fitting.tag
					self._fit_data.value = fitting.attrib['value']

				elif fitting.tag == "hardware":
					# I would like to come back to cargo at some point, but I'm skipping it for now
					if fitting.attrib['slot'] == "cargo":
						continue

					if fitting.attrib['slot'] == "drone bay":
						self._fit_data.qty = int(fitting.attrib['qty'])
						self._fit_data.group = fitting.attrib['slot']

					else:
						# Extract the module group and slot number
						q = re.search(" \d+$", fitting.attrib['slot'])

						self._fit_data.slot_num = int(q.group(0)[1:])
						self._fit_data.group = fitting.attrib['slot'][:q.start()]

					self._fit_data.value = fitting.attrib['type']

				self._populate_fittings(self._fit_data)

	def get(self):
		return(self.ship_fit)
