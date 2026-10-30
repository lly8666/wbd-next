"""Bounded original-OS UDP load fixture helpers; never transport/FEC product."""
import math

class FirstDeliveryBitmap:
    """One bit per sequence. Never let hostile sequence IDs allocate memory."""
    __slots__ = ("_bits","limit","count","low","high")
    def __init__(self,limit):
        if type(limit) is not int or not 0 <= limit <= 250_000_000:
            raise ValueError("invalid bounded sequence limit")
        self._bits=bytearray((limit+8)//8)
        self.limit=limit
        self.count=0
        self.low=None
        self.high=None
    def __contains__(self,seq):
        return (type(seq) is int and 0 <= seq <= self.limit and
                bool(self._bits[seq>>3] & (1<<(seq&7))))
    def add(self,seq):
        if type(seq) is not int or not 0 <= seq <= self.limit:
            raise ValueError("source sequence outside bounded scenario")
        byte=seq>>3
        bit=1<<(seq&7)
        if self._bits[byte]&bit:return False
        self._bits[byte]|=bit
        self.count+=1
        if self.low is None or seq<self.low:self.low=seq
        if self.high is None or seq>self.high:self.high=seq
        return True
    def __len__(self):return self.count
    @property
    def storage_bytes(self):return len(self._bits)

def bounded_sequence_limit(bytes_per_second,duration_s,min_payload):
    if bytes_per_second<=0 or duration_s<=0 or min_payload<=0:
        raise ValueError("invalid scenario dimensions")
    return min(250_000_000,2*math.ceil(bytes_per_second*duration_s/min_payload)+8192)

def rate_wait_seconds(now,send_end,drain_end,credit,next_payload,rate,next_probe):
    """Sleep in OS select() until socket RX, next full source, or 10Hz probe."""
    if now>=drain_end:return 0.0
    if now<send_end and credit>=next_payload:return 0.0
    deadline=min(now+.05,drain_end)
    if now<send_end:
        deadline=min(deadline,send_end,
                     now+max(0.0,next_payload-credit)/rate,next_probe)
    return max(0.0,deadline-now)

def receiver_buffer_request_bytes(platform,is_v2):
    if is_v2:return (16 if platform=="win32" else 4)*1024*1024
    return 2*1024*1024
