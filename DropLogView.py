import Config, time, json, urllib2, webbrowser, SimpleHTTPServer, SocketServer, threading
from operator import itemgetter
from PyQt4 import QtCore, QtGui
import steamodd as steam

from LogEntriesDialog import LogEntriesWindow
from Common import u
from Common import returnResourcePath
from Common import curry

schema = None

class DropLogView(QtGui.QWidget):
	def __init__(self, mainwindow, tray, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.mainwindow = mainwindow
		self.tray = tray
		self.settings = Config.settings
		self.threadevent = threading.Event()
		self.schemaThreadRunning = False
		self.logWindow = QtGui.QTextBrowser()
		self.logWindow.setOpenLinks(False) # Don't try to open links inside viewer itself
		self.view = 'separate'
		self.separateSorting = 'time_up'
		self.aggregateSorting = 'account_up'
		self.showItemValues = False
		self.loggedAccounts = []
		self.accountThreads = {}
		self.eventsList = []
		self.selectedAccounts = []
		self.priceList = None
		self.hatCount = 0
		self.weaponCount = 0
		self.toolCount = 0
		self.crateCount = 0
		self.valueCount = 0

		self.webServer = False
		if self.settings.get_option('Settings', 'log_web_view') == 'On':
			self.changeWebServerStatus(self.settings.get_option('Settings', 'log_web_view'))

		self.notificationsToastie = False
		if self.settings.get_option('Settings', 'sys_tray_notifications') != '':
			self.toggleSysTrayNotifications(self.settings.get_option('Settings', 'sys_tray_notifications'))

		self.logWindow.setReadOnly(True)

		self.updateWindow(construct = True)

	def updateWindow(self, construct=False):

		# Add horizontal toolbar actions

		switchToAccountsViewIcon = QtGui.QIcon()
		switchToAccountsViewIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/arrow_left.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.switchToAccountsViewAction = self.mainwindow.htoolBar.addAction(switchToAccountsViewIcon, 'Accounts view')
		QtCore.QObject.connect(self.switchToAccountsViewAction, QtCore.SIGNAL('triggered()'), self.changeMainWindowView)

		self.mainwindow.htoolBar.addSeparator()

		addAccountsIcon = QtGui.QIcon()
		addAccountsIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/add_account.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.addAccountsAction = self.mainwindow.htoolBar.addAction(addAccountsIcon, 'Add accounts')
		QtCore.QObject.connect(self.addAccountsAction, QtCore.SIGNAL('triggered()'), self.addAccounts)

		removeAccountsIcon = QtGui.QIcon()
		removeAccountsIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/remove_account.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.removeAccountsAction = self.mainwindow.htoolBar.addAction(removeAccountsIcon, 'Remove accounts')
		QtCore.QObject.connect(self.removeAccountsAction, QtCore.SIGNAL('triggered()'), self.removeAccounts)

		stopLoggingIcon = QtGui.QIcon()
		stopLoggingIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/terminate.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.stopLoggingAction = self.mainwindow.htoolBar.addAction(stopLoggingIcon, 'Stop logging')
		QtCore.QObject.connect(self.stopLoggingAction, QtCore.SIGNAL('triggered()'), self.stopLogging)

		self.mainwindow.htoolBar.addSeparator()

		toggleLogEntriesIcon = QtGui.QIcon()
		toggleLogEntriesIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/toggle_entries.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.toggleLogEntriesAction = self.mainwindow.htoolBar.addAction(toggleLogEntriesIcon, 'Toggle log entries')
		QtCore.QObject.connect(self.toggleLogEntriesAction, QtCore.SIGNAL('triggered()'), self.toggleEntries)
		
		saveToFileIcon = QtGui.QIcon()
		saveToFileIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/save_file.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.saveToFileAction = self.mainwindow.htoolBar.addAction(saveToFileIcon, 'Save to file')
		QtCore.QObject.connect(self.saveToFileAction, QtCore.SIGNAL('triggered()'), self.saveToFile)
		
		self.mainwindow.htoolBar.addSeparator()
		
		resetCountIcon = QtGui.QIcon()
		resetCountIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/reset_button.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.resetCountAction = self.mainwindow.htoolBar.addAction(resetCountIcon, 'Reset count')
		QtCore.QObject.connect(self.resetCountAction, QtCore.SIGNAL('triggered()'), self.resetCount)
		
		self.mainwindow.htoolBar.addSeparator()
		
		font = QtGui.QFont()
		font.setFamily('TF2 Build')
		font.setPointSize(23)
		
		self.hatCounterwidget = QtGui.QWidget()
		self.hatCounterLayout = QtGui.QVBoxLayout(self.hatCounterwidget)
		self.hatCounterLayout.setSpacing(0)
		self.hatCounterLayout.setContentsMargins(10, -1, 10, -1)

		self.hatCounter = QtGui.QLabel()
		self.hatCounter.setFont(font)
		self.hatCounter.setText(str(self.hatCount))
		self.hatCounter.setAlignment(QtCore.Qt.AlignCenter)

		self.hatCounterLabel = QtGui.QLabel()
		self.hatCounterLabel.setText('Hats')
		self.hatCounterLabel.setAlignment(QtCore.Qt.AlignCenter)
		
		self.hatCounterLayout.addWidget(self.hatCounter)
		self.hatCounterLayout.addWidget(self.hatCounterLabel)
		self.mainwindow.htoolBar.addWidget(self.hatCounterwidget)

		self.weaponCounterwidget = QtGui.QWidget()
		self.weaponCounterLayout = QtGui.QVBoxLayout(self.weaponCounterwidget)
		self.weaponCounterLayout.setSpacing(0)
		self.weaponCounterLayout.setContentsMargins(10, -1, 10, -1)

		self.weaponCounter = QtGui.QLabel()
		self.weaponCounter.setFont(font)
		self.weaponCounter.setText(str(self.weaponCount))
		self.weaponCounter.setAlignment(QtCore.Qt.AlignCenter)

		self.weaponCounterLabel = QtGui.QLabel()
		self.weaponCounterLabel.setText('Weapons')
		self.weaponCounterLabel.setAlignment(QtCore.Qt.AlignCenter)

		self.weaponCounterLayout.addWidget(self.weaponCounter)
		self.weaponCounterLayout.addWidget(self.weaponCounterLabel)
		self.mainwindow.htoolBar.addWidget(self.weaponCounterwidget)
		
		self.toolCounterwidget = QtGui.QWidget()
		self.toolCounterLayout = QtGui.QVBoxLayout(self.toolCounterwidget)
		self.toolCounterLayout.setSpacing(0)
		self.toolCounterLayout.setContentsMargins(10, -1, 10, -1)

		self.toolCounter = QtGui.QLabel()
		self.toolCounter.setFont(font)
		self.toolCounter.setText(str(self.toolCount))
		self.toolCounter.setAlignment(QtCore.Qt.AlignCenter)

		self.toolCounterLabel = QtGui.QLabel()
		self.toolCounterLabel.setText('Tools')
		self.toolCounterLabel.setAlignment(QtCore.Qt.AlignCenter)
		
		self.toolCounterLayout.addWidget(self.toolCounter)
		self.toolCounterLayout.addWidget(self.toolCounterLabel)
		self.mainwindow.htoolBar.addWidget(self.toolCounterwidget)
		
		self.crateCounterwidget = QtGui.QWidget()
		self.crateCounterLayout = QtGui.QVBoxLayout(self.crateCounterwidget)
		self.crateCounterLayout.setSpacing(0)
		self.crateCounterLayout.setContentsMargins(10, -1, 10, -1)

		self.crateCounter = QtGui.QLabel()
		self.crateCounter.setFont(font)
		self.crateCounter.setText(str(self.crateCount))
		self.crateCounter.setAlignment(QtCore.Qt.AlignCenter)

		self.crateCounterLabel = QtGui.QLabel()
		self.crateCounterLabel.setText('Crates')
		self.crateCounterLabel.setAlignment(QtCore.Qt.AlignCenter)
		
		self.crateCounterLayout.addWidget(self.crateCounter)
		self.crateCounterLayout.addWidget(self.crateCounterLabel)
		self.mainwindow.htoolBar.addWidget(self.crateCounterwidget)

		self.valueCounterwidget = QtGui.QWidget()
		self.valueCounterLayout = QtGui.QVBoxLayout(self.valueCounterwidget)
		self.valueCounterLayout.setSpacing(0)
		self.valueCounterLayout.setContentsMargins(10, -1, 10, -1)

		self.valueCounter = QtGui.QLabel()
		self.valueCounter.setFont(font)
		self.valueCounter.setText(str("%.2f" % float(self.valueCount)))
		self.valueCounter.setAlignment(QtCore.Qt.AlignCenter)

		self.valueCounterLabel = QtGui.QLabel()
		self.valueCounterLabel.setText('Value')
		self.valueCounterLabel.setAlignment(QtCore.Qt.AlignCenter)
		
		self.valueCounterLayout.addWidget(self.valueCounter)
		self.valueCounterLayout.addWidget(self.valueCounterLabel)
		if self.showItemValues:
			self.mainwindow.htoolBar.addWidget(self.valueCounterwidget)

		self.mainwindow.htoolBar.addSeparator()

		switchLogViewIcon = QtGui.QIcon()
		switchLogViewIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/switch_log_view.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.switchLogViewAction = self.mainwindow.htoolBar.addAction(switchLogViewIcon, 'Switch log view')
		QtCore.QObject.connect(self.switchLogViewAction, QtCore.SIGNAL('triggered()'), self.switchLogView)

		if construct:
			self.gridLayout = QtGui.QGridLayout(self)
			self.gridLayout.setMargin(0)

			self.verticalLayout = QtGui.QVBoxLayout()
			self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
			self.gridLayout.addWidget(self.logWindow)
			
			QtCore.QObject.connect(self.logWindow, QtCore.SIGNAL('anchorClicked(QUrl)'), self.openLink)

			QtCore.QMetaObject.connectSlotsByName(self)

			self.updateLogDisplay()

	def getSelectedAccounts(self):
		self.emit(QtCore.SIGNAL('retrieveSelectedAccounts'))

	def setSelectedAccounts(self, selectedAccounts):
		self.selectedAccounts = selectedAccounts

	def changeMainWindowView(self):
		self.mainwindow.changeView()

	def switchLogView(self):
		if self.view == 'separate':
			self.view = 'aggregate'
		else:
			self.view = 'separate'
		self.updateLogDisplay()

	def fetchSchema(self):
		if not self.schemaThreadRunning:
			# Block account threads from starting the first time until schema is downloaded
			self.threadevent.clear()
			# Run the schema downloading thread
			self.schemathread = SchemaThread(self.threadevent)
			QtCore.QObject.connect(self.schemathread, QtCore.SIGNAL('schemaSeedFail'), self.killSchemaThread)
			self.schemathread.start()
			self.schemaThreadRunning = True

	def killSchemaThread(self):
		self.schemaThreadRunning = False

	def addAccounts(self):
		APIKey = self.settings.get_option('Settings', 'API_key')
		if len(APIKey) != 32:
			QtGui.QMessageBox.warning(self.mainwindow, 'API key not valid', 'Your API key is not valid, please check you have entered it correctly')
			return None

		self.getSelectedAccounts()
		if len(self.selectedAccounts) == 0:
			QtGui.QMessageBox.information(self.mainwindow, 'No accounts selected', 'Please select at least one account from the accounts page to add')
			return None
		for account in self.selectedAccounts:
			self.addAccount(account)

	def addAccount(self, account):
		global schema

		if schema is None:
			self.fetchSchema()

		if account not in self.accountThreads:
			self.thread = DropMonitorThread(account, self.threadevent)
			QtCore.QObject.connect(self.thread, QtCore.SIGNAL('logEvent(PyQt_PyObject)'), self.addEvent)
			QtCore.QObject.connect(self.thread, QtCore.SIGNAL('threadDeath'), self.removeThread)
			self.accountThreads[account] = self.thread
			if account not in self.loggedAccounts:
				self.loggedAccounts.append(account)
			self.thread.start()

	def removeAccounts(self):
		self.getSelectedAccounts()
		if len(self.selectedAccounts) == 0:
			QtGui.QMessageBox.information(self.mainwindow, 'No accounts selected', 'Please select at least one account from the accounts page to remove')
			return None
		for account in self.selectedAccounts:
			self.removeAccount(account)

	def removeAccount(self, account):
		if account in self.accountThreads:
			self.accountThreads[account].kill()

	def stopLogging(self):
		for account in self.accountThreads:
			self.accountThreads[account].kill()

	def toggleEntries(self):
		logEntriesWindow = LogEntriesWindow()
		logEntriesWindow.setModal(True)
		logEntriesWindow.exec_()
		self.updateLogDisplay()
	
	def resetCount(self):
		self.hatCount = 0
		self.weaponCount = 0
		self.toolCount = 0
		self.crateCount = 0
		self.valueCount = 0.0

		self.hatCounter.setText(str(self.hatCount))
		self.weaponCounter.setText(str(self.weaponCount))
		self.toolCounter.setText(str(self.toolCount))
		self.crateCounter.setText(str(self.crateCount))
		self.valueCounter.setText(str("%.2f" % float(self.valueCount)))

	def addEvent(self, event):
		if event['event_type'] == 'weapon_drop':
			self.weaponCount += 1
		elif event['event_type'] == 'crate_drop':
			self.crateCount += 1
		elif event['event_type'] == 'hat_drop':
			self.hatCount += 1
		elif event['event_type'] == 'tool_drop':
			self.toolCount += 1
		self.valueCount += self.returnItemValue(event['schema_id'], event['quality'], event['uncraftable'], event['attributes'], ret_float=True)
		self.eventsList.append(event)
		self.updateLogDisplay()

		if self.notificationsToastie:
			sysTrayToggles = self.settings.get_option('Settings', 'sys_tray_notifications').split(',')
			notify = False
			if event['event_type'] == 'weapon_drop' and 'weapons' in sysTrayToggles:
				notify = True
				itemtype = 'Weapon'
			elif event['event_type'] == 'crate_drop' and 'crates' in sysTrayToggles:
				notify = True
				itemtype = 'Crate'
			elif event['event_type'] == 'hat_drop' and 'hats' in sysTrayToggles:
				notify = True
				itemtype = 'Hat'
			elif event['event_type'] == 'tool_drop' and 'tools' in sysTrayToggles:
				notify = True
				itemtype = 'Tool'
			if notify:
				self.notificationsThread.addNotification({'itemtype': itemtype, 'display_name': event['display_name'], 'item': event['item']})

	def removeThread(self, account):
		if account in self.accountThreads:
			del self.accountThreads[account]

	def saveToFile(self):
		filename = QtGui.QFileDialog.getSaveFileName(self, 'Save log to file')
		if filename:
			toggles = self.settings.get_option('Settings', 'ui_log_entry_toggles').split(',')
			log_file_formatting = self.settings.get_option('Settings', 'log_file_formatting')
			string = ''
			for event in self.eventsList:
				if event['event_type'] == 'system_message' and 'system' in toggles:
					string += '%s, %s, %s, %s\r\n' % (event['date'], event['time'], event['message'], event['display_name'])
				else:
					print_string = event['event_type'] == 'weapon_drop' and 'weapons' in toggles
					print_string = print_string or event['event_type'] == 'crate_drop' and 'crates' in toggles
					print_string = print_string or event['event_type'] == 'hat_drop' and 'hats' in toggles
					print_string = print_string or event['event_type'] == 'tool_drop' and 'tools' in toggles
					if print_string:
						itemstring = log_file_formatting.replace('{time}', event['time'])
						itemstring = itemstring.replace('{date}', event['date'])
						itemstring = itemstring.replace('{item}', event['item'])
						itemstring = itemstring.replace('{itemtype}', event['event_type'])
						itemstring = itemstring.replace('{id}', event['item_id'])
						itemstring = itemstring.replace('{account}', event['account'])
						itemstring = itemstring.replace('{accountnickname}', event['display_name'])
						itemstring = itemstring.replace('{nline}', '\r\n')
						string += itemstring
			f = open(filename, 'wb')
			f.write(string.encode('utf-8'))
			f.close()

	def openLink(self, url):
		if url.toString()[0] == '#':
			sorting = url.toString()[1:]
			if self.view == 'separate':
				self.separateSorting = sorting
			elif self.view == 'aggregate':
				self.aggregateSorting = sorting
			self.updateLogDisplay()
		else:
			webbrowser.open(url.toString())

	def openSteamSite(self):
		webbrowser.open(r'http://steampowered.com')

	def updatePriceList(self, pricelist):
		if pricelist is not None:
			self.priceList = pricelist
			self.updateLogDisplay()

	def returnItemLink(self, colour, steam_id, item_id):
		backpack_viewer = self.settings.get_option('Settings', 'backpack_viewer')

		if backpack_viewer == 'Backpack.tf':
			return '<a style="color: #%s;text-decoration:none" href="http://backpack.tf/item/%s" target="_blank">Link</a>' % (colour, item_id)
		elif backpack_viewer == 'OPTF2':
			return '<a style="color: #%s;text-decoration:none" href="http://optf2.com/tf2/item/%s/%s" target="_blank">Link</a>' % (colour, steam_id, item_id)
		elif backpack_viewer == 'Steam':
			return '<a style="color: #%s;text-decoration:none" href="http://steamcommunity.com/profiles/%s/inventory/#440_2_%s" target="_blank">Link</a>' % (colour, steam_id, item_id)
		elif backpack_viewer == 'TF2B':
			return '<a style="color: #%s;text-decoration:none" href="http://tf2b.com/tf2/item/%s/%s" target="_blank">Link</a>' % (colour, steam_id, item_id)
		elif backpack_viewer == 'TF2Items':
			return '<a style="color: #%s;text-decoration:none" href="http://www.tf2items.com/item/%s" target="_blank">Link</a>' % (colour, item_id)

	def returnWikiLink(self, colour, item):
		return '<a style="color: #%s;text-decoration:none" href="http://wiki.tf2.com/wiki/%s" target="_blank">%s</a>' % (colour, item, item)

	def returnValueLink(self, colour, item_schema_id, item_quality, uncraftable, attributes):
		value = self.returnItemValue(item_schema_id, item_quality, uncraftable, attributes)
		if uncraftable == 'True':
			item_quality = '600'
		index = '0'
		for attribute in attributes:
			attrname = attribute.get_name()
			if attrname == 'set supply crate series' or attrname == 'attach particle effect':
				index = str(attribute.get_value_formatted())
				break
		return '<a style="color: #%s;text-decoration:none" href="http://backpack.tf/vote/%s/%s/%s" target="_blank">%s</a>' % (colour, item_schema_id, item_quality, index, value)

	def returnBackpackLink(self, colour, steam_id, display_name):
		backpack_viewer = self.settings.get_option('Settings', 'backpack_viewer')

		if backpack_viewer == 'Backpack.tf':
			return '<a style="color: #%s;text-decoration:none" href="http://backpack.tf/id/%s" target="_blank">%s</a>' % (colour, steam_id, display_name)
		elif backpack_viewer == 'OPTF2':
			return '<a style="color: #%s;text-decoration:none" href="http://optf2.com/tf2/user/%s" target="_blank">%s</a>' % (colour, steam_id, display_name)
		elif backpack_viewer == 'Steam':
			return '<a style="color: #%s;text-decoration:none" href="http://steamcommunity.com/id/%s/inventory" target="_blank">%s</a>' % (colour, steam_id, display_name)
		elif backpack_viewer == 'TF2B':
			return '<a style="color: #%s;text-decoration:none" href="http://tf2b.com/tf2/%s" target="_blank">%s</a>' % (colour, steam_id, display_name)
		elif backpack_viewer == 'TF2Items':
			return '<a style="color: #%s;text-decoration:none" href="http://www.tf2items.com/id/%s" target="_blank">%s</a>' % (colour, steam_id, display_name)

	def returnItemValue(self, item_schema_id, item_quality, uncraftable, attributes, ret_float=False):
		index = '0'
		for attribute in attributes:
			attrname = attribute.get_name()
			if attrname == 'set supply crate series' or attrname == 'attach particle effect':
				index = str(attribute.get_value_formatted())
				break

		if uncraftable == 'True':
			item_quality = '600'
		try:
			if len(self.priceList[item_schema_id][item_quality]) == 1:
				index = self.priceList[item_schema_id][item_quality].keys()[0]
			value = self.priceList[item_schema_id][item_quality][index]['value']
			if ret_float:
				return float(value)
			else:
				return str("%.2f" % float(value))
		except:
			if ret_float:
				return 0.00
			else:
				return 'N/A'

	def addTableRow(self, event):
		toggles = self.settings.get_option('Settings', 'ui_log_entry_toggles').split(',')

		self.size = self.settings.get_option('Settings', 'ui_log_font_size')
		self.family = self.settings.get_option('Settings', 'ui_log_font_family')
		self.style = self.settings.get_option('Settings', 'ui_log_font_style')
		self.weight = self.settings.get_option('Settings', 'ui_log_font_weight')
		self.colour = self.settings.get_option('Settings', 'ui_log_font_colour')
		if event['event_type'] != 'system_message':
			self.accountcolour = self.settings.get_option('Account-' + event['account'], 'ui_log_colour')

		if event['event_type'] == 'system_message':
			if 'system' in toggles:
				tableRow = """<tr style="color:#%s; font-family:'%s'; font-size:%spt;""" % (self.colour, self.family, self.size)
				if self.weight == '75':
					tableRow += 'font-weight:bold;'
				if self.style == '1':
					tableRow += 'font-style:italic;'
				tableRow += """">"""
				tableRow += """<td align='center' >""" + event['message'] + """</td>"""
				tableRow += """<td></td>"""
				if self.showItemValues:
					tableRow += """<td></td>"""
				tableRow += """<td></td>"""
				tableRow += """<td align='center' >""" + event['display_name'] + """</td>"""
				tableRow += """<td align='center' >""" + event['time'] + """</td>"""
			else:
				return None
		else:
			tableRow = """<tr style="color:#%s; font-family:'%s'; font-size:%spt;""" % (self.accountcolour, self.family, self.size)
			if self.weight == '75':
				tableRow += 'font-weight:bold;'
			if self.style == '1':
				tableRow += 'font-style:italic;'
			tableRow += """">"""
			if event['event_type'] == 'weapon_drop' and 'weapons' in toggles:
				tableRow += """<td align='center' >""" + 'Weapon' + """</td>"""
			elif event['event_type'] == 'crate_drop' and 'crates' in toggles:
				tableRow += """<td align='center' >""" + 'Crate' + """</td>"""
			elif event['event_type'] == 'hat_drop' and 'hats' in toggles:
				tableRow += """<td align='center' >""" + 'Hat' + """</td>"""
			elif event['event_type'] == 'tool_drop' and 'tools' in toggles:
				tableRow += """<td align='center' >""" + 'Tool' + """</td>"""
			else:
				# Nothing to display then
				return None
			tableRow += """<td align='center' >""" + self.returnWikiLink(self.accountcolour, event['item']) + """</td>"""
			tableRow += """<td align='center' >""" + self.returnItemLink(self.accountcolour, event['steam_id'], event['item_id']) + """</td>"""
			if self.showItemValues:
				tableRow += """<td align='center' >""" + self.returnValueLink(self.accountcolour, event['schema_id'], event['quality'], event['uncraftable'], event['attributes']) + """</td>"""
			tableRow += """<td align='center' >""" + self.returnBackpackLink(self.accountcolour, event['steam_id'], event['display_name']) + """</td>"""
			tableRow += """<td align='center' >""" + event['time'] + """</td>"""
			tableRow += """</tr>"""

		return tableRow

	def addTableRowAccount(self, account):
		toggles = self.settings.get_option('Settings', 'ui_log_entry_toggles').split(',')

		self.size = self.settings.get_option('Settings', 'ui_log_font_size')
		self.family = self.settings.get_option('Settings', 'ui_log_font_family')
		self.style = self.settings.get_option('Settings', 'ui_log_font_style')
		self.weight = self.settings.get_option('Settings', 'ui_log_font_weight')
		self.colour = self.settings.get_option('Settings', 'ui_log_font_colour')
		self.accountcolour = self.settings.get_option('Account-' + account['account'], 'ui_log_colour')

		tableRow = """<tr style="color:#%s; font-family:'%s'; font-size:%spt;""" % (self.accountcolour, self.family, self.size)
		if self.weight == '75':
			tableRow += 'font-weight:bold;'
		if self.style == '1':
			tableRow += 'font-style:italic;'
		tableRow += """">"""

		tableRow += """<td align='center' >""" + self.returnBackpackLink(self.accountcolour, account['steam_id'], account['display_name']) + """</td>"""
		if self.showItemValues:
			tableRow += """<td align='center' >""" + str("%.2f" % float(account['value'])) + """</td>"""
		tableRow += """<td align='center' >""" + str(account['hatcount']) + """</td>"""
		tableRow += """<td align='center' >""" + str(account['weaponcount']) + """</td>"""
		tableRow += """<td align='center' >""" + str(account['toolcount']) + """</td>"""
		tableRow += """<td align='center' >""" + str(account['cratecount']) + """</td>"""
		tableRow += """<td align='center' >""" + str(account['totalcount']) + """</td>"""
		tableRow += """</tr>"""

		return tableRow

	def sortEvents(self, eventsList, sorting):
		if sorting == 'time_up':
			return reversed(eventsList)
		elif sorting == 'time_down':
			return eventsList
		elif sorting == 'type_up':
			return sorted(eventsList, key=itemgetter('event_type'), reverse=False)
		elif sorting == 'type_down':
			return sorted(eventsList, key=itemgetter('event_type'), reverse=True)
		elif sorting == 'item_up':
			return sorted(eventsList, key=itemgetter('item'), reverse=False)
		elif sorting == 'item_down':
			return sorted(eventsList, key=itemgetter('item'), reverse=True)
		elif sorting == 'account_up':
			return sorted(eventsList, key=itemgetter('display_name'), reverse=False)
		elif sorting == 'account_down':
			return sorted(eventsList, key=itemgetter('display_name'), reverse=True)
		elif sorting == 'value_up':
			return sorted(eventsList, key=lambda event: self.returnItemValue(event['schema_id'], event['quality'], event['uncraftable'], event['attributes'], ret_float=True), reverse=True)
		elif sorting == 'value_down':
			return sorted(eventsList, key=lambda event: self.returnItemValue(event['schema_id'], event['quality'], event['uncraftable'], event['attributes'], ret_float=True), reverse=False)

	def sortAggregateStats(self, statsList, sorting):
		if sorting == 'account_up':
			return sorted(statsList, key=itemgetter('display_name'), reverse=False)
		elif sorting == 'account_down':
			return sorted(statsList, key=itemgetter('display_name'), reverse=True)
		elif sorting == 'hat_up':
			return sorted(statsList, key=itemgetter('hatcount'), reverse=True)
		elif sorting == 'hat_down':
			return sorted(statsList, key=itemgetter('hatcount'), reverse=False)
		elif sorting == 'weapon_up':
			return sorted(statsList, key=itemgetter('weaponcount'), reverse=True)
		elif sorting == 'weapon_down':
			return sorted(statsList, key=itemgetter('weaponcount'), reverse=False)
		elif sorting == 'tool_up':
			return sorted(statsList, key=itemgetter('toolcount'), reverse=True)
		elif sorting == 'tool_down':
			return sorted(statsList, key=itemgetter('toolcount'), reverse=False)
		elif sorting == 'crate_up':
			return sorted(statsList, key=itemgetter('cratecount'), reverse=True)
		elif sorting == 'crate_down':
			return sorted(statsList, key=itemgetter('cratecount'), reverse=False)
		elif sorting == 'total_up':
			return sorted(statsList, key=itemgetter('totalcount'), reverse=True)
		elif sorting == 'total_down':
			return sorted(statsList, key=itemgetter('totalcount'), reverse=False)
		elif sorting == 'value_up':
			return sorted(statsList, key=itemgetter('value'), reverse=True)
		elif sorting == 'value_down':
			return sorted(statsList, key=itemgetter('value'), reverse=False)

	def returnNewOrderTag(self, tag, ordering):
		if (tag + '_up') == ordering:
			return tag + '_down'
		elif (tag + '_down') == ordering:
			return tag + '_up'
		else:
			return tag + '_up'

	def returnOrderSymbol(self, tag, ordering):
		if (tag + '_up') == ordering:
			return '&#9650;'
		elif (tag + '_down') == ordering:
			return '&#9660;'
		else:
			return ''
	
	def updateLogDisplay(self):
		logWindowStyle = 'background-color: #%s;color: #%s;' % (self.settings.get_option('Settings', 'ui_log_background_colour'), self.settings.get_option('Settings', 'ui_log_font_colour'))
		self.logWindow.setStyleSheet(logWindowStyle)
		self.colour = self.settings.get_option('Settings', 'ui_log_font_colour')

		display_string = """<table width=100%>"""
		display_string += """<tr>"""

		if self.view == 'separate':
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Type %s</a></th>""" % (self.returnNewOrderTag('type', self.separateSorting), self.colour, self.returnOrderSymbol('type', self.separateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Item %s</a></th>""" % (self.returnNewOrderTag('item', self.separateSorting), self.colour, self.returnOrderSymbol('item', self.separateSorting))
			display_string += """<th style="font-size:13px">Item Link</th>"""
			if self.showItemValues:
				display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Value %s</a></th>""" % (self.returnNewOrderTag('value', self.separateSorting), self.colour, self.returnOrderSymbol('value', self.separateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Account %s</a></th>""" % (self.returnNewOrderTag('account', self.separateSorting), self.colour, self.returnOrderSymbol('account', self.separateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Time %s</a></th>""" % (self.returnNewOrderTag('time', self.separateSorting), self.colour, self.returnOrderSymbol('time', self.separateSorting))
		elif self.view == 'aggregate':
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Account %s</a></th>""" % (self.returnNewOrderTag('account', self.aggregateSorting), self.colour, self.returnOrderSymbol('account', self.aggregateSorting))
			if self.showItemValues:
				display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Value %s</a></th>""" % (self.returnNewOrderTag('value', self.aggregateSorting), self.colour, self.returnOrderSymbol('value', self.aggregateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Hats %s</a></th>""" % (self.returnNewOrderTag('hat', self.aggregateSorting), self.colour, self.returnOrderSymbol('hat', self.aggregateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Weapons %s</a></th>""" % (self.returnNewOrderTag('weapon', self.aggregateSorting), self.colour, self.returnOrderSymbol('weapon', self.aggregateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Tools %s</a></th>""" % (self.returnNewOrderTag('tool', self.aggregateSorting), self.colour, self.returnOrderSymbol('tool', self.aggregateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Crates %s</a></th>""" % (self.returnNewOrderTag('crate', self.aggregateSorting), self.colour, self.returnOrderSymbol('crate', self.aggregateSorting))
			display_string += """<th><a href="#%s" style="color:#%s;text-decoration:none;font-size:13px">Total %s</a></th>""" % (self.returnNewOrderTag('total', self.aggregateSorting), self.colour, self.returnOrderSymbol('total', self.aggregateSorting))

		display_string += """</tr>"""

		if self.view == 'separate':
			for event in self.sortEvents(self.eventsList, self.separateSorting):
				tableRow = self.addTableRow(event)
				if tableRow is not None:
					display_string += tableRow
		elif self.view == 'aggregate':
			accounts = []
			for account in self.loggedAccounts:
				if self.settings.get_option('Account-' + account, 'account_nickname') != '':
					displayname = self.settings.get_option('Account-' + account, 'account_nickname')
				else:
					displayname = account
				accountdict = {'account': account, 'steam_id': None, 'display_name': displayname, 'hatcount': 0, 'weaponcount': 0, 'toolcount': 0, 'cratecount': 0, 'totalcount': 0, 'value': 0.0}
				accounts.append(accountdict)

			for event in self.eventsList:
				accountindex = map(itemgetter('display_name'), accounts).index(event['display_name'])
				if accounts[accountindex]['steam_id'] is None:
					accounts[accountindex]['steam_id'] = event['steam_id']

				if event['event_type'] == 'weapon_drop':
					accounts[accountindex]['weaponcount'] += 1
					accounts[accountindex]['totalcount'] += 1
				elif event['event_type'] == 'crate_drop':
					accounts[accountindex]['cratecount'] += 1
					accounts[accountindex]['totalcount'] += 1
				elif event['event_type'] == 'hat_drop':
					accounts[accountindex]['hatcount'] += 1
					accounts[accountindex]['totalcount'] += 1
				elif event['event_type'] == 'tool_drop':
					accounts[accountindex]['toolcount'] += 1
					accounts[accountindex]['totalcount'] += 1

				accounts[accountindex]['value'] += self.returnItemValue(event['schema_id'], event['quality'], event['uncraftable'], event['attributes'], ret_float=True)
			
			for account in self.sortAggregateStats(accounts, self.aggregateSorting):
				display_string += self.addTableRowAccount(account)

		display_string += """</table>"""

		self.logWindow.setHtml(display_string)
		if self.webServer:
			self.webthread.setHTML("""<html style='%s'><link rel="shortcut icon" href="/favicon.png">%s</html>""" % (logWindowStyle, display_string))

		self.hatCounter.setText(str(self.hatCount))
		self.weaponCounter.setText(str(self.weaponCount))
		self.toolCounter.setText(str(self.toolCount))
		self.crateCounter.setText(str(self.crateCount))
		self.valueCounter.setText(str("%.2f" % float(self.valueCount)))

	def changeWebServerStatus(self, status):
		if status == 'Off':
			if self.webServer:
				self.webthread.kill()
			self.webServer = False
		elif status == 'On':
			if not self.webServer:
				self.webthread = WebViewThread()
				self.webthread.start()
			else: # Restart thread in case port number has changed
				self.webthread.kill()
				self.webthread.start()
			self.webServer = True

	def toggleSysTrayNotifications(self, toggles):
		if toggles == '':
			if self.notificationsToastie:
				self.notificationsThread.kill()
			self.notificationsToastie = False
		else:
			if not self.notificationsToastie:
				self.notificationsThread = SysNotificationsThread(self.tray)
				self.notificationsThread.start()
			self.notificationsToastie = True

	def toggleItemValues(self):
		if self.settings.get_option('Settings', 'log_show_item_value') == 'True':
			if not self.showItemValues:
				self.priceListThread = GetPricesThread()
				QtCore.QObject.connect(self.priceListThread, QtCore.SIGNAL('valuesUpdate'), self.updatePriceList)
				self.priceListThread.start()
			self.showItemValues = True
		else:
			if self.showItemValues:
				self.priceListThread.kill()
			self.showItemValues = False
		self.updateLogDisplay()
		self.mainwindow.redrawWindowStates()

class GetPricesThread(QtCore.QThread):
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.url = r'http://backpack.tf/api/IGetPrices/v2/?format=json&currency=metals'
		self.values = None
		self.alive = True

	def returnValues(self):
		self.emit(QtCore.SIGNAL('valuesUpdate'), self.values)

	def kill(self):
		self.alive = False

	def run(self):
		while self.alive:
			try:
				response = json.loads(urllib2.urlopen(self.url, timeout=15).read())
				values = response['response']['prices']
				self.values = values
			except:
				pass
			self.returnValues()

			if self.values is None:
				limit = 60
			else:
				limit = 60*60

			# Allow thread death while sleeping
			timer = 0
			while self.alive and timer < limit: 
				time.sleep(1)
				timer += 1

class SysNotificationsThread(QtCore.QThread):
	def __init__(self, tray, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.alive = True
		self.notifications = []
		self.tray = tray

	def addNotification(self, notification):
		self.notifications.append(notification)

	def kill(self):
		self.alive = False

	def run(self):
		while self.alive:
			if len(self.notifications) != 0:
				notification = self.notifications[0]
				self.tray.showMessage('{0} Drop'.format(notification['itemtype']), '{0} has found a {1}!'.format(notification['display_name'], notification['item'].encode('utf-8')))
				self.notifications.pop(0)
			else:
				pass
			time.sleep(5)

class WebViewThread(QtCore.QThread):
	def __init__(self, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.settings = Config.settings
	
	class MyHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
		html = ''
		def do_GET(self):
			if self.path == '/favicon.png':
				f = open(returnResourcePath('images/tf2idle.png'), 'rb')
				self.send_response(200)
				self.send_header('Content-type', 'image/png')
				self.end_headers()
				self.wfile.write(f.read())
				self.wfile.close()
			else:
				self.send_response(200)
				self.send_header("Content-type", "text/html")
				self.end_headers()
				self.wfile.write(self.html)
				self.wfile.close()

		# Hide log output from console
		def log_message(self, format, *args):
			return

	def setHTML(self, html):
		self.MyHandler.html = html

	def kill(self):
		try:
			self.httpd.shutdown()
			self.httpd.server_close()
		except:
			# Already dead
			pass
	
	def run(self):
		self.port = int(self.settings.get_option('Settings', 'log_web_view_port'))
		self.httpd = SocketServer.TCPServer(("", self.port), self.MyHandler)
		self.httpd.serve_forever()

class SchemaThread(QtCore.QThread):
	def __init__(self, event, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.settings = Config.settings
		self.event = event
		self.firstRun = True

	def run(self):
		global schema

		while True:
			try:
				steam.set_api_key(self.settings.get_option('Settings', 'API_key'))
				schema = steam.tf2.item_schema(lang='en')
				if self.firstRun:
					self.event.set()
					self.firstRun = False
			except:
				if self.firstRun:
					self.event.set()
					self.emit(QtCore.SIGNAL('schemaSeedFail'))
					break

			time.sleep(60*60*12)

class DropMonitorThread(QtCore.QThread):
	def __init__(self, account, event, parent=None):
		QtCore.QThread.__init__(self, parent)
		self.settings = Config.settings
		self.account = account
		self.event = event
		self.keepThreadAlive = True
		steam.set_api_key(self.settings.get_option('Settings', 'API_key'))
		self.lastID = None

	def returnNewestItems(self):
		global schema

		self.event.wait()

		try:
			backpack = steam.tf2.backpack(self.settings.get_option('Account-' + self.account, 'steam_vanityid'), schema=schema)
		except:
			return None
		if self.lastID is None:
			self.lastID = 0
			for item in backpack:
				if item.get_id() > self.lastID:
					self.lastID = item.get_id()
			return []
		else:
			newestitems = []
			for item in backpack:
				if item.get_id() > self.lastID:
					newestitems.append(item)
			return newestitems

	def kill(self):
		self.keepThreadAlive = False

	def run(self):
		global schema

		if self.settings.get_option('Account-' + self.account, 'account_nickname') != '':
			self.displayname = self.settings.get_option('Account-' + self.account, 'account_nickname')
		else:
			self.displayname = self.account

		# Wait for event object to give all clear that schema is downloaded
		self.event.wait()
		if schema is None:
			self.emit(QtCore.SIGNAL('logEvent(PyQt_PyObject)'), {'event_type': 'system_message',
																 'message': 'Could not download schema',
																 'display_name': self.displayname,
																 'item': '',
																 'schema_id': '',
																 'quality': '',
																 'uncraftable': '',
																 'attributes': '',
																 'time': time.strftime('%H:%M', time.localtime(time.time())),
																 'date': time.strftime('%d/%m/%y', time.localtime(time.time()))
																 }
					  )
			self.emit(QtCore.SIGNAL('threadDeath'), self.account)
			return None

		# Try with a known test case first to make sure it's the key that's invalid
		try:
			steam.user.profile('robinwalker').get_id64()
		except:
			self.emit(QtCore.SIGNAL('logEvent(PyQt_PyObject)'), {'event_type': 'system_message',
																 'message': 'API key not valid',
																 'display_name': self.settings.get_option('Account-' + self.account, 'account_nickname'),
																 'item': '',
																 'schema_id': '',
																 'quality': '',
																 'uncraftable': '',
																 'attributes': '',
																 'time': time.strftime('%H:%M', time.localtime(time.time())),
																 'date': time.strftime('%d/%m/%y', time.localtime(time.time()))
																 }
					  )
			self.emit(QtCore.SIGNAL('threadDeath'), self.account)
			return None

		try:
			self.steamid = steam.user.profile(self.settings.get_option('Account-' + self.account, 'steam_vanityid')).get_id64()
		except:
			self.emit(QtCore.SIGNAL('logEvent(PyQt_PyObject)'), {'event_type': 'system_message',
																 'message': 'Could not resolve steam vanity ID',
																 'display_name': self.settings.get_option('Account-' + self.account, 'account_nickname'),
																 'item': '',
																 'schema_id': '',
																 'quality': '',
																 'uncraftable': '',
																 'attributes': '',
																 'time': time.strftime('%H:%M', time.localtime(time.time())),
																 'date': time.strftime('%d/%m/%y', time.localtime(time.time()))
																 }
					  )
			self.emit(QtCore.SIGNAL('threadDeath'), self.account)
			return None

		self.emit(QtCore.SIGNAL('logEvent(PyQt_PyObject)'), {'event_type': 'system_message',
															 'message': 'Started logging',
															 'steam_id': self.steamid,
															 'display_name': self.displayname,
															 'item': '',
															 'schema_id': '',
															 'quality': '',
								 							 'uncraftable': '',
															 'attributes': '',
															 'time': time.strftime('%H:%M', time.localtime(time.time())),
															 'date': time.strftime('%d/%m/%y', time.localtime(time.time()))
															 }
				  )

		while self.keepThreadAlive:
			try:
				newestitems = self.returnNewestItems()
				if newestitems is None:
					continue

				for item in newestitems:
					itemname = u(item.get_name())
					id = str(item.get_id())
					schema_id = str(item.get_schema_id())
					quality = str(item.get_quality()['id'])
					uncraftable = str(item.is_uncraftable())
					attributes = item.get_attributes()
					event_time = time.strftime('%H:%M', time.localtime(time.time()))
					event_date = time.strftime('%d/%m/%y', time.localtime(time.time()))
					
					eventdict = {'item': itemname,
								 'account': self.account,
								 'display_name': self.displayname,
								 'steam_id': self.steamid,
								 'item_id': id,
								 'schema_id': schema_id,
								 'quality': quality,
								 'uncraftable': uncraftable,
								 'attributes': attributes,
								 'time': event_time,
								 'date': event_date
								 }
					
					slot = item.get_slot()
					class_ = item.get_class()
					craft_material_type = item.get_craft_material_type()

					if craft_material_type is not None:
						if craft_material_type == 'hat':
							eventdict['event_type'] = 'hat_drop'
						elif craft_material_type == 'weapon':
							eventdict['event_type'] = 'weapon_drop'
						elif craft_material_type == 'supply_crate':
							if itemname == 'Mann Co. Supply Crate':
								crateseries = str(int(item.get_attributes()[0].get_value()))
								eventdict['item'] = eventdict['item'] + ' #' + crateseries
							eventdict['event_type'] = 'crate_drop'
						elif craft_material_type == 'tool':
							eventdict['event_type'] = 'tool_drop'
						else:
							# Catch all
							eventdict['event_type'] = 'tool_drop'
					else:
						if slot == 'head' or slot == 'misc':
							eventdict['event_type'] = 'hat_drop'
						elif slot == 'primary' or slot == 'secondary' or slot == 'melee' or slot == 'pda2':
							eventdict['event_type'] = 'weapon_drop'
						elif class_ == 'supply_crate':
							# Stick crate series on end of crate item name
							if itemname == 'Mann Co. Supply Crate':
								crateseries = str(int(item.get_attributes()[0].get_value()))
								eventdict['item'] = eventdict['item'] + ' #' + crateseries
							eventdict['event_type'] = 'crate_drop'
						elif class_ == 'tool' or slot == 'action' or class_ == 'craft_item':
							eventdict['event_type'] = 'tool_drop'
						else:
							# Catch all
							eventdict['event_type'] = 'tool_drop'

					self.emit(QtCore.SIGNAL('logEvent(PyQt_PyObject)'), eventdict)
				if len(newestitems) != 0:
					self.lastID = max([item.get_id() for item in newestitems])
			except:
				pass
			# Allow thread death while sleeping
			timer = 0
			pollTime = int(self.settings.get_option('Settings', 'log_poll_time'))
			while self.keepThreadAlive and timer < 60 * pollTime: 
				time.sleep(1)
				timer += 1
		self.emit(QtCore.SIGNAL('logEvent(PyQt_PyObject)'), {'event_type': 'system_message',
															 'message': 'Stopped logging',
															 'display_name': self.displayname,
															 'item': '',
															 'schema_id': '',
															 'quality': '',
								 							 'uncraftable': '',
								 							 'attributes': '',
															 'time': time.strftime('%H:%M', time.localtime(time.time())),
															 'date': time.strftime('%d/%m/%y', time.localtime(time.time()))
															 }
				  )
		self.emit(QtCore.SIGNAL('threadDeath'), self.account)
