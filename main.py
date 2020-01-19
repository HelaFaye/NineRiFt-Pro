import os
from threading import Thread
from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock, mainthread
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty, Property
from kivy.lang import Builder

from utils import tprint, sidethread, specialthread
from fwupd import FWUpd
from fwget import FWGet
from nbcmd import Command
from nbclient import Client


class MainWindow(BoxLayout):
    pass

class CommandScreen(Screen):
    def setcmd(self,c):
        ScriptUI = self.ids['scriptspace']
        ScriptUI.clear_widgets()
        if c == 'changesn':
            changesnui = Builder.load_file("changesn.kv")
            ScriptUI.add_widget(changesnui)
        if c == 'dump':
            dumpui = Builder.load_file("dump.kv")
            ScriptUI.add_widget(dumpui)


class NineRiFt(App):
    def initialize(self):
        self.root_folder = self.user_data_dir
        self.cache_folder = os.path.join(self.root_folder, 'cache')

        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)

        self.conn = Client()
        self.conn.bind(on_error=lambda a,b: tprint(b))

        self.com = Command(self.conn)
        self.fwupd = FWUpd(self.conn)
        self.fwget = FWGet(self.cache_folder)

        self.versel = BooleanProperty(False)
        self.hasextbms = BooleanProperty(False)
        tprint("Don't forget to post a review")

    def build(self):
        self.initialize()
        self.mainwindow = MainWindow()
        return self.mainwindow

    @specialthread
    def connection_toggle(self):
        if self.conn.state == 'connected':
            self.conn.disconnect()
        elif self.conn.state == 'disconnected':
            self.conn.connect()

    @specialthread
    def fwget_select_model(self, screen, mod):
        if mod is not 'Model':
            self.fwget.setModel(mod)
            self.fwget.setRepo("https://files.scooterhacking.org/" + mod + "/fw/repo.json")
            tprint('loading repo')
            self.fwget.loadRepo(self.fwget.repoURL)
            self.fwget_update_versions(screen)
        else:
            tprint('set model to update available versions')

    @specialthread
    def fwget_func(self, dev, version):
        self.fwget.Gimme(dev, version)

    @sidethread
    def executecmd(self, c):
        if self.conn.state == 'connected':
            tprint(c+' execute')
            if c is 'lock':
                self.com.lock()
            if c is 'unlock':
                self.com.unlock()
            if c is 'reboot':
                self.com.reboot()
            if c is 'powerdown':
                self.com.powerdown()
            if c is 'sniff':
                self.com.sniff()
            if c is 'dump':
                if self.com.device is not '':
                    self.com.dump(self.com.device)
                else:
                    tprint('set device first')
            if c is 'info':
                self.com.info()
            if c is 'changesn':
                if self.com.new_sn is not '':
                    self.com.changesn(self.com.new_sn)
                else:
                    tprint('set NewSN first')
        elif self.conn.state == 'disconnected':
            tprint("You aren't connected")

    def selfile_filter(self, mod, vers, dev):
            check = ['!.md5']
            filters = []
            if mod is 'm365':
                if dev is not 'DRV':
                    sf = ['*.bin']
                    filters = sf+check
                elif dev is 'DRV':
                    if vers=='>=141':
                        sf = ['*.bin.enc']
                    elif vers=='<141':
                        sf = ['*.bin']
                    else:
                        sf = ['']
                    filters = sf+check
            if mod is 'm365pro':
                if dev is 'DRV':
                    sf = ['*.bin.enc']
                else:
                    sf = ['*.bin']
                filters = sf+check
            if mod is 'esx' or 'max':
                sf = ['*.bin.enc']
                filters = sf+check
            print('selfile_filter set to %s' % filters)
            return filters

    @mainthread
    def fwget_update_versions(self, screen):
        sel = screen.ids.part.text
        if sel == 'BLE':
            dev = self.fwget.BLE
        elif sel == 'BMS':
            dev = self.fwget.BMS
        elif sel == 'DRV':
            dev = self.fwget.DRV
        else:
            dev = []
        if dev != []:
            versions = [str(e) for e in dev]
            tprint('FWGet Vers. available: '+str(versions))
            screen.ids.version.values = versions

    def select_model(self, mod):
        values = ['BLE', 'DRV', 'BMS']
        if mod.startswith('m365'):
            self.hasextbms = False
            if mod is 'm365':
                self.versel = True
            elif mod is 'm365pro':
                self.versel = False
        if mod is 'esx':
            self.versel = False
            self.hasextbms = True
        if mod is 'max':
            self.versel = False
            self.hasextbms = False
        if self.hasextbms is True:
            try:
                values.append('ExtBMS')
            except:
                print('ExtBMS entry already present')
        if self.hasextbms is False:
            try:
                values.remove('ExtBMS')
            except:
                print('no ExtBMS entry to remove')
        return values

    def on_stop(self):
        self.conn.disconnect()

    @sidethread
    def fwupd_func(self, chooser):
        if len(chooser.selection) != 1:
            tprint('Choose file to flash')
            return
        self.fwupd.Flash(chooser.selection[0])

    @mainthread
    def setprogbar(self, prog, maxprog):
        FlashScreen.setprog(prog, maxprog)

if __name__ == "__main__":
    NineRiFt().run()
