from __future__ import absolute_import

import os
import json
from watchdog.events import PatternMatchingEventHandler
from rcore.observer import Observable

class ConfigWatcher(PatternMatchingEventHandler):
    def __init__(self, cb, filename):
        self.conf_change_cb = cb
        super(ConfigWatcher, self).__init__([filename], ignore_directories=True)

    def on_created(self, e):
        self.conf_change_cb()

    def on_modified(self, event):
        self.conf_change_cb()


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
        with open(self.configFile, "rb") as f:
            try:
                self.config = json.load(f)
            except ValueError as e:
                print("Config syntax error: " + str(e))

        from rcore.core import Core
        Core.instance().fs_watch.schedule(ConfigWatcher(self.onChanged, os.path.basename(self.configFile)), os.path.dirname(self.configFile))

    def onChanged(self):
        try:
            self.reload()
            print "Config reload complete. Start calling change handlers"
            self.emit("changed")
        except Exception, e:
            print "ERROR: Something wrong with new config file. staying with old one: "+repr(e)
            self._changeChecker.start(self.changeCheckInterval, False)

    def __call__(self):
        return self.config

if "config" not in globals():
    config = Config()
