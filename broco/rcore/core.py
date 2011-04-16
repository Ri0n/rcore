# To change this template, choose Tools | Templates
# and open the template in the editor.
from __future__ import absolute_import

import os
import sys

from twisted.python import log, syslog
from twisted.python.logfile import DailyLogFile
from twisted.internet import reactor

from rcore.globals import appInit, getCore, config, Context, makeContext, setCurrentContext
from rcore.rpctools import RPCService
from rcore.error import InternalError

class MainContext(Context):
    def log(self, msg):
        log.msg("MC: "+msg)

class Core(object):

    @staticmethod
    def instance(cls):
        return getCore()
    
    def __init__(self, configFile):
        appInit(self)
        config.reload(configFile)
        try:
            logDest = config().log.destination
            if logDest == 'syslog':
                try:
                    prefix = config().log.syslogprefix
                except:
                    prefix = os.path.basename(sys.argv[0])
                syslog.startLogging(prefix)
            elif logDest == 'stdout':
                log.startLogging(sys.stdout)
            else:
                log.startLogging(DailyLogFile(os.path.basename(logDest), os.path.dirname(logDest)))
        except:
            log.startLogging(sys.stdout)
            log.msg("Setting log from config file is failed. continue with logging to stdout")
        
        from rcore.alarm import Alarm
        self._rpcServices = {}
        self.registerRPCService("alarm", Alarm())
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

    def emergencyStop(self, msg):
        def alarmCB(result):
            reactor.stop()
        print "CRITICAL ERROR: ", msg, "\n stopping server.."
        d = self.getRPCService("alarm").notify("CRITICAL ERROR: " + msg + "\n\nserver stopped..", ['error'])
        d.addCallback(alarmCB)
        
    def getUser(self, login):
        return self._users[login]
    
    def debugEnabled(self, opt = ""):
        try:
            if config().debug.enable:
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
