from __future__ import absolute_import

import os
import json
from watchdog.events import FileSystemEventHandler
from rcore.observer import Observable
from rcore.core import Core


class ConfigWatcher(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config

    def on_created(self, e):
        self.config.onChanged()

    def on_modified(self, event):
        self.config.onChanged()


class Config(Observable):

    changeCheckInterval = 5

    def __init__(self):
        Observable.__init__(self)
        self.wd = None
        self.config = None

    def reload(self, configFile = None):
        self.configFile = configFile
        if not os.path.exists(self.configFile):
            raise Exception("Config file %s not found" % self.configFile)
        with file(self.configFile) as f:
            self.config = json.load(f)
        Core.instance().fs_watch.schedule(ConfigWatcher(self), self.configFile)

    def onChanged(self):
        try:
            self.reload()
            print "Config reload complete. Start calling change handlers"
            self.emit("changed")
        except Exception, e:
            print "ERROR: Something wrong with new config file. staying with old one: "+repr(e)
            self._changeChecker.start(self.changeCheckInterval, False)

    def __call__(self):
        return self.config.root

if "config" not in globals():
    config = Config()
