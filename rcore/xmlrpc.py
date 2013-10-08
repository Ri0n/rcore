from __future__ import absolute_import

import xmlrpclib
import urlparse

from xml.sax.saxutils import escape
from twisted.web import server, xmlrpc, http, resource
from twisted.python import failure, log
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionRefusedError
from twisted.internet.ssl import DefaultOpenSSLContextFactory

from rcore import config, user, Core
from rcore.error import getFailureFor, RegularError, InternalError, NoRPCProxiesLeft
from rcore.rpctools import RPCService
from rcore.context import Context, waitForDeferred, makeContext, setCurrentContext, deleteContext
from twisted.web.xmlrpc import Fault

_defaultUser = None

def listen(url, site):
    global _defaultUser
    data = urlparse.urlparse(url, "http", False)
    if data.scheme == "https":
        query = urlparse.parse_qs(data.query)
        reactor.listenSSL(
            int(data.port or 443),
            site,
            DefaultOpenSSLContextFactory(
                query["private"][0],
                query["cert"][0]
            ),
            interface=data.hostname or "127.0.0.1"
        )
    else:
        reactor.listenTCP(
            int(data.port or 80),
            site,
            interface=data.hostname or "127.0.0.1"
        )
    if data.username and data.password:
        _defaultUser = user.User(data.username, data.password, "Default User")
    

class Site(server.Site):
    
    def __init__(self, *args, **kwargs):
        server.Site.__init__(self, *args, **kwargs)
        self._activeState = True

    def startFactory(self):
        server.Site.startFactory(self)
        log.msg("Init complete. listening for requests..")
        
    def setActiveState(self, state, comment = ""):
        self._activeState = state
        self._activeStateComment = comment
        
    def render(self, resrc):
        if self._activeState:
            return server.Site.render(self, resrc)
        
        if self.method == "HEAD":
            self.setResponseCode(http.SERVICE_UNAVAILABLE)
            self.write('')
        else:
            body = resource.ErrorPage(
                http.SERVICE_UNAVAILABLE,
                "Service is temporary disabled. Be patient",
                self._activeStateComment).render(self)
            self.setHeader('content-length', str(len(body)))
            self.write(body)
        self.finish()


class XMLRPC(xmlrpc.XMLRPC):
    """PAMM Request demon"""

    def auth(self, user, passwd):
        global _defaultUser
        if _defaultUser:
            return _defaultUser.auth(passwd, user)
        return True

    def render_POST(self, request):
        user = request.getUser()
        passwd = request.getPassword()

        if user=='' and passwd=='':
            request.setResponseCode(http.UNAUTHORIZED)
            return 'Authorization required!'

        if not self.auth(user, passwd):
            request.setResponseCode(http.UNAUTHORIZED)
            return 'Authorization failed!'

        request.content.seek(0, 0)
        request.setHeader("content-type", "text/xml")
        try:
            args, functionPath = xmlrpclib.loads(request.content.read(), use_datetime=True)
        except Exception as e:
            f = xmlrpclib.Fault(self.FAILURE, "Can't deserialize input: %s" % (e,))
            self._cbRender(f, request)
        else:
            try:
                function = self._getFunction(functionPath)
            except xmlrpclib.Fault as f:
                self._cbRender(f, request)
            else:
                def closeReq(result):
                    deleteContext(requestId)
                    if isinstance(result, failure.Failure) and not isinstance(result.value, xmlrpclib.Fault):
                        if isinstance(result.value, RegularError):
                            log.msg("Request error: " + repr(result.value))
                            return xmlrpclib.Fault(result.value.code, str(result.value))
                        log.msg("Request finished with unexpected error. see traceback below")
                        result.printTraceback()
                        return xmlrpclib.Fault("INTERNAL_ERROR", str(result.value))
                    
                    return result
                
                requestId = makeContext(Request, request, (functionPath, args))
                setCurrentContext(requestId)
                d = defer.maybeDeferred(function, *args)
                d.addBoth(closeReq)
                d.addErrback(self._ebRender)
                d.addCallback(self._cbRender, request)
        return server.NOT_DONE_YET


class Request(Context):

    def __init__(self, httpRequest, callParams):
        super(Request, self).__init__()
        self.initiator = httpRequest.getUser()
        log.msg("XML-RPC from %s: " % self.initiator + callParams[0] + str(callParams[1]))
        

class Service(RPCService):
    _namespaceSeparator = "."
    _alertable = False
    
    """If set to True, current core context will be restored after XML-RPC request complete"""
    restoreContext = True
    
    def __init__(self, methodPath = ""):
        self._methodPath = methodPath
        
    def __getattr__(self, name):
        mpath = self._methodPath and self._namespaceSeparator.join([self._methodPath, name]) or name
        return self.__class__(mpath)
    
    @defer.deferredGenerator
    def __call__(self, *params):
        if self._methodPath:
            try:
                print "XML-RPC %s:" % self.__class__.__name__, self._methodPath, params
                proxy = self._getProxy()
                proxy.queryFactory.noisy = False
                wfd = waitForDeferred(proxy.callRemote(self._methodPath, *params))
                wfd.setRestoreContext(self.restoreContext)
                yield wfd
                result = wfd.getResult()
                yield result
                return
            except Exception as e:
                errStr = str(e) if isinstance(e, Fault) else getFailureFor(e).getTraceback()
                msg = "Internal XML-RPC Failed: " + self.__class__.__name__ + ":" + self._methodPath + \
                    str(params) + "\n" + errStr
                log.msg(msg)
                self.__class__._lastError = msg
                if self._alertable:
                    Core.instance().getRPCService("alarm").notify([msg,
                        "<div style='color:#ff0000;font-weight:bold'>%s</div>" % escape(self.__class__._lastError).replace("\n", "<br/>")], ["error"])
                raise
        else:
            raise InternalError("method name is not given")
            
    def _getProxy(self):
        raise NotImplementedError("_getProxy must be implemented in an inherited class")
        
        
class ExchangableService(Service):
    def _getProxies(self):
        raise NotImplementedError("_getProxies must be implemented in an inherited class")
    
    def _getProxy(self):
        cls = self.__class__
        def updateProxies(sender):
            cls._proxies = self._getProxies()
            cls._currentProxyIndex = 0
            cls._needNextProxy = False
            
        if not hasattr(cls, "_proxies"):
            updateProxies()
            config.connect("changed", updateProxies)
            
        if cls._needNextProxy:
            nextIndex = (cls._currentProxyIndex + 1) % len(cls._proxies)
            if nextIndex == cls.firstProxy:
                raise NoRPCProxiesLeft("all proxies of %s are down" % self.__class__.__name__)
            cls._currentProxyIndex = nextIndex
        else: # remember first called proxy before failures
            cls.firstProxy = cls._currentProxyIndex
            
        return cls._proxies[cls._currentProxyIndex]
    
    def __call__(self, *params):
        
        def checkConnection(failure):
            failure.trap(ConnectionRefusedError)
            print "trying next proxy if available"
            self.__class__._needNextProxy = True
            return Service.__call__(self, *params).addErrback(checkConnection)
        
        self.__class__._needNextProxy = False
        d = Service.__call__(self, *params)
        d.addErrback(checkConnection)
        return d
