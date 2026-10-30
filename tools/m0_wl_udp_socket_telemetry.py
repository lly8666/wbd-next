"""Low-overhead *fixture socket* UDP queue/drops, not Rust packet stats.

Linux /proc/net/udp drops belongs to an EXACT bound UDP socket inode.
Linux /proc/net/snmp Udp RcvbufErrors is guest GLOBAL (not per fixture).
Any missing field returns None, never a manufactured zero.
Only read at 1Hz or start/end; never per-packet syscalls.
"""
import os,pathlib,sys

def parse_udp_mib(raw):
    lines=raw.splitlines()
    for i in range(len(lines)-1):
        a=lines[i].split()
        b=lines[i+1].split()
        if a and b and a[0]==b[0]=="Udp:" and len(a)==len(b):
            try:return {k:int(v) for k,v in zip(a[1:],b[1:])}
            except ValueError:return {}
    return {}

def parse_udp_socket(raw,inode):
    expected=str(inode)
    for line in raw.splitlines()[1:]:
        row=line.split()
        if len(row)<13 or row[9]!=expected:continue
        try:
            return {"rx_queue_bytes":int(row[4].split(":")[1],16),
                    "socket_drops":int(row[-1])}
        except (IndexError,ValueError):return None
    return None

def parse_linux_raw_sockets(raw):
    """Guest-global IPv4 raw socket inode, queue bytes and drop counters."""
    rows={}
    for line in raw.splitlines()[1:]:
        fields=line.split()
        if len(fields)<13:continue
        try:
            inode=fields[9]
            if not inode.isdigit() or inode=="0":continue
            rows[inode]={"rx_queue_bytes":int(fields[4].split(":")[1],16),
                         "drops":int(fields[-1])}
        except (IndexError,ValueError):continue
    return rows

def raw_sockets_delta(first,last):
    if first is None or last is None:return None
    # A disappearing/replaced socket is not evidence of zero drops.
    if set(first)!=set(last) or not first:return None
    out={}
    for inode in first:
        a=first[inode].get("drops");b=last[inode].get("drops")
        if type(a) is not int or type(b) is not int or b<a:return None
        out[inode]={"drops_delta":b-a,
                    "last_rx_queue_bytes":last[inode].get("rx_queue_bytes")}
    return out

def raw_socket_product_owners(inodes,proc_root="/proc"):
    """One-shot exact Linux product comm + fd inode join, not PID inference.
    Only enumerates fd symlinks for the fixed product process basenames;
    no app data or credentials leave the guest in this diagnostic.
    """
    valid={str(x) for x in inodes}
    found={}
    try:entries=list(pathlib.Path(proc_root).iterdir())
    except OSError:return found
    for proc in entries:
        if not proc.name.isdigit():continue
        try:comm=(proc/"comm").read_text(encoding="ascii").strip()
        except (OSError,UnicodeError):continue
        if comm not in ("wbd-v4-server","wbd-v4-client"):continue
        try:fds=list((proc/"fd").iterdir())
        except OSError:continue
        for fd in fds:
            try:target=os.readlink(fd)
            except OSError:continue
            if not target.startswith("socket:[") or not target.endswith("]"):continue
            inode=target[8:-1]
            if inode in valid:
                found[inode]={"pid":int(proc.name),"comm":comm,
                              "identity":"EXACT_PROC_FD_SOCKET_INODE"}
    return found

def _windows_udp_ipv4_stats(fetch=None):
    """Read Windows IPv4 machine-global UDP MIB; never claim per-socket drops."""
    import ctypes
    class UdpStats(ctypes.Structure):
        _fields_=[("dwInDatagrams",ctypes.c_uint32),
                  ("dwNoPorts",ctypes.c_uint32),
                  ("dwInErrors",ctypes.c_uint32),
                  ("dwOutDatagrams",ctypes.c_uint32),
                  ("dwNumAddrs",ctypes.c_uint32)]
    if fetch is None:
        if sys.platform!="win32":return None
        try:
            fetch=ctypes.WinDLL("iphlpapi").GetUdpStatistics
            fetch.argtypes=[ctypes.POINTER(UdpStats)]
            fetch.restype=ctypes.c_ulong
        except (OSError,AttributeError):return None
    result=UdpStats()
    try:
        if fetch(ctypes.byref(result))!=0:return None
    except (OSError,TypeError):return None
    return {"in_datagrams":int(result.dwInDatagrams),
            "no_ports":int(result.dwNoPorts),
            "in_errors":int(result.dwInErrors)}

