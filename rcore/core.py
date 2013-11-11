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

from __future__ import absolute_import

import os
import sys
import getpass
import locale

from twisted.python import log
from twisted.python.logfile import DailyLogFile
from twisted.internet import reactor, defer

from rcore.context import Context, makeContext, setCurrentContext
from rcore.rpctools import RPCService
from rcore.error import InternalError
from rcore.observer import Observable

_default_locale = locale.getdefaultlocale()[1]


def get_system_username():
    try:
        result = getpass.getuser()
    except (ImportError, KeyError):
        # KeyError will be raised by os.getpwuid() (called by getuser())
        # if there is no corresponding entry in the /etc/passwd file
        # (a very restricted chroot environment, for example).
        return ''
    try:
        result = result.decode(_default_locale)
    except UnicodeDecodeError:
        # UnicodeDecodeError - preventive treatment for non-latin Windows.
        return ''
    return result


def sys2uni(s):
    if isinstance(s, unicode):
        return s
    try:
        return str(s).decode(_default_locale)
    except UnicodeDecodeError:
        return ""


class MainContext(Context):
    def log(self, msg):
        if type(msg) == unicode:
            msg = msg.encode("UTF-8")
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
                from twisted.python import syslog
                try:
                    prefix = config()['log']['syslogprefix']
                except:
                    prefix = os.path.basename(sys.argv[0])
                syslog.startLogging(prefix)
            elif logDest == 'stdout':
                log.startLogging(sys.stdout)
            else:
                dn = os.path.dirname(logDest)
                if not dn:
                    dn = self.get_default_log_dir()
                if dn and not os.path.exists(dn):
                    os.makedirs(dn, 0755)
                log.startLogging(DailyLogFile(os.path.basename(logDest), dn))
        except Exception as e:
            log.startLogging(sys.stdout)
            log.msg("Setting log from config file is failed. continue with logging to stdout: " + str(e))

        from rcore.alarm import Alarm
        self._rpcServices = {}
        self._users = {}
        self.mainContextId = makeContext(MainContext)
        setCurrentContext(self.mainContextId)

    def get_default_log_dir(self):
        """
        Returns directory for storing logs. this function is called if log destination is just file w/o path

        it should be reimplemented in child class if it wants control log destination dir
        """
        return ""
            
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

    def stop(self, msg="no message"):
        """
        emits aboutToStop event
        receivers can delay stop by adding their deferreds by calling Core.delayStop
        """
        def cb(result):
            reactor.stop()
            log.msg("Server stopped")
        from rcore.config import config
        config.stopWatching()
        log.msg("Stopping server: "+msg)
        self.emit("aboutToStop")

        if len(self._deferredStopList):
            dl = defer.DeferredList(self._deferredStopList)
            dl.addBoth(cb)
            defer.waitForDeferred(dl)
        else:
            cb(None)

    def getUser(self, login):
        return self._users[login]
    
    def debugEnabled(self, opt=""):
        from rcore.config import config
        try:
            if config()['debug']['enable']:
                return bool(int(config().debug.get(opt, 0))) if opt else True
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
