import calendar
import time

def timed(fn):
    def wrapped(*args, **kwargs):
        now = time.time()
        res = fn(*args, **kwargs)
        delta = time.time()-now
        print "\n%s took\t%5.3fs"%(fn.__name__,delta)
        return res
    return wrapped

def skip(fn):
    def wrapped(*args, **kwargs):
        print "Skipping %s"%fn.__name__
        return
    return wrapped

def timestamp():
    n = time.gmtime()
    return calendar.timegm(n)
