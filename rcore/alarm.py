from __future__ import absolute_import

from twisted.web.xmlrpc import Proxy

from rcore.config import config
from rcore.xmlrpc import Service

class Alarm(Service):
    restoreContext = False
    
    def _getProxy(self):
        return Proxy(config().hermes.url.encode("utf-8"))
