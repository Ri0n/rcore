# Context specific classes and functions

import time

from twisted.python import log as twistedLog
from twisted.internet import defer

#from rcore.queue import DQueue
from rcore.error import InternalError

_contextData = {
    "contexts" : {},
    "currentId" : -1
}

TwistedsWaitForDeferred = defer.waitForDeferred

class waitForDeferred(TwistedsWaitForDeferred):
    def __init__(self, d):
        self.contextId = getCurrentContextId()
        self.needResoreContext = True
        return TwistedsWaitForDeferred.__init__(self, d)

    def getResult(self):
        if self.needResoreContext:
            setCurrentContext(self.contextId)
        return TwistedsWaitForDeferred.getResult(self)
    
    def setRestoreContext(self, state):
        self.needResoreContext = state
        
defer.waitForDeferred = waitForDeferred # exchange with our improved version

class Context(object):
    def __init__(self):
        self._db = None
        self.initiator = self.__class__.__name__ # we need this for logs. this is default
        self.logPrefix = ""
        self._options = {}
        
    def __del__(self):
        self.log("Deleting job: " + self.__class__.__name__)
        self.closeDb()

    def close(self):
        self.closeDb()

    def log(self, msg):
        twistedLog.msg(self.logPrefix+msg)

    def closeDb(self):
        if self._db:
            try:
                self._db.commit()
            except Exception, e:
                self.log("ignoring db exceptions: " + str(e))
            self._db.close()
            self._db = None

    @property
    def db(self):
        """Instance of db connection for this job"""
        if not self._db:
            from rcore import Core
            self._db = Core.instance().makeDbSession()
        return self._db
    
    def setOption(self, name, value):
        self._options[name] = value
    
    def getOption(self, name, defaultValue = None):
        return self._options.get(name, defaultValue)
    
    
def log(text):
    getContext().log(text)
    
def makeContext(constructor, *args, **kw):
    def getUID():
        while (True):
            h = hash(time.time())
            if h not in _contextData["contexts"]:
                return h
         
    id = getUID()
    _contextData["contexts"][id] = constructor(*args, **kw)
    return id

def deleteContext(id):
    from rcore.core import Core
    del _contextData["contexts"][id]
    if id == _contextData["currentId"]:
        _contextData["currentId"] = Core.instance().mainContextId

def getContext(id = None):
    if id:
        return _contextData["contexts"][id]
    return _contextData["contexts"][_contextData["currentId"]]

def getCurrentContextId():
    return _contextData["currentId"]
    
def setCurrentContext(id):
    if id in _contextData["contexts"]:
        _contextData["currentId"] = id
    else:
        raise InternalError("Context with id = %d is not registered" % id)

def executeInContext(func, *args, **kw):
    return executeInExactContext(func, Context, *args, **kw)

def executeInExactContext(func, constructor, *args, **kw):
    from rcore.core import Core
    if Core.instance().debugEnabled():
        print "Context: execute in context: ", str(func)
    
    def deleteTempContext(result):
        deleteContext(contextId)
        return result
        
    currentId = _contextData["currentId"]
    contextId = makeContext(constructor)
    setCurrentContext(contextId)
    d = defer.maybeDeferred(func, *args, **kw)
    d.addBoth(deleteTempContext)
    setCurrentContext(currentId)
    return d


#@defer.deferredGenerator
#def executeInExactContext(func, constructor, *args, **kw):
#    contextId = makeContext(constructor)
#    setCurrentContext(contextId)
#    wfd = waitForDeferred(defer.maybeDeferred(func, *args, **kw))
#    yield wfd
#    try:
#        result = wfd.getResult()
#        deleteContext(contextId)
#        yield result
#    except:
#        deleteContext(contextId)
#        raise

