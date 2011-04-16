from __future__ import absolute_import

import os
import inotifyx
from twisted.internet import task

from rcore.xmlobject import XMLFile
from rcore.observer import Observable

class Config(Observable):

    changeCheckInterval = 5

    def __init__(self):
        Observable.__init__(self)
        self.fd = inotifyx.init()
        self.wd = None
        self.changeHandlers = []
        self.config = None
        self._changeChecker = task.LoopingCall(self._checkInotify)

    def reload(self, configFile = None):
        if configFile:
            self.configFile = configFile
            if not os.path.exists(self.configFile):
                raise Exception("Config file %s not found" % self.configFile)
        self.config = XMLFile(path=self.configFile)
        self._changeChecker.start(self.changeCheckInterval, True)

    def _checkInotify(self):

        def tryReload():
            self._changeChecker.stop()
            try:
                self.reload()
                print "Config reload complete. Start calling change handlers"
                self.emit("changed")
                #map(lambda h:h(), self.changeHandlers)
            except Exception, e:
                print "ERROR: Something wrong with new config file. staying with old one: "+repr(e)
                self._changeChecker.start(self.changeCheckInterval, False)

        if not self.wd:
            try:
                self.wd = inotifyx.add_watch(self.fd, self.configFile,
                                       inotifyx.IN_IGNORED | inotifyx.IN_MODIFY)
            except Exception, e:
                print "Adding config file watch failed(deleted?). next try in "\
                      "%d seconds: %s" % (self.changeCheckInterval, repr(e))

        events = inotifyx.get_events(self.fd, 0)
        for e in events: print e, " "

        if len(events) and events[-1:][0].mask & inotifyx.IN_IGNORED: # watch removed
            self.wd = None
            print "Config watch removed. resetting..."
            tryReload()

        elif len([e for e in events if e.mask & inotifyx.IN_MODIFY]):
            print "Config changed. reloading..."
            tryReload()

    def __call__(self):
        return self.config.root

if "config" not in globals():
    config = Config()
