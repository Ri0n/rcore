from __future__ import absolute_import

import sys
from inspect import isclass
from twisted.python import failure


class RegularError(Exception):
    
    code = "UNKNOWN_ERROR"

    def __init__(self, value = ""):
        self.value = value

    def __str__(self):
        return str(self.toText()[1])
    
    def __repr__(self):
        return self.__class__.__name__ + "(" + repr(self.toText()[1]) + ")"

    def toText(self, addText = ""):
        return self.code, str(self.value) + addText

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
        
