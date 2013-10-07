# To change this template, choose Tools | Templates
# and open the template in the editor.
from __future__ import absolute_import

import os
import sys

from twisted.python import log, syslog
from twisted.python.logfile import DailyLogFile
from twisted.internet import reactor, defer

from rcore.context import Context, makeContext, setCurrentContext
from rcore.rpctools import RPCService
from rcore.error import InternalError
from rcore.observer import Observable


class MainContext(Context):
    def log(self, msg):
        log.msg("MC: "+msg)

_coreInstance = None


class Core(Observable):

    @staticmethod
    def instance():
        """
        @rtype : Core
        """
        return _coreInstance
    
    def __init__(self, configFile):
        global _coreInstance
        if _coreInstance:
            raise Exception("Instance of app already exists")
        _coreInstance = self

        self._deferredStopList = []

        from rcore.config import config
        config.reload(configFile)
        try:
            logDest = config()['log']['destination']
            if logDest == 'syslog':
                try:
                    prefix = config()['log']['syslogprefix']
                except:
                    prefix = os.path.basename(sys.argv[0])
                syslog.startLogging(prefix)
            elif logDest == 'stdout':
                log.startLogging(sys.stdout)
            else:
                log.startLogging(DailyLogFile(os.path.basename(logDest), os.path.dirname(logDest)))
        except Exception as e:
            log.startLogging(sys.stdout)
            log.msg("Setting log from config file is failed. continue with logging to stdout: " + str(e))

        from rcore.alarm import Alarm
        self._rpcServices = {}
        self._users = {}
        self.mainContextId = makeContext(MainContext)
        setCurrentContext(self.mainContextId)
            
    def run(self):
        reactor.run()
        
    def registerRPCService(self, name, service):
        assert isinstance(service, RPCService)
        self._rpcServices[name] = service
        
    def getRPCService(self, name):
        return self._rpcServices[name]

    def delayStop(self, d):
        """
        Delay stop of daemon with deferred d
        """
        self._deferredStopList.append(d)

    def stop(self, msg):
        """
        emits aboutToStop event
        receivers can delay stop by adding their deferreds by calling Core.delayStop
        """
        def cb(result):
            reactor.stop()
            log.msg("Server stopped")

        log.msg("Stopping server: "+msg)
        self.emit("aboutToStop")
        if len(self._deferredStopList):
            dl = defer.DeferredList(self._deferredStopList)
            dl.addBoth(cb)
            defer.waitForDeferred(dl)
        else:
            cb()

    def getUser(self, login):
        return self._users[login]
    
    def debugEnabled(self, opt=""):
        try:
            if config()['debug']['enable']:
                return bool(int(config().debug._get(opt, 0))) if opt else True
        except:
            pass
        return False
    
    def hostIp(self):
        import socket
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            pass
        import fcntl
        import struct
        for i in xrange(10):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', "eth%d"%i))[20:24])
            except:
                pass
        raise InternalError("Failed to auto-detect host IP address")
