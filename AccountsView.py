﻿import Config, subprocess, webbrowser, shutil, os, ctypes
from PyQt4 import QtCore, QtGui
from sets import Set

import Sandboxie
from AccountDialog import AccountDialogWindow
from GroupsDialog import GroupsDialogWindow
from Common import returnResourcePath
from Common import curry

class Worker(QtCore.QThread):
	def __init__(self, parent = None):
		QtCore.QThread.__init__(self, parent)

	def copyDirectory(self, root_src_dir, root_dst_dir):
	    for src_dir, dirs, files in os.walk(root_src_dir):
	        dst_dir = src_dir.replace(root_src_dir, root_dst_dir)
	        if not os.path.exists(dst_dir):
	            os.mkdir(dst_dir)
	        for file_ in files:
	            src_file = os.path.join(src_dir, file_)
	            dst_file = os.path.join(dst_dir, file_)
	            if os.path.exists(dst_file):
	                os.remove(dst_file)
	            shutil.copy(src_file, dst_dir)

	def run(self):
		self.settings = Config.settings
		steam_location = self.settings.get_option('Settings', 'steam_location')
		secondary_steamapps_location = self.settings.get_option('Settings', 'secondary_steamapps_location')

		if not os.path.exists(steam_location + os.sep + 'steamapps/common/Team Fortress 2' + os.sep):
			self.returnMessage('Path does not exist', 'The Team Fortress 2 folder path does not exist. Please check settings')
		elif not os.path.exists(secondary_steamapps_location):
			self.returnMessage('Path does not exist', 'The secondary Team Fortress 2 folder path does not exist. Please check settings')
		else:
			self.emit(QtCore.SIGNAL('StartedCopyingTF2'))
			try:
				self.copyDirectory(steam_location + os.sep + 'steamapps/common/Team Fortress 2' + os.sep, secondary_steamapps_location + os.sep + 'common/Team Fortress 2' + os.sep)
			except:
				self.returnMessage('File copy error', 'The Team Fortress 2 directory could not be copied')
			self.emit(QtCore.SIGNAL('FinishedCopyingTF2'))
			self.returnMessage('Info', 'Finished updating the Team Fortress 2 directory. Remember to start the backup Steam installation unsandboxed to finish the update process')
		
	def returnMessage(self, title, message):
		self.emit(QtCore.SIGNAL('returnMessage'), title, message)

