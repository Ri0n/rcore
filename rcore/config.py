# Copyright (c) 2013, Il'inykh Sergey
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL IL'INYKH SERGEY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# auto reloading config handling class with pubsub inside
#
# config should be stored in json format
# config file is reloaded when changed or recreated
# config class sends "changed" event via public subscribe
#
# usage:
# from rcore import config
# config.connect("changed", my_callback)  # my_callback will be called when config reloaded (details in observer.py)
# config()["var1"]["subvar2"]  # access to config's data

from __future__ import absolute_import

import os
import json
import re
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

    def stopWatching(self):
        if self.observer and self.observer.isAlive():
            self.observer.stop()

    def reload(self, configFile = None):
        if not os.path.exists(configFile):
            raise Exception("Config file %s not found" % str(configFile))
        with open(configFile, "rb") as f:
            try:
                data = f.read()
                data = re.sub('^\s*(/\*.*\*/\s*|//.*)$', "", data, flags=re.M)
                self.config = json.loads(data)
                self.configFile = configFile
                print("Config file %s is loaded successfully" % os.path.abspath(self.configFile))
                if not self.observer:
                    self.observer = Observer()
                    self.observer.schedule(ConfigWatcher(self._onChanged, os.path.basename(self.configFile)),
                                           os.path.dirname(self.configFile), recursive=False)
                    self.observer.start()
                return True

            except ValueError as e:
                print("Config syntax error: " + str(e))
                if self.config is None:
                    raise SyntaxError("Config syntax error: " + str(e))
        return False

    def _onChanged(self):
        try:
            if self.reload(self.configFile):
                print ("Config reload complete. Start calling change handlers")
                self.emit("changed")
        except Exception as e:
            print ("ERROR: Something wrong with new config file. staying with old one: "+repr(e))

    def __call__(self):
        return self.config

    def save(self, filename=None):
        filename = filename or self.configFile
        d = os.path.dirname(filename)
        if not os.path.exists(d):
            os.makedirs(d, 0o755)  # hardcoded chmod?
        with open(filename, "w") as f:
            json.dump(self.config, f, indent=4)

if "config" not in globals():
    config = Config()
