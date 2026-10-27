"""Native Windows ORIGINAL Go+Rust process CPU/RSS sampler for Actions.

GetProcessTimes includes native Rust DLL as well as original Go runtime and
OS syscall charge. It cannot individually attribute Go or Rust CPU, and is
never described as such. Read-only, 1Hz, no privilege or third-party package.
"""
import ctypes
from ctypes import wintypes
import json
import os
import time

class _FileTime(ctypes.Structure):
    _fields_=[("low",wintypes.DWORD),("high",wintypes.DWORD)]

class _Memory(ctypes.Structure):
    _fields_=[
        ("cb",wintypes.DWORD),
        ("page_fault_count",wintypes.DWORD),
        ("peak_working_set",ctypes.c_size_t),
        ("working_set",ctypes.c_size_t),
        ("quota_peak_paged_pool",ctypes.c_size_t),
        ("quota_paged_pool",ctypes.c_size_t),
        ("quota_peak_nonpaged_pool",ctypes.c_size_t),
        ("quota_nonpaged_pool",ctypes.c_size_t),
        ("pagefile",ctypes.c_size_t),
        ("peak_pagefile",ctypes.c_size_t),
        ("private_bytes",ctypes.c_size_t),
    ]

def _sec(t):
    return ((int(t.high)<<32)|int(t.low))*1e-7

def sample_windows_original_process(proc,path,stop,interval=1.0):
    if os.name!="nt":
        return
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    psapi=ctypes.WinDLL("psapi",use_last_error=True)
    cpu=kernel.GetProcessTimes
    cpu.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(_FileTime)]*4
    cpu.restype=wintypes.BOOL
    memory=psapi.GetProcessMemoryInfo
    memory.argtypes=[ctypes.c_void_p,ctypes.POINTER(_Memory),wintypes.DWORD]
    memory.restype=wintypes.BOOL
    handle=ctypes.c_void_p(int(proc._handle))
    previous=None
    with open(path,"w",encoding="utf-8") as out:
        while proc.poll() is None and not stop.is_set():
            create,exit_time,kernel_time,user_time=(_FileTime() for _ in range(4))
            mem=_Memory()
            mem.cb=ctypes.sizeof(mem)
            now=time.monotonic()
            if cpu(handle,ctypes.byref(create),ctypes.byref(exit_time),
                   ctypes.byref(kernel_time),ctypes.byref(user_time)) and \
               memory(handle,ctypes.byref(mem),mem.cb):
                total=_sec(kernel_time)+_sec(user_time)
                pct=None
                if previous is not None and now>previous[0]:
                    pct=round(100*(total-previous[1])/(now-previous[0]),3)
                row={
                    "scope":"SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED",
                    "native_pid":proc.pid,
                    "monotonic_s":round(now,6),
                    "cpu_total_s":round(total,6),
                    "cpu_kernel_s":round(_sec(kernel_time),6),
                    "cpu_user_s":round(_sec(user_time),6),
                    "cpu_pct_one_logical_core":pct,
                    "working_set_bytes":int(mem.working_set),
                    "peak_working_set_bytes":int(mem.peak_working_set),
                    "private_bytes":int(mem.private_bytes),
                    "logical_cpus_reported":os.cpu_count(),
                }
                out.write(json.dumps(row,sort_keys=True)+"\n")
                out.flush()
                previous=(now,total)
            stop.wait(interval)
