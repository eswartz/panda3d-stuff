import heapq

from panda3d.direct import CInterval

class Scheduler(object):
    def __init__(self):
        self._listener = None

        # sorted list of (start, func)
        self._queue = []
        # sorted list of (start, Interval)
        self._intervals = []

        self._ticking = False
        self._time = 0

    def start(self):
        self._listener = lambda x: self._updateIntervals(x)

    def clearQueue(self):
        """
        Remove any pending actions or scheduled intervals
        :return
        """
        for _, itvl in self._intervals:
            if itvl.getState() == CInterval.SStarted:
                itvl.finish()
            else:
                itvl.pause()
        self._intervals = []
        self._queue = []

    def isQueueEmpty(self):
        return not self._queue and not self._intervals

    def stop(self):
        self.clearQueue()

    def _getEndTime(self):
        # initial guess
        deadline = self._time
        if self._queue:
            deadline = self._queue[-1][0] + 0.001
        if self._intervals:
            for start, itvl in self._intervals:
                deadline = max(deadline, start + itvl.getDuration())
        return deadline

    def schedule(self, secs, doit, fromNow=False):
        if fromNow:
            startTime = self._time
        else:
            startTime = self._getEndTime()

        startTime += secs

        #print services.mission.gameTime, "start Time:",startTime
        self._queue.append((startTime, doit))

        if not self._ticking:
            # do this later, so we don't have 0-scheduled stuff
            # constantly jumping to the front of the queue
            heapq.heapify(self._queue)

        #print services.mission.gameTime,"new end time after",secs,"for",doit,"=",startTime
        return startTime

    def scheduleInterval(self, secs, interval, fromNow=False):
        startTime = self.schedule(secs, lambda: interval.start(), fromNow)

        self._intervals.append((startTime, interval))
        heapq.heapify(self._intervals)

    def tick(self, now, fullSpeed=False):
        self._time = now
        while self._queue:
            start, doit = self._queue[0]
            if now >= start or fullSpeed:
                #print "starting",doit
                self._queue[0:1] = []
                self._ticking = True
                try:
                    doit()
                except:
                    import traceback
                    traceback.print_exc()
                finally:
                    self._ticking = False
                    if now < start and fullSpeed:
                        self._time = start
                        break
            else:
                break

        # in case anything was scheduled from doit()
        heapq.heapify(self._queue)

        for secs, itvl in list(self._intervals):
            if itvl.getState() == CInterval.SStarted and fullSpeed:
                itvl.finish()
            if itvl.getState() == CInterval.SFinal:
                self._intervals.remove((secs, itvl))


