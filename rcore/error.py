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

import sys
from inspect import isclass
from twisted.python import failure


class RegularError(Exception):
    
    code = "UNKNOWN_ERROR"

    def __init__(self, value = ""):
        self.value = value

    def __str__(self):
        txt = self.toText()[1]
        return txt if isinstance(txt, str) else txt.encode('utf-8')
    
    def __repr__(self):
        return self.__class__.__name__ + "(" + repr(self.toText()[1]) + ")"

    def toText(self, addText = ""):
        return self.code, (self.value if isinstance(self.value, bytes) else unicode(self.value)) + addText

    def toFailure(self, exc_tb = None):
        return failure.Failure(self, exc_tb=exc_tb)


class InternalError(RegularError):
    code = "INTERNAL_ERROR"

class SchedulerError(RegularError):
    code = "SCHEDULER_ERROR"

class InvalidParametersError(RegularError):
    code = "INVALID_PARAMETERS"

class InvalidFilterParametersError(RegularError):
    code = "INVALID_FILTER_PARAMETERS"
    
class NoRPCProxiesLeft(RegularError):
    code = "NO_RPC_PROXIES_LEFT"

class DbError(RegularError):
    code = "UNKNOWN_DB_ERROR"

class DbRecordNotFound(DbError):
    code = "RECORD_NOT_FOUND"
    def __init__(self, table, params, comment = ""):
        super(DbRecordNotFound, self).__init__(comment)
        self.table = table
        self.params = params
        
    def toText(self, addText = ""):
        return self.code, ("%s%s "%(self.table, self.params)) + \
               str(self.value) + addText

class DbLogicError(DbError):
    code = "DB_LOGIC_ERROR"
    
class DbIntegrityError(DbError):
    code = "DB_INTEGRITY_ERROR"
    
    
class ContextError(InternalError):
    code = "CONTEXT_ERROR"
    
class AccessDenied(RegularError):
    code = "ACCESS_DENIED"

def getFailureFor(err):
    if isinstance(err, failure.Failure):
        if not isinstance(err.value, RegularError):
            err.value = InternalError(repr(err.value))
        return err
    if not isinstance(err, RegularError):
        err = InternalError(repr(err))
        tb = sys.exc_info()[2]
        f = err.toFailure(exc_tb=tb)
        del tb
        return f
    return err.toFailure()


__all__ = ["getFailureFor"]

lkeys = locals().keys()
for k in lkeys:
    i = locals()[k]
    if isclass(i) and issubclass(i, RegularError):
        __all__.append(k)
        
