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
    # Win32 FILETIME is two uint32 on Windows x64 AND in Linux CI tests.
    _fields_=[("low",ctypes.c_uint32),("high",ctypes.c_uint32)]

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

class _ThreadEntry(ctypes.Structure):
    # THREADENTRY32 consists of seven 32-bit fields; never use a host
    # c_ulong (64-bit on Linux) to model the Windows kernel ABI.
    _fields_=[("size",ctypes.c_uint32),("usage",ctypes.c_uint32),
              ("thread_id",ctypes.c_uint32),("owner_pid",ctypes.c_uint32),
              ("base_priority",ctypes.c_int32),("delta_priority",ctypes.c_int32),
              ("flags",ctypes.c_uint32)]

def _thread_cpu_snapshot(kernel, pid, previous):
    """One 1Hz Toolhelp read, outside the product. No native packet callbacks."""
    snapshot=kernel.CreateToolhelp32Snapshot(0x00000004,0) # TH32CS_SNAPTHREAD
    if snapshot==ctypes.c_void_p(-1).value:
        return {"status":"NOT_MEASURED_TOOLHELP"},previous
    current={}
    samples=[]
    try:
        entry=_ThreadEntry()
        entry.size=ctypes.sizeof(entry)
        valid=kernel.Thread32First(snapshot,ctypes.byref(entry))
        while valid:
            if entry.owner_pid==pid:
                handle=kernel.OpenThread(0x0800,False,entry.thread_id)
                if handle:
                    try:
                        create,exit_time,kt,ut=(_FileTime() for _ in range(4))
                        if kernel.GetThreadTimes(handle,ctypes.byref(create),
                                                 ctypes.byref(exit_time),
                                                 ctypes.byref(kt),ctypes.byref(ut)):
                            kt_s=_sec(kt);ut_s=_sec(ut);total=kt_s+ut_s
                            name=""
                            name_pointer=ctypes.c_void_p()
                            hr=kernel.GetThreadDescription(handle,ctypes.byref(name_pointer))
                            if hr==0 and name_pointer.value:
                                try:name=ctypes.wstring_at(name_pointer.value)
                                finally:kernel.LocalFree(name_pointer)
                            # Name failure or an empty description is not
                            # evidence this thread belongs to Go rather
                            # than Rust. Preserve status for the RCA.
                            description_status=("NAMED" if name else
                                "EMPTY" if hr==0 else "HRESULT_"+format(hr&0xffffffff,"08x"))
                            prev=previous.get(entry.thread_id)
                            delta=max(0.,total-prev[0]) if prev else 0.
                            dk=max(0.,kt_s-prev[1]) if prev else 0.
                            du=max(0.,ut_s-prev[2]) if prev else 0.
                            current[entry.thread_id]=(total,kt_s,ut_s)
                            samples.append({"tid":int(entry.thread_id),"name":name,
                                            "name_status":description_status,
                                            "cpu_total_s":round(total,6),
                                            "cpu_kernel_s":round(kt_s,6),
                                            "cpu_user_s":round(ut_s,6),
                                            "cpu_delta_s":round(delta,6),
                                            "cpu_kernel_delta_s":round(dk,6),
                                            "cpu_user_delta_s":round(du,6)})
                    finally:
                        kernel.CloseHandle(handle)
            entry.size=ctypes.sizeof(entry)
            valid=kernel.Thread32Next(snapshot,ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    named=[row for row in samples if row["name"] in ("wbd-native-tx","wbd-native-rx")]
    return {
        "status":"MEASURED" if samples else "NO_THREAD_SAMPLES",
        "thread_count_sampled":len(samples),
        "named_rust_workers":len(named),
        "thread_name_status_counts":{
            label:sum(x["name_status"]==label for x in samples)
            for label in sorted({x["name_status"] for x in samples})
        },
        "all_thread_cpu_kernel_delta_s":round(sum(x["cpu_kernel_delta_s"] for x in samples),6),
        "all_thread_cpu_user_delta_s":round(sum(x["cpu_user_delta_s"] for x in samples),6),
        "all_thread_cpu_delta_s":round(sum(x["cpu_delta_s"] for x in samples),6),
        "rust_tx_cpu_delta_s":round(sum(x["cpu_delta_s"] for x in named if x["name"]=="wbd-native-tx"),6),
        "rust_tx_kernel_delta_s":round(sum(x["cpu_kernel_delta_s"] for x in named if x["name"]=="wbd-native-tx"),6),
        "rust_tx_user_delta_s":round(sum(x["cpu_user_delta_s"] for x in named if x["name"]=="wbd-native-tx"),6),
        "rust_rx_cpu_delta_s":round(sum(x["cpu_delta_s"] for x in named if x["name"]=="wbd-native-rx"),6),
        "rust_rx_kernel_delta_s":round(sum(x["cpu_kernel_delta_s"] for x in named if x["name"]=="wbd-native-rx"),6),
        "rust_rx_user_delta_s":round(sum(x["cpu_user_delta_s"] for x in named if x["name"]=="wbd-native-rx"),6),
        "other_threads_cpu_delta_s":round(sum(x["cpu_delta_s"] for x in samples if x["name"] not in ("wbd-native-tx","wbd-native-rx")),6),
        "hottest_threads":sorted(samples,key=lambda x:x["cpu_delta_s"],reverse=True)[:6],
        "interpretation":"Exact Win32 thread kernel/user CPU only. NAMELESS THREADS ARE NOT GO. Native driver execution beyond this process and syscall substage attribution are NOT measured.",
    },current

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
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=ctypes.c_void_p
    kernel.Thread32First.argtypes=[ctypes.c_void_p,ctypes.POINTER(_ThreadEntry)]
    kernel.Thread32First.restype=wintypes.BOOL
    kernel.Thread32Next.argtypes=[ctypes.c_void_p,ctypes.POINTER(_ThreadEntry)]
    kernel.Thread32Next.restype=wintypes.BOOL
    kernel.OpenThread.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenThread.restype=ctypes.c_void_p
    kernel.GetThreadTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(_FileTime)]*4
    kernel.GetThreadTimes.restype=wintypes.BOOL
    kernel.GetThreadDescription.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)]
    kernel.GetThreadDescription.restype=ctypes.c_long
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    kernel.CloseHandle.restype=wintypes.BOOL
    previous=None
    previous_threads={}
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
                row["thread_cpu"],previous_threads=_thread_cpu_snapshot(
                    kernel,proc.pid,previous_threads)
                out.write(json.dumps(row,sort_keys=True)+"\n")
                out.flush()
                previous=(now,total)
            stop.wait(interval)
