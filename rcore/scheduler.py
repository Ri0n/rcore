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

import collections
from datetime import datetime, timedelta, date, time
#import sched, time
from twisted.internet import defer, reactor
from twisted.python import failure, log

from rcore.error import SchedulerError, InternalError
from rcore.context import executeInExactContext, getContext, Context

STATE_PAUSED = 0
STATE_DELAY = 1
STATE_WORK = 2


class SchedulerJob(object):
    def __init__(self, job, *args):
        self.job = job
        self.args = args
        self.repeatedDelay = None
        self.timeHandler = None
        self.time = None
        self.result = None
        self.state = STATE_PAUSED
        self.pauseRequested = False
        self.maxExecTime = timedelta(minutes=10)
        self.currentDeferred = None
        self.timeoutDC = None

    def isWorking(self):
        return self.state == STATE_WORK

    def repeated(self, delay):
        if type(delay) == timedelta:
            self.repeatedDelay = delay
        if type(delay) == int:
            self.repeatedDelay = timedelta(seconds=delay)
        else:
            self.repeatedDelay = self._convertDelay(delay)
        if self.repeatedDelay < timedelta(seconds=1):
            raise Exception("period too small!")
        return self

    def start(self, startAt=None):
        self.state = STATE_DELAY
        now = datetime.now()
        tt = type(startAt)
        if tt == timedelta:
            self.time = now + startAt
        elif tt == datetime:
            self.time = startAt
        elif tt == time:
            self.time = datetime.combine(date.today(), startAt)
        elif tt == int:
            self.time = now + timedelta(seconds=startAt)
        elif tt == str: # we will consider this is time hh:mm:ss
            self.time = datetime.combine(date.today(), time()) + self._convertDelay(startAt)
        else:
            self.time = now
        if self.time < now and not self.repeatedDelay:
            raise InternalError("Invalid scheduler time")
        td = self.time - now
        self.timeHandler = reactor.callLater(td.days * 86400 + td.seconds, self._execute)
        return self

    def cancel(self):
        if self.timeHandler:
            self.timeHandler.cancel()
            scheduler.removeJob(self)

    def force(self):
        """active job right now. usefull in case of looped jobs"""

        def returnActualResult(result):
            return self.result

        d = self._execute()
        d.addCallback(returnActualResult)
        return d

    def pause(self):
        if self.state != STATE_PAUSED:
            if self.timeHandler and self.timeHandler.active():
                self.timeHandler.cancel()
                self.timeHandler = None
            if self.state == STATE_WORK:
                self.pauseRequested = True
            else:
                self.state = STATE_PAUSED

    def resume(self):
        if self.state == STATE_PAUSED:
            self._nextLoop()

    def _nextLoop(self):
        now = datetime.now()
        while self.time - now < timedelta(seconds=1): # don't call too often or in past
            self.time += self.repeatedDelay
        td = self.time - now
        self.timeHandler = reactor.callLater(td.days * 86400 + td.seconds, self._execute)

    def _execute(self):
        def checkTimeout(d):
            if d and not d.called:
                from rcore import Core

                Core.instance().getRPCService("alarm").notify("Execution of %s was timed out. This usually mean "
                                                              "that deferreds chain is corrupted or something just hangs and "
                                                              "its definitelly a bad sign. notice if this a looped job next "
                                                              "cycle will never be started" % repr(self), ["error"])

        if scheduler.aboutToExecute(self) == False: # current execution cancelled
            return defer.succeed(None)
        if self.state == STATE_WORK:
            raise SchedulerError("Can't execute. it's already executing")

        def handleResult(result):
            """just stores last execution result"""
            self.result = result
            if isinstance(result, failure.Failure):
                log.msg(result.getTraceback())
            self.state = STATE_DELAY
            self.currentDeferred = None
            if not self.repeatedDelay:
                scheduler.removeJob(self)
            else:
                if self.pauseRequested:
                    self.state = STATE_PAUSED
                    self.pauseRequested = False
                else:
                    self._nextLoop()

        self.state = STATE_WORK
        self.startedAt = datetime.today()
        self.timeHandler = None
        self.currentDeferred = defer.maybeDeferred(self.job, *self.args)
        self.currentDeferred.addBoth(handleResult)
        reactor.callLater(self.maxExecTime.days * 86400 + \
                          self.maxExecTime.seconds, checkTimeout, self.currentDeferred)
        return self.currentDeferred

    def _convertDelay(self, strTime):
        if isinstance(strTime, timedelta):
            return strTime
        ret = dict(sec=0, min=0, hour=0)
        names = ["sec", "min", "hour"]
        exp = strTime.split(':')
        exp.reverse()
        for v in names:
            if len(exp):
                ret[v] = int(exp[0])
                del exp[0]
            else:
                break
        return timedelta(hours=ret["hour"], minutes=ret["min"], seconds=ret["sec"])


class ContextedSchedulerJob(SchedulerJob):
    def __init__(self, context, *args):
        assert issubclass(context, Context) and isinstance(context.run, collections.Callable)
        super(ContextedSchedulerJob, self).__init__(lambda: executeInExactContext(lambda: getContext().run(), context),
                                                    *args)


class Scheduler(object):
    SkipBlocked = 1
    RescheduleBlocked = 2
    QueueBlocked = 3

    def __init__(self):
        self.scheduled = []
        self.blockers = dict()
        self.blockActions = dict()

    def job(self, executor, *args):
        j = SchedulerJob(executor, *args)
        self.scheduled.append(j)
        return j

    def contextJob(self, context, *args):
        j = ContextedSchedulerJob(context, *args)
        self.scheduled.append(j)
        return j

    def removeJob(self, job):
        self.scheduled.remove(job)

    def stop(self):
        for s in self.scheduled:
            s.cancel()

    def setConcurrentBlock(self, jobs):
        for cj in jobs:
            if id(cj) not in self.blockers:
                self.blockers[id(cj)] = []
            for bj in jobs:
                if bj != cj:
                    self.blockers[id(cj)].append(bj)

    def setOnBlockAction(self, job, actionType, *args):
        self.blockActions[id(job)] = dict(action=actionType, args=args)

    def aboutToExecute(self, job):
        """
        its kinda signal from job to scheduler that job is going
        to execute. Scheduler checks here for blockers and may delay
        or stop execution if necessary
        """
        jid = id(job)
        if jid not in self.blockers:
            return True
        for j in self.blockers[jid]:
            if j.isWorking():
                if jid not in self.blockActions:
                    from rcore import Core

                    Core.instance().getRPCService("alarm").notify("Execution of %s was blocked by currently"
                                                            " working %s and no handlers for this case were set. This"
                                                            " usually means architectural design flaw." % \
                                                            (repr(job), repr(j)), ["error"])
                    return False
                if self.blockActions[jid]['action'] == self.QueueBlocked:
                    log.msg("execution of %s queued" % repr(job))

                    def queueExecution(result, job):
                        log.msg("executing queued job" % repr(job))
                        reactor.callLater(0, job._execute)
                        return result

                    j.currentDeferred.addBoth(queueExecution, job)
                if self.blockActions[jid]['action'] == self.RescheduleBlocked:
                    raise Exception("RescheduleBlocked is not implemented")

                return False
        return True


scheduler = Scheduler()
