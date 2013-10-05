from __future__ import absolute_import

import os
import json
from watchdog.events import FileSystemEventHandler, EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED
from watchdog.observers import Observer
from rcore.observer import Observable
from twisted.internet import reactor

class ConfigWatcher(FileSystemEventHandler):
    def __init__(self, cb, filename):
        self.filename = filename
        self.conf_change_cb = cb
        self.callback_scheduled = False
        super(ConfigWatcher, self).__init__()

    def on_cb_schedule_timeout(self):
        self.callback_scheduled = False
        self.conf_change_cb()

    def on_any_event(self, event):
        if self.callback_scheduled or event.is_directory or event.event_type not in\
                (EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED) or os.path.basename(event.src_path) != self.filename:
            return
        self.callback_scheduled = True
        reactor.callLater(1, self.on_cb_schedule_timeout)


class Config(Observable):

    def __init__(self):
        Observable.__init__(self)
        self.wd = None
        self.config = None
        self.observer = None

    def reload(self, configFile = None):
        self.configFile = configFile
        if not os.path.exists(self.configFile):
            raise Exception("Config file %s not found" % self.configFile)
        with open(self.configFile, "rb") as f:
            try:
                self.config = json.load(f)
                print("Config file loaded successfully")
                if not self.observer:
                    self.observer = Observer()
                    self.observer.schedule(ConfigWatcher(self._onChanged, os.path.basename(self.configFile)),
                                           os.path.dirname(self.configFile), recursive=False)
                    self.observer.start()
                    from rcore.core import Core
                    Core.instance().connect("aboutToStop", lambda sender: self.observer.stop())

            except ValueError as e:
                print("Config syntax error: " + str(e))

    def _onChanged(self):
        try:
            self.reload(self.configFile)
            print "Config reload complete. Start calling change handlers"
            self.emit("changed")
        except Exception, e:
            print "ERROR: Something wrong with new config file. staying with old one: "+repr(e)

    def __call__(self):
        return self.config

if "config" not in globals():
    config = Config()
