"""H2309 strictly read-only original Windows kernel TCP sender telemetry.

Uses Microsoft Winsock SIO_TCP_INFO (TCP_INFO_v0) on the SAME Python-owned
original inner TCP socket. Not fake TCP, no custom ACK, no new send or TCP
congestion-control changes, no capture of payload or process secrets.
See https://learn.microsoft.com/windows/win32/api/mstcpip/ns-mstcpip-tcp_info_v0
"""
import ctypes
import os

SIO_TCP_INFO=0xD8000027
class TCP_INFO_v0(ctypes.Structure):
    _fields_=[
        ("State",ctypes.c_uint32),
        ("Mss",ctypes.c_uint32),
        ("ConnectionTimeMs",ctypes.c_uint64),
        ("TimestampsEnabled",ctypes.c_uint8),
        ("RttUs",ctypes.c_uint32),
        ("MinRttUs",ctypes.c_uint32),
        ("BytesInFlight",ctypes.c_uint32),
        ("Cwnd",ctypes.c_uint32),
        ("SndWnd",ctypes.c_uint32),
        ("RcvWnd",ctypes.c_uint32),
        ("RcvBuf",ctypes.c_uint32),
        ("BytesOut",ctypes.c_uint64),
        ("BytesIn",ctypes.c_uint64),
        ("BytesReordered",ctypes.c_uint32),
        ("BytesRetrans",ctypes.c_uint32),
        ("FastRetrans",ctypes.c_uint32),
        ("DupAcksIn",ctypes.c_uint32),
        ("TimeoutEpisodes",ctypes.c_uint32),
        ("SynRetrans",ctypes.c_uint8),
    ]
assert ctypes.sizeof(TCP_INFO_v0)==88, "MS_TCP_INFO_NATIVE_ABI_LAYOUT"

def read_original_socket_tcp_info(sock):
    if os.name!="nt":
        raise RuntimeError("H2309_WINDOWS_WINSOCK_ONLY")
    ws2=ctypes.WinDLL("ws2_32",use_last_error=True)
    fn=ws2.WSAIoctl
    fn.argtypes=[ctypes.c_size_t,ctypes.c_uint32,ctypes.c_void_p,
                 ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,
                 ctypes.POINTER(ctypes.c_uint32),ctypes.c_void_p,ctypes.c_void_p]
    fn.restype=ctypes.c_int
    version=ctypes.c_uint32(0) # Microsoft TCP_INFO_v0
    info=TCP_INFO_v0()
    count=ctypes.c_uint32(0)
    result=fn(sock.fileno(),SIO_TCP_INFO,ctypes.byref(version),
              ctypes.sizeof(version),ctypes.byref(info),
              ctypes.sizeof(info),ctypes.byref(count),None,None)
    if result!=0:
        code=ws2.WSAGetLastError()
        raise OSError(code,"SIO_TCP_INFO_READ_ONLY_FAILED")
    if count.value!=ctypes.sizeof(info):
        raise RuntimeError("H2309_TCP_INFO_SHORT_NATIVE_READBACK")
    return {name:int(getattr(info,name)) for name in (
        "State","Mss","RttUs","MinRttUs","BytesInFlight","Cwnd",
        "SndWnd","RcvWnd","RcvBuf","BytesOut","BytesIn",
        "BytesReordered","BytesRetrans","FastRetrans",
        "DupAcksIn","TimeoutEpisodes","SynRetrans")}
