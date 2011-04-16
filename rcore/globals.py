# To change this template, choose Tools | Templates
# and open the template in the editor.
from __future__ import absolute_import

from rcore.config import config #@UnusedImport
from rcore.context import (
    Context, #@UnusedImport
    getContext, #@UnusedImport
    makeContext, #@UnusedImport
    setCurrentContext, #@UnusedImport
    executeInContext, #@UnusedImport
    log #@UnusedImport
)
from rcore.scheduler import scheduler #@UnusedImport

_coreInstance = None

def appInit(core):
    global _coreInstance
    _coreInstance = core

def getCore():
    '''
    @rtype: C{Core}
    '''
    return _coreInstance

__all__ = ["config", "scheduler", "appInit", "getCore", "Context",
           "getContext", "makeContext", "setCurrentContext", "executeInContext", "log"]
