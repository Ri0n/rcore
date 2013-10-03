# To change this template, choose Tools | Templates
# and open the template in the editor.
from __future__ import absolute_import

from rcore.config import config  # @UnusedImport
from rcore.context import (
    Context,  # @UnusedImport
    getContext,  # @UnusedImport
    makeContext,  # @UnusedImport
    setCurrentContext,  # @UnusedImport
    executeInContext,  # @UnusedImport
    log  # @UnusedImport
)
from rcore.scheduler import scheduler  # @UnusedImport

def appInit(core):
    global _coreInstance
    _coreInstance = core

__all__ = ["config", "scheduler", "appInit", "Context",
           "getContext", "makeContext", "setCurrentContext", "executeInContext", "log"]
