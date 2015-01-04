"""Python reference counter statistics.
"""
import sys, gc, inspect, weakref, time
from UserDict import UserDict
from types import InstanceType

# a special container which we can recognize and avoid
# including in output sets, which might create reference loops
class _StatsDict(weakref.WeakKeyDictionary):
  pass

class StatsDelta(object):
  """GC statistics tracking.

  Monitors the number of instances of each type/class (cf. gcstats())
  and prints a report of any changes (ie. new types/count changes).
  Intended to assist in detecting reference leaks.
  """
  def __init__(self):
    self.reset()
  def reset(self):
    """Reset internal statistics counters
    """
    self.stats, self.ntypes = None, None
  def collect(self, file=sys.stderr):
    """Collect stats and print results to file

    :param file: A writable file-like object
    """
    cur = gcstats()
    Ncur = len(cur)
    if self.stats is not None:
      prev = self.stats
      Nprev = self.ntypes # may be less than len(prev)

      if Ncur!=Nprev:
        print >>file,"# Types %d -> %d"%(Nprev,Ncur)

      Scur, Sprev, first = set(cur), set(prev), True
      for T in Scur-Sprev: # new types
        if first:
          print >>file,'New Types'
          first=False
        print >>file,' ',T,cur[T]

      first = True
      for T in Scur&Sprev:
        if cur[T]==prev[T]:
          continue
        if first:
          print >>file,'Known Types'
          first=False
        print >>file,' ',T,cur[T],'delta',cur[T]-prev[T]

    self.stats, self.ntypes = cur, len(cur)
    #gc.collect()

def gcstats():
  """Count the number of instances of each type/class

  :returns: A WeakKeyDictionary mapping type to an integer number of references
  """
  all = gc.get_objects()
  _stats = {}

  for obj in all:
    K = type(obj)
    if K in [_StatsDict, StatsDelta]:
      continue # avoid counting ourselves

    elif K is InstanceType: # instance of an old-style class
      K = getattr(obj, '__class__', K)

    try:
      _stats[K] += 1
    except KeyError:
      _stats[K] = 1

  # explicitly break the reference loop between the list and this frame,
  # which is contained in the list
  # This would otherwise prevent the list from being free'd
  del all

  # use a weakref to allow types to be GC'd
  return _StatsDict(_stats)

class _StatsThread(object):
  def __init__(self, period, file):
    self.period, self.file = period, file
    self.S = StatsDelta()

  def __call__(self):
    while True:
      self.S.collect(file=self.file)
      time.sleep(self.period)

def periodic(period=60.0, file=sys.stderr):
  """Start a daemon thread which will periodically print GC stats

  :param period: Update period in seconds
  :param file: A writable file-like object
  """
  import threading, time
  S = _StatsThread(period=period, file=file)
  T = threading.Thread(target=S)
  T.daemon = True
  T.start()

if __name__=='__main__':
  #for T,C in gcstats().iteritems():
  #  print T,C
  gc.set_debug(gc.DEBUG_COLLECTABLE|gc.DEBUG_INSTANCES|gc.DEBUG_OBJECTS)
  S=StatsDelta()
  while True:
    print 'Iteration'
    S.collect()
    #gc.collect()
