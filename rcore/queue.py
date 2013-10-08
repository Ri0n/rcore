from __future__ import absolute_import

from twisted.internet import reactor, defer
from twisted.python import log

from rcore.context import waitForDeferred, getCurrentContextId,\
    setCurrentContext
from rcore.error import getFailureFor, ContextError, RegularError, InternalError

# in order to use this class in some context-free place like Core
# you have to create context and set it as current
#
# This class is something like extended DeferredList which stores items itself
# in resultset and has advanced settings and methods


class DQueue(object):
    """
    Does some asynchronous work for list of items.

    The work may return Deferred or some result or throw exception.
    it's preferable to throw exceptions based on RegularException to be shown in the log.
    when all items handled or callback will be called with results list as argument.
    results has a form like [[bool success, result1, item1], [bool success, result2, item2], ...].
    in case of failures stored result item is an instance of Failure.

    Example of usage:

    def handle_results(results):
        for r in results:
            if results[0]:  # success
                with open("file"+str(results[2]), "w") as f
                    f.write(results[1])

    q = DQueue([1,2,3], lambda item, url: getPage(url+"/"+str(item), url)
    d = q.run()
    d.addCallback(handle_results)

    """
    def __init__(self, items, work, *args, **kw):
        """
        @param items: list of items
        @param work: Callable wor
        @param args: list of args passed to work
        @param kw: dict of kwargs passed to work
        @return:
        """
        self._items = items[:]
        self._work = work
        self._args = args
        self._kw = kw
        self._results = []
        self._stopOnFailure = False
        self._success = True
        self._successCount = 0
        self._lastResult = None
        self._firstError = None

    def setStopOnFailure(self, status=True):
        """
        if True stops queue handling on first exception calling errback with Failure
        @param status: bool on/off stop on failure
        """
        self._stopOnFailure = status

    @defer.deferredGenerator
    def run(self):
        while len(self._items):
            item = self._items.pop(0)
            wfd = waitForDeferred(defer.maybeDeferred(self._work, item, *self._args, **self._kw))
            yield wfd
            try:
                result = wfd.getResult()
                self._successCount += 1
                self._lastResult = [True, result, item]
                self._results.append(self._lastResult)
            except Exception as e:
                self._success = False
                failure = getFailureFor(e)
                if not failure.check(RegularError):
                    failure.printTraceback()
                if not self._firstError:
                    self._firstError = (failure, item)
                self._lastResult = [False, failure, item]
                self._results.append(self._lastResult)
                if self._stopOnFailure:
                    raise
                    #yield self._results
                    #return
                    
        yield self._results

    def stop(self):
        self._items = []
        
    def isSuccess(self):
        return self._success
    
    def successCount(self):
        return self._successCount
    
    def lastResult(self):
        return self._lastResult
    
    def firstError(self):
        return self._firstError




# Action queue class
#
# its very similar to deferred queue (DQueue) but have no finish callback
# and will call setted callback or errback for each element
class ActionQueueItem:
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.identifier = None
        self.defer = None
        self.contextId = None
        self.active = False
        
    def setIdentifier(self, i):
        """
        Identifier allows search and clean this item in the queue
        """
        self.identifier = i
        return self
        
    def getDeferred(self):
        if not self.defer:
            self.defer = defer.Deferred()
        return self.defer
    
    def toTop(self):
        self.queue.moveToTop(self)
    
    def saveContext(self):
        self.contextId = getCurrentContextId()
        return self
    
    def invoke(self, defualtCallback, defaultErrback):
        from rcore import Core
        if Core.instance().debugEnabled():
            print("ActionQueue: Executing job from queue: " + str(self.func))
        self.active = True
        d = defer.maybeDeferred(self.func, *self.args, **self.kwargs)
        if self.defer:
            if Core.instance().debugEnabled():
                print("ActionQueue: adding own callback")
            d.addCallbacks(self.defer.callback, self.defer.errback)
        else:
            if Core.instance().debugEnabled():
                print("ActionQueue: adding default callback")
            d.addCallbacks(defualtCallback, defaultErrback)
        return d
            
    def isActive(self):
        """
        Checks if execution started all already finished.

         False means this item still wait in the queue
        """
        return self.active


class ActionQueue(list):
    """
    It's more like endless queue.

    it sleeps while queue is empty and execute some action when it's queued
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor accepts standard for `list` args
        """
        list.__init__(self, *args, **kwargs)
        self._errback = self._callback = lambda result: result
        self.active = False;
        self.checkPlanned = False
        self.finishWaiter = None
        
    def append(self, func, *args, **kwargs):
        """
        Enqueue some action `func`.

        Passed func will be executed with passed args and kwargs (no other args passed to func)
        You can get deferred from returned action and do with it what you want
        @param func: Callable
        @param args: list of args for callable
        @param kwargs: dict of kwargs for callable
        @return: ActionQueueItem
        """
        from rcore import Core
        if Core.instance().debugEnabled():
            print("ActionQueue: Adding job to queue: " + str(func))
        item = ActionQueueItem(func, args, kwargs)
        list.append(self, item)
        if not self.checkPlanned:
            self.checkPlanned = True
            if Core.instance().debugEnabled():
                print("ActionQueue: Planning check queue")
            reactor.callLater(0, self.checkQueue)
        return item
        
    def checkQueue(self):
        from rcore import Core
        
        def finished(result, item):
            if Core.instance().debugEnabled():
                print("ActionQueue: job finished: " + str(result))
            
            self.active = False;
            reactor.callLater(0, self.checkQueue)
            if item.contextId:
                try:
                    setCurrentContext(item.contextId)
                except Exception as e:
                    print("ActionQueue: Unable to restore context. "
                          "this should never happen and may damage other context and their data.")
                    print("ActionQueue: Actual result was: " + str(result))
                    return ContextError(str(e)).toFailure()
            #import gc
            #from rcore import Context
            #print "GARBAGE: ", gc.garbage, gc.get_referrers([a for a in gc.get_objects() if isinstance(a, Context)][-1])
            #return result
        
        
        if Core.instance().debugEnabled():
            print("ActionQueue: Checking queue: " + (str(len(self)) + " jobs" if len(self) else "empty"))
            
        if len(self):
            if not self.active:
                self.active = True
                item = self.pop(0)
                item.invoke(self._callback, self._errback).addBoth(finished, item)
        else:
            self.checkPlanned = False
            if self.finishWaiter:
                d = self.finishWaiter
                self.finishWaiter = None
                d.callback(None)
            
    def setCallback(self, func = None):
        self._callback = func if hasattr(func, "__call__") else lambda result: result
        
    def setErrback(self, func = None):
        self._errback = func if hasattr(func, "__call__") else lambda result: result
        
    def findByIdentifier(self, id):
        id = id if isinstance(id, (list, tuple, set)) else set([id])
        for i in self:
            if i.identifier in id: return i
        return False
    
    def cleanByIdentifier(self, id):
        id = id if isinstance(id, (list, tuple, set)) else set([id])
        i = 0
        while i < len(self):
            if self[i].identifier in id and not self[i].isActive():
                del self[i]
            else:
                i += 1
    
    def moveToTop(self, item):
        for i in xrange(len(self)):
            if self[i] == item:
                del self[i] # nothing bad if its already 0th item
                self.insert(0, item)
                return
        raise InternalError("Can't move to top not existent ActionQueueItem")
    
    def waitForFinish(self):
        """
        Actually doesn't wait but returns Deferred which is fired when queue is empty.

        You can call this method even on already empty queue with the same result

        @return: Deferred
        """
        if not self.checkPlanned:
            return defer.succeed(None)
        self.finishWaiter = defer.Deferred()
        return self.finishWaiter
