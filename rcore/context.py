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

# Context specific classes and functions

# Contexts are some long living instances which can be accessed from everywhere.
# For example you are handling simultaneous xmlrpc requests. And for each request you want to keep some global data
# For each request this data is different (for example login of user of request), so you assign context to request
# and store data there.
# You can inherit from Context and pass it to makeContext for example or to executeInExactContext
#
# this module has it's own waitForDeferred, so you can use deferred generators to always stay in exact context
# which is probably most preferable way of using contexts

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

    def err_log(self, msg, why=None):
        if isinstance(msg, bytes):
            twistedLog.err(self.logPrefix+msg, why)
        else:
            twistedLog.err(msg, why if isinstance(why, str) else why.encode('utf-8'))

    def closeDb(self):
        if self._db:
            try:
                self._db.commit()
            except Exception as e:
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


def err_log(text, why=None):
    getContext().err_log(text, why)

    
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
    """
    Creates instance of passed context constructor and set it current before starting func.
    restores context before return.
    @param func:
    @param constructor:
    @param args:
    @param kw:
    @return:
    """
    from rcore.core import Core
    if Core.instance().debugEnabled():
        print ("Context: execute in context: " + str(func))
    
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

