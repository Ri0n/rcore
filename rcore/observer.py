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

'''
Created on 29.09.2010

@author: rion

implementation of public subscribe design pattern

to use it, inherit your classes from Observable to be able emit events and to connect to events of other classes.

to emit event just call self.emit("event_name", args..)
to connect use obj.connect("event_name", callback)  # notice sender's instance will be passed to callback as 1st arg
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
        except Exception as e:
            print ("disconnect failed: " + repr(e))
    
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