def _windows_ipv4_udp_delta(first,last):
    a=first.get("windows_host_ipv4_udp_stats") if first else None
    b=last.get("windows_host_ipv4_udp_stats") if last else None
    if not isinstance(a,dict) or not isinstance(b,dict):return None
    return {key+"_delta":(b[key]-a[key]
            if type(a.get(key)) is int and type(b.get(key)) is int
            and b[key]>=a[key] else None)
            for key in ("in_datagrams","in_errors","no_ports")}

def _read(path):
    try:return pathlib.Path(path).read_text(encoding="ascii")
    except (OSError,UnicodeError):return None

def snapshot(sock, include_raw_owners=False):
    try:actual=sock.getsockopt(__import__("socket").SOL_SOCKET,__import__("socket").SO_RCVBUF)
    except OSError:actual=None
    result={"scope":"BOUND_UDP_GENERATOR_RECEIVER_SOCKET",
            "so_rcvbuf_effective_bytes":actual,
            "linux_socket_udp_drops":None,
            "linux_socket_rx_queue_bytes":None,
            "linux_guest_global_udp_rcvbuf_errors":None,
            "linux_guest_global_udp_in_errors":None,
            "linux_guest_rmem_max_bytes":None,
            "linux_guest_rmem_default_bytes":None,
            "linux_raw_socket_snapshot":None,
            "linux_raw_socket_owners":None,
            "linux_raw_socket_scope":"WSL_GUEST_GLOBAL_AF_INET_RAW_NOT_ONE_PRODUCT_INODE",
            "windows_host_ipv4_udp_stats":None,
            "windows_udp_scope":"MACHINE_GLOBAL_IPV4_NOT_PER_SOCKET"}
    if sys.platform=="win32":
        result["windows_host_ipv4_udp_stats"]=_windows_udp_ipv4_stats()
        return result
    if sys.platform!="linux":return result
    try:inode=os.fstat(sock.fileno()).st_ino
    except OSError:return result
    raw=_read("/proc/net/udp")
    row=parse_udp_socket(raw,inode) if raw else None
    if row is not None:
        result["linux_socket_udp_drops"]=row["socket_drops"]
        result["linux_socket_rx_queue_bytes"]=row["rx_queue_bytes"]
    raw=_read("/proc/net/raw")
    result["linux_raw_socket_snapshot"]=parse_linux_raw_sockets(raw) if raw is not None else None
    if include_raw_owners and result["linux_raw_socket_snapshot"] is not None:
        result["linux_raw_socket_owners"]=raw_socket_product_owners(
            result["linux_raw_socket_snapshot"])
    raw=_read("/proc/net/snmp")
    mib=parse_udp_mib(raw) if raw else {}
    result["linux_guest_global_udp_rcvbuf_errors"]=mib.get("RcvbufErrors")
    result["linux_guest_global_udp_in_errors"]=mib.get("InErrors")
    for field,path in (("linux_guest_rmem_max_bytes","/proc/sys/net/core/rmem_max"),
                       ("linux_guest_rmem_default_bytes","/proc/sys/net/core/rmem_default")):
        raw=_read(path)
        if raw:
            try:result[field]=int(raw.strip())
            except ValueError:pass
    return result

def delta(first,last):
    out={}
    for key in ("linux_socket_udp_drops",
                "linux_guest_global_udp_rcvbuf_errors",
                "linux_guest_global_udp_in_errors"):
        a=first.get(key) if first else None
        b=last.get(key) if last else None
        out[key+"_delta"]=(b-a if type(a) is int and type(b) is int and b>=a else None)
    out["windows_host_ipv4_udp_deltas"]=_windows_ipv4_udp_delta(first,last)
    out["linux_raw_socket_deltas"]=raw_sockets_delta(
        first.get("linux_raw_socket_snapshot") if first else None,
        last.get("linux_raw_socket_snapshot") if last else None)
    return out
