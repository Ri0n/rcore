'''
Created on 29.09.2010

@author: rion
'''
from __future__ import absolute_import

import types
import weakref

from rcore.queue import DQueue
from twisted.internet import defer

class WeakHandler(object):
    def __init__(self, observable, eventName, handler):
        self.observable = observable
        self.eventName = eventName
        if isinstance(handler, types.MethodType):
            self.methodName = handler.__func__.__name__
            self.invoke = self._callMethod
            if handler.__self__:  # bound method
                self.ref = weakref.ref(handler.__self__, self.removeSelf)
            else:
                self.ref = weakref.ref(handler.im_class, self.removeSelf)
        else:
            self.ref = weakref.ref(handler, self.removeSelf)
            self.invoke = self._callFunc
            
    def removeSelf(self, ref):
        self.observable.disconnect(self.eventName, self)
        self.observable = None
        self.ref = None
            
    def _callMethod(self, *args, **kwargs):
        return getattr(self.ref(), self.methodName)(*args, **kwargs)
    
    def _callFunc(self, *args, **kwargs):
        return self.ref()(*args, **kwargs)
        

class Observable(object):
    def connect(self, name, handler):
        if "connections" not in self.__dict__:
            self.__dict__["connections"] = {}
        if name not in self.__dict__["connections"]:
            self.__dict__["connections"][name] = []
        self.__dict__["connections"][name].append(WeakHandler(self, name, handler))
    
    def disconnect(self, eventName, handler = None):
        try:
            if handler:
                self.__dict__["connections"][eventName].remove(handler)
            else:
                del self.__dict__["connections"][eventName]
            return
        except Exception, e:
            print "disconnect failed: " + repr(e)        
    
    def disconnectAll(self):
        self.__dict__["connections"] = {}
    
    def emit(self, name, *args, **kwargs):
        if name in self.__dict__.get("connections", {}) and len(self.__dict__["connections"][name]):
            dq = DQueue(self.__dict__["connections"][name], lambda h: h.invoke(self, *args, **kwargs))
            dq.setStopOnFailure(True)
            return dq.run().addCallback(lambda results: None if dq.isSuccess() else dq.lastResult()[1])
        return defer.succeed(True)


class Observer(object):
    pass