class AccountsView(QtGui.QWidget):
	def __init__(self, mainwindow):
		QtGui.QWidget.__init__(self)
		self.mainwindow = mainwindow
		self.settings = Config.settings
		self.toolBars = []
		self.accountButtons = []
		self.chosenSelectGroupAccounts = []
		self.chosenDeselectGroupAccounts = []
		self.createdSandboxes = []
		self.sandboxieINIIsModified = False
		self.copyingTF2 = False
		self.percentage = 0

		self.updateWindow(construct = True)

	def updateWindow(self, construct=False):
		self.mainwindow.htoolBar.clear()
		self.mainwindow.vtoolBar.clear()
		
		# Add vertical toolbar actions	

		addAccountIcon = QtGui.QIcon()
		addAccountIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/add_account.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.addAccountAction = self.mainwindow.vtoolBar.addAction(addAccountIcon, 'Add account')
		QtCore.QObject.connect(self.addAccountAction, QtCore.SIGNAL('triggered()'), self.openAccountDialog)
		
		editAccountIcon = QtGui.QIcon()
		editAccountIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/edit_account.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.editAccountAction = self.mainwindow.vtoolBar.addAction(editAccountIcon, 'Edit account')
		QtCore.QObject.connect(self.editAccountAction, QtCore.SIGNAL('triggered()'), curry(self.openAccountDialog, editAccount=True))
		
		removeAccountIcon = QtGui.QIcon()
		removeAccountIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/remove_account.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.deleteAccountsAction = self.mainwindow.vtoolBar.addAction(removeAccountIcon, 'Delete account')
		QtCore.QObject.connect(self.deleteAccountsAction, QtCore.SIGNAL('triggered()'), self.deleteAccounts)
		
		self.mainwindow.vtoolBar.addSeparator()
		
		selectGroupIcon = QtGui.QIcon()
		selectGroupIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/select_group.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.selectGroupsAction = self.mainwindow.vtoolBar.addAction(selectGroupIcon, 'Select Groups')
		QtCore.QObject.connect(self.selectGroupsAction, QtCore.SIGNAL('triggered()'), self.selectGroups)
		
		viewBackpackIcon = QtGui.QIcon()
		viewBackpackIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/backpack.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.viewBackpackAction = self.mainwindow.vtoolBar.addAction(viewBackpackIcon, 'View backpack')
		QtCore.QObject.connect(self.viewBackpackAction, QtCore.SIGNAL('triggered()'), self.openBackpack)
		
		# Add horizontal toolbar actions
		switchToLogViewIcon = QtGui.QIcon()
		switchToLogViewIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/arrow_right.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.switchToLogViewAction = self.mainwindow.htoolBar.addAction(switchToLogViewIcon, 'Drop log view')
		QtCore.QObject.connect(self.switchToLogViewAction, QtCore.SIGNAL('triggered()'), self.changeMainWindowView)
		
		self.mainwindow.htoolBar.addSeparator()
		
		startIdleIcon = QtGui.QIcon()
		startIdleIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/start_idle.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.startIdleAction = self.mainwindow.htoolBar.addAction(startIdleIcon, 'Start idling')
		QtCore.QObject.connect(self.startIdleAction, QtCore.SIGNAL('triggered()'), curry(self.startUpAccounts, action='idle'))
		
		startIdleUnsandboxedIcon = QtGui.QIcon()
		startIdleUnsandboxedIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/start_idle_unsandboxed.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.startIdleUnsandboxedAction = self.mainwindow.htoolBar.addAction(startIdleUnsandboxedIcon, 'Idle unsandboxed')
		QtCore.QObject.connect(self.startIdleUnsandboxedAction, QtCore.SIGNAL('triggered()'), curry(self.startUpAccounts, action='idle_unsandboxed'))
		
		startTF2Icon = QtGui.QIcon()
		startTF2Icon.addPixmap(QtGui.QPixmap(returnResourcePath('images/start_tf2.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.startTF2Action = self.mainwindow.htoolBar.addAction(startTF2Icon, 'Start TF2')
		QtCore.QObject.connect(self.startTF2Action, QtCore.SIGNAL('triggered()'), curry(self.startUpAccounts, action='start_TF2'))
		
		startSteamIcon = QtGui.QIcon()
		startSteamIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/start_steam.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.startSteamAction = self.mainwindow.htoolBar.addAction(startSteamIcon, 'Start Steam')
		QtCore.QObject.connect(self.startSteamAction, QtCore.SIGNAL('triggered()'), curry(self.startUpAccounts, action='start_steam'))
		
		startProgramIcon = QtGui.QIcon()
		startProgramIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/start_program.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.startProgramAction = self.mainwindow.htoolBar.addAction(startProgramIcon, 'Start Program')
		QtCore.QObject.connect(self.startProgramAction, QtCore.SIGNAL('triggered()'), self.startProgram)
		
		self.mainwindow.htoolBar.addSeparator()
		
		terminateSandboxIcon = QtGui.QIcon()
		terminateSandboxIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/terminate.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.terminateSandboxAction = self.mainwindow.htoolBar.addAction(terminateSandboxIcon, 'Terminate sandbox')
		QtCore.QObject.connect(self.terminateSandboxAction, QtCore.SIGNAL('triggered()'), curry(self.modifySandboxes, action='/terminate'))
		
		emptySandboxIcon = QtGui.QIcon()
		emptySandboxIcon.addPixmap(QtGui.QPixmap(returnResourcePath('images/delete_sandbox.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.emptySandboxAction = self.mainwindow.htoolBar.addAction(emptySandboxIcon, 'Empty sandbox')
		QtCore.QObject.connect(self.emptySandboxAction, QtCore.SIGNAL('triggered()'), curry(self.modifySandboxes, action='delete_sandbox_silent'))

		self.mainwindow.htoolBar.addSeparator()

		updateTF2Icon = QtGui.QIcon()
		if self.copyingTF2:
			progressimage = returnResourcePath('images/updating_tf2.png')
			updateTF2Icon.addPixmap(QtGui.QPixmap(progressimage), QtGui.QIcon.Normal, QtGui.QIcon.Off)
			self.updateTF2Action = self.mainwindow.htoolBar.addAction(updateTF2Icon, 'Updating TF2 folder')
		else:
			updateTF2Icon.addPixmap(QtGui.QPixmap(returnResourcePath('images/update_tf2.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
			self.updateTF2Action = self.mainwindow.htoolBar.addAction(updateTF2Icon, 'Update TF2 folder')
			QtCore.QObject.connect(self.updateTF2Action, QtCore.SIGNAL('triggered()'), self.updateTF2)

		if construct:
			self.gridLayout = QtGui.QGridLayout(self)
			self.gridLayout.setMargin(0)
			
			self.verticalLayout = QtGui.QVBoxLayout()
			self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
			
			# Add keyboard shortcut to select all account boxes
			QtGui.QShortcut(QtGui.QKeySequence('Ctrl+A'), self.mainwindow, self.SelectAllAccounts)

			QtCore.QMetaObject.connectSlotsByName(self)

		self.updateAccountBoxes()

	def changeMainWindowView(self):
		self.mainwindow.changeView()

	def updateAccountBoxes(self):
		# Get selected accounts and remove all account boxes
		checkedbuttons = []
		for widget in self.accountButtons:
			if widget.isChecked():
				checkedbuttons.append(str(widget.text()))
			widget.close()
			del widget

		self.accountButtons = []
		row = 0
		column = 0
		numperrow = int(self.settings.get_option('Settings', 'ui_no_of_columns'))
		ui_account_box_font_size = self.settings.get_option('Settings', 'ui_account_box_font_size')
		ui_account_box_icon_size = int(self.settings.get_option('Settings', 'ui_account_box_icon_size'))
		ui_account_box_icon = self.settings.get_option('Settings', 'ui_account_box_icon')

		# Sort account boxes alphabetically
		sortedlist = []
		for account in list(Set(self.settings.get_sections()) - Set(['Settings'])):
			if self.settings.get_option(account, 'account_nickname') != '':
				sortedlist.append((self.settings.get_option(account, 'account_nickname'), account))
			else:
				sortedlist.append((self.settings.get_option(account, 'steam_username'), account))

		for account in sorted(sortedlist):
			accountname = account[0]
			commandLinkButton = QtGui.QCommandLinkButton(self)
			commandLinkButton.setMinimumSize(QtCore.QSize(1, 1))
			commandLinkButton.setObjectName(self.settings.get_option(account[1], 'steam_username'))
			icon = QtGui.QIcon()
			if ui_account_box_icon != '':
				icon.addPixmap(QtGui.QPixmap(ui_account_box_icon))
			else:
				icon.addPixmap(QtGui.QPixmap(returnResourcePath('images/unselected_button.png')), QtGui.QIcon.Selected, QtGui.QIcon.Off)
				icon.addPixmap(QtGui.QPixmap(returnResourcePath('images/selected_button.png')), QtGui.QIcon.Selected, QtGui.QIcon.On)
			commandLinkButton.setIcon(icon)
			commandLinkButton.setIconSize(QtCore.QSize(ui_account_box_icon_size, ui_account_box_icon_size))
			commandLinkButton.setCheckable(True)
			commandLinkButton.setChecked((accountname in checkedbuttons or 
										 self.settings.get_option(account[1], 'steam_username') in self.chosenSelectGroupAccounts)
										 and self.settings.get_option(account[1], 'steam_username') not in self.chosenDeselectGroupAccounts
										 )
			commandLinkButton.setStyleSheet('font: %spt "TF2 Build";' % ui_account_box_font_size)
			commandLinkButton.setText(accountname)
			self.accountButtons.append(commandLinkButton)
			self.gridLayout.addWidget(commandLinkButton, row, column, 1, 1)
			column += 1
			if column == numperrow:
				row += 1
				column = 0

	def mousePressEvent(self, event):
		button = event.button()
		# Uncheck all account boxes on mouse right click
		if button == 2:
			for account in self.accountButtons:
				account.setChecked(False)
	
	def SelectAllAccounts(self):
		for account in self.accountButtons:
			account.setChecked(True)
	
	def returnSelectedAccounts(self):
		selectedList = []
		for account in self.accountButtons:
			if account.isChecked():
				selectedList.append(str(account.objectName()))
		self.emit(QtCore.SIGNAL('returnedSelectedAccounts(PyQt_PyObject)'), selectedList)

	def startDropLog(self, account):
		if self.settings.get_option('Settings', 'auto_add_to_log') == 'True':
			self.emit(QtCore.SIGNAL('startDropLog(PyQt_PyObject)'), account)

	def stopDropLog(self, account):
		self.emit(QtCore.SIGNAL('stopDropLog(PyQt_PyObject)'), account)
	
	def openAccountDialog(self, editAccount=False):
		if editAccount:
			checkedbuttons = []
			for widget in self.accountButtons:
				if widget.isChecked():
					checkedbuttons.append('Account-' + str(widget.objectName()))
			if len(checkedbuttons) == 0:
				QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to edit')
			else:
				dialogWindow = AccountDialogWindow(accounts=checkedbuttons)
				dialogWindow.setModal(True)
				dialogWindow.exec_()
				self.updateAccountBoxes()
		else:
			dialogWindow = AccountDialogWindow()
			dialogWindow.setModal(True)
			dialogWindow.exec_()
			self.updateAccountBoxes()

	def deleteAccounts(self):
		checkedbuttons = []
		for widget in self.accountButtons:
			if widget.isChecked():
				checkedbuttons.append(str(widget.objectName()))
		if len(checkedbuttons) == 0:
			QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to delete')
		else:
			reply = QtGui.QMessageBox.warning(self, 'Warning', 'Are you sure to want to delete these accounts?', QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
			if reply == QtGui.QMessageBox.Yes:
				for account in checkedbuttons:
					self.settings.remove_section('Account-' + account)
				self.updateAccountBoxes()

				self.settings.flush_configuration()
	
	def selectGroups(self):
		dialogWindow = GroupsDialogWindow()
		dialogWindow.setModal(True)
		dialogWindow.exec_()
		self.chosenSelectGroupAccounts, self.chosenDeselectGroupAccounts = dialogWindow.returnAccounts()
		self.updateAccountBoxes()
		# Remove group accounts from selection after updating window
		self.chosenSelectGroupAccounts = []
		self.chosenDeselectGroupAccounts = []
	
	def startUpAccounts(self, action):
		easy_sandbox_mode = self.settings.get_option('Settings', 'easy_sandbox_mode')
		self.commands = []

		# Get selected accounts
		checkedbuttons = []
		for widget in self.accountButtons:
			if widget.isChecked():
				checkedbuttons.append(str(widget.objectName()))

		# Error dialogs if no accounts selected
		if len(checkedbuttons) == 0:
			if action == 'idle':
				QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to idle')
			elif action == 'idle_unsandboxed':
				QtGui.QMessageBox.information(self, 'No account selected', 'Please select an account to idle')
			elif action == 'start_steam':
				QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to start Steam with')
			elif action == 'start_TF2':
				QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to start TF2 with')

		# Error dialog if > 1 accounts selected and trying to run them all unsandboxed
		elif action == 'idle_unsandboxed' and len(checkedbuttons) > 1:
			QtGui.QMessageBox.information(self, 'Too many accounts selected', 'Please select one account to idle')
		# Error dialog if easy sandbox mode is on and program isn't run with elevated privileges
		elif easy_sandbox_mode == 'yes' and action != 'idle_unsandboxed' and not self.runAsAdmin():
			QtGui.QMessageBox.information(self, 'Easy sandbox mode requires admin', 'TF2Idle requires admin privileges to create/modify sandboxes. Please run the program as admin.')
		else:
			steamlocation = self.settings.get_option('Settings', 'steam_location')
			secondary_steamapps_location = self.settings.get_option('Settings', 'secondary_steamapps_location')
			sandboxielocation = self.settings.get_option('Settings', 'sandboxie_location')
			low_priority_mode = self.settings.get_option('Settings', 'low_priority_mode') == 'yes'

			for account in checkedbuttons:
				username = self.settings.get_option('Account-' + account, 'steam_username')
				password = self.settings.get_option('Account-' + account, 'steam_password')
				sandboxname = self.settings.get_option('Account-' + account, 'sandbox_name')
				if self.settings.get_option('Account-' + account, 'sandbox_install') == '' and easy_sandbox_mode == 'yes':
					sandbox_install = secondary_steamapps_location
				else:
					sandbox_install = self.settings.get_option('Account-' + account, 'sandbox_install')
				# Check if account has launch parameters that override main parameters
				if self.settings.has_option('Account-' + account, 'launch_options') and self.settings.get_option('Account-' + account, 'launch_options') != '':
					steamlaunchcommand = self.settings.get_option('Account-' + account, 'launch_options')
				else:
					steamlaunchcommand = self.settings.get_option('Settings', 'launch_options')

				if not self.sandboxieINIIsModified and easy_sandbox_mode == 'yes':
					Sandboxie.backupSandboxieINI()
					self.mainwindow.sandboxieINIHasBeenModified()

				if action == 'idle':
					command = r'"%s/Steam.exe" -login "%s" "%s" -applaunch 440 %s' % (sandbox_install, username, password, steamlaunchcommand)
					if easy_sandbox_mode == 'yes' and self.settings.get_option('Account-' + account, 'sandbox_install') == '':
						self.commandthread.addSandbox('TF2Idle' + username)
						self.createdSandboxes.append(username)
						if low_priority_mode:
							command = r'"%s/Start.exe" /box:%s cmd /c start /low "" %s' % (sandboxielocation, 'TF2Idle' + username, command)
						else:
							command = r'"%s/Start.exe" /box:%s %s' % (sandboxielocation, 'TF2Idle' + username, command)
					else:
						if low_priority_mode:
							command = r'"%s/Start.exe" /box:%s cmd /c start /low "" %s' % (sandboxielocation, sandboxname, command)
						else:
							command = r'"%s/Start.exe" /box:%s %s' % (sandboxielocation, sandboxname, command)
					# Start logging automatically
					self.startDropLog(account)

				elif action == 'idle_unsandboxed':
					if low_priority_mode:
						command = r'cmd /c start /low "" "%s/Steam.exe" -login "%s" "%s" -applaunch 440 %s' % (steamlocation, username, password, steamlaunchcommand)
					else:
						command = r'"%s/Steam.exe" -login "%s" "%s" -applaunch 440 %s' % (steamlocation, username, password, steamlaunchcommand)
					# Start logging automatically
					self.startDropLog(account)

				elif action == 'start_steam':
					command = r'"%s/Steam.exe" -login "%s" "%s"' % (sandbox_install, username, password)
					if easy_sandbox_mode == 'yes' and self.settings.get_option('Account-' + account, 'sandbox_install') == '':
						self.commandthread.addSandbox('TF2Idle' + username)
						self.createdSandboxes.append(username)
						if low_priority_mode:
							command = r'"%s/Start.exe" /box:%s cmd /c start /low "" %s' % (sandboxielocation, 'TF2Idle' + username, command)
						else:
							command = r'"%s/Start.exe" /box:%s %s' % (sandboxielocation, 'TF2Idle' + username, command)
					else:
						if low_priority_mode:
							command = r'"%s/Start.exe" /box:%s cmd /c start /low "" %s' % (sandboxielocation, sandboxname, command)
						else:
							command = r'"%s/Start.exe" /box:%s %s' % (sandboxielocation, sandboxname, command)

				elif action == 'start_TF2':
					command = r'"%s/Steam.exe" -login "%s" "%s" -applaunch 440' % (sandbox_install, username, password)
					if easy_sandbox_mode == 'yes' and self.settings.get_option('Account-' + account, 'sandbox_install') == '':
						self.commandthread.addSandbox('TF2Idle' + username)
						self.createdSandboxes.append(username)
						if low_priority_mode:
							command = r'"%s/Start.exe" /box:%s cmd /c start /low "" %s' % (sandboxielocation, 'TF2Idle' + username, command)
						else:
							command = r'"%s/Start.exe" /box:%s %s' % (sandboxielocation, 'TF2Idle' + username, command)
					else:
						if low_priority_mode:
							command = r'"%s/Start.exe" /box:%s cmd /c start /low "" %s' % (sandboxielocation, sandboxname, command)
						else:
							command = r'"%s/Start.exe" /box:%s %s' % (sandboxielocation, sandboxname, command)

				self.commands.append(command)
			self.commandthread = Sandboxie.SandboxieThread()
			self.commandthread.addCommands(self.commands)
			self.commandthread.start()
	
	def openBackpack(self):
		# Get selected accounts
		checkedbuttons = []
		for widget in self.accountButtons:
			if widget.isChecked():
				checkedbuttons.append(str(widget.objectName()))

		# Error dialog if no accounts selected
		if len(checkedbuttons) == 0:
			QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to view backpack')
		else:
			backpack_viewer = self.settings.get_option('Settings', 'backpack_viewer')
			if backpack_viewer == 'Backpack.tf':
				url = 'http://backpack.tf/id/%(ID)s'
			elif backpack_viewer == 'OPTF2':
				url = 'http://optf2.com/tf2/user/%(ID)s'
			elif backpack_viewer == 'Steam':
				url = 'http://steamcommunity.com/id/%(ID)s/inventory'
			elif backpack_viewer == 'TF2B':
				url = 'http://tf2b.com/tf2/%(ID)s'
			elif backpack_viewer == 'TF2Items':
				url = 'http://www.tf2items.com/id/%(ID)s'
			for account in checkedbuttons:
				webbrowser.open(url % {'ID': self.settings.get_option('Account-' + account, 'steam_vanityid')})
	
	def modifySandboxes(self, action):
		# Get selected accounts
		checkedbuttons = []
		for widget in self.accountButtons:
			if widget.isChecked():
				checkedbuttons.append(str(widget.objectName()))

		# Error dialog if no accounts selected
		if len(checkedbuttons) == 0:
			if action == '/terminate':
				QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to terminate its sandbox')
			else:
				QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account to delete its sandbox contents')
		else:
			sandboxie_location = self.settings.get_option('Settings', 'sandboxie_location')
			for account in checkedbuttons:
				if account in self.createdSandboxes:
					command = r'"%s/Start.exe" /box:%s %s' % (sandboxie_location, 'TF2Idle' + account, action)
					subprocess.call(command)
					self.createdSandboxes.remove(account)
				elif self.settings.get_option('Account-' + account, 'sandbox_name') != '':
					command = r'"%s/Start.exe" /box:%s %s' % (sandboxie_location, self.settings.get_option('Account-' + account, 'sandbox_name'), action)
					subprocess.call(command)
				# Stop logging automatically
				self.stopDropLog(account)

	def startProgram(self):
		# Get selected accounts
		checkedbuttons = []
		for widget in self.accountButtons:
			if widget.isChecked():
				checkedbuttons.append(str(widget.objectName()))

		# Error dialog if no accounts selected
		if len(checkedbuttons) == 0:
			QtGui.QMessageBox.information(self, 'No accounts selected', 'Please select at least one account sandbox to launch a program in')
		else:
			program = QtGui.QFileDialog.getOpenFileName(self, 'Choose program to launch sandboxed', filter = 'Programs (*.exe *.bat *.msi *.jar)')
			if program:
				sandboxie_location = self.settings.get_option('Settings', 'sandboxie_location')
				for account in checkedbuttons:
					if account in self.createdSandboxes:
						accountname = 'TF2Idle' + account
					elif self.settings.get_option('Account-' + account, 'sandbox_name') != '':
						accountname = self.settings.get_option('Account-' + account, 'sandbox_name')
					command = r'"%s/Start.exe" /box:%s %s' % (sandboxie_location, self.settings.get_option('Account-' + account, 'sandbox_name'), program)
					subprocess.call(command)

	def updateTF2(self):
		def Dialog(title, message):
			QtGui.QMessageBox.information(self, title, message)

		self.thread = Worker()
		QtCore.QObject.connect(self.thread, QtCore.SIGNAL('returnMessage'), Dialog)
		QtCore.QObject.connect(self.thread, QtCore.SIGNAL('StartedCopyingTF2'), curry(self.changeTF2LockState, lock=True))
		QtCore.QObject.connect(self.thread, QtCore.SIGNAL('FinishedCopyingTF2'), curry(self.changeTF2LockState, lock=False))
		self.thread.start()

	def changeTF2LockState(self, lock):
		if lock:
			self.copyingTF2 = True
		else:
			self.copyingTF2 = False
		self.updateWindow()

	def runAsAdmin(self):
		try:
			is_admin = os.getuid() == 0
		except AttributeError:
			is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
		return is_admin