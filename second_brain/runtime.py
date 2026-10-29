import os
import sys
import time


def process_usage():
    rss = None
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        get_current = ctypes.windll.kernel32.GetCurrentProcess
        get_current.restype = wintypes.HANDLE
        query = ctypes.windll.psapi.GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if query(get_current(), ctypes.byref(counters), counters.cb):
            rss = counters.WorkingSetSize
    else:
        import resource

        measured = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss = measured if sys.platform == "darwin" else measured * 1024
    return {
        "pid": os.getpid(),
        "cpu_seconds": round(time.process_time(), 3),
        "rss_bytes": rss,
        "rss_kind": "current working set" if sys.platform == "win32" else "peak resident set",
        "platform": sys.platform,
    }
