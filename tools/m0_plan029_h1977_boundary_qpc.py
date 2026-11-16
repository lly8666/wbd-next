#!/usr/bin/env python3
"""H1977 original signed Windows QPC boundary diagnosis for severe 60ms stalls.

Only Windows QueryPerformanceCounter values are subtracted. Unlike strict
H1966 performance qualification, this diagnostic RETAINS exact-sequence TCP
retransmits and requires every 1024B app window to have genuine TX mailbox,
RX Wintun SendPacket and kernel inner read receipts. Never label a failed
underlying original Action as PASS based on this sidecar.
"""
import math
from m0_plan029_h1966_steady_qpc import read_chunks,ING,LEG,MIN_COUNT,SIZE,need

TX="PLAN029_H1977_TX_MAILBOX_QPC_FINAL "
RX="PLAN029_H1977_RX_WINTUN_SEND_QPC_FINAL "
FD="PLAN029_H1977_FD_READ_QPC_FINAL "
MAP="PLAN029_H1977_PROXY_MAP_FINAL "
SOURCE="original_native_windows_owner"

def boundary_rows(log,mark,fields,src,min_count=0):
    f=None;total=None;dropped=None;parts={}
    for line in log.splitlines():
        if mark not in line:continue
        text=line.split(mark,1)[1]
        need("source="+src in text,"H1977 wrong owner/source "+mark)
        tokens=dict(word.split("=",1) for word in
                    text.split(" source=",1)[0].split() if "=" in word)
        need(all(k in tokens for k in
                 ("frequency","total","dropped","chunk","count","rows")),
             "H1977 missing chunk metadata")
        fq,n,drop,chunk,count=(int(tokens[k]) for k in
                              ("frequency","total","dropped","chunk","count"))
        need(fq>1000 and 0<=n<=8192 and drop==0 and
             0<=chunk<100 and 0<=count<=96,
             "H1977 QPC overflow or invalid owner metadata")
        if f is None:f,total,dropped=fq,n,drop
        need((fq,n,drop)==(f,total,dropped) and chunk not in parts,
             "H1977 mixed/duplicate QPC chunks")
        raw=tokens["rows"]
        rows=raw.split(",") if count else []
        need(len(rows)==count,"H1977 chunk count mismatch")
        parsed=[]
        for item in rows:
            vals=item.split(":")
            need(len(vals)==fields,"H1977 row format drift")
            parsed.append(tuple(int(v) for v in vals))
        parts[chunk]=parsed
    need(f is not None and set(parts)==set(range(len(parts))),
         "H1977 signed QPC chunks missing")
    rows=[r for i in range(len(parts)) for r in parts[i]]
    need(len(rows)==total and total>=min_count,"H1977 missing owner rows")
    return f,rows

def us_dist(rows,f):
    need(len(rows)==MIN_COUNT and all(v>=0 for v in rows),
         "H1977 one or more request windows missing")
    a=sorted(rows)
    return {k:round(a[math.ceil(p*len(a))-1]*1_000_000/f,3)
            for k,p in (("p50_us",.5),("p95_us",.95),
                        ("p99_us",.99),("max_us",1.0))}

def analyze(log,steady,source):
    need(steady["source_sha"]==source,"H1977 different original source")
    direct=steady["direct"]
    need(direct["source"]==source and direct["measured"]==MIN_COUNT and
         len(direct["app_qpc"])==MIN_COUNT and
         direct["exact_bytes"]==(MIN_COUNT+32)*SIZE and direct["half_close"],
         "H1977 real original app/bytes/FIN absent")
    f,ing=read_chunks(log,ING,6,"original_rust_wintun_tx_test_only")
    fl,legs=read_chunks(log,LEG,12,"original_rust_tcp_test_only")
    ft,tx=boundary_rows(log,TX,6,SOURCE,MIN_COUNT)
    fr,rx=boundary_rows(log,RX,6,SOURCE,MIN_COUNT)
    fe,fd=boundary_rows(log,FD,3,"original_winsock_events",0)
    need(f==fl==ft==fr==fe==direct["qpc_frequency"],
         "H1977 not a single original Win32 QPC frequency")
    mappings=[line for line in log.splitlines() if MAP in line]
    need(len(mappings)==1,"H1977 proxy mapping Stop missing")
    m=mappings[0].split(MAP,1)[1].split(" source=",1)[0]
    tok=dict(x.split("=",1) for x in m.split() if "=" in x)
    need(int(tok["frequency"])==f,"H1977 mapping QPC drift")
    pairs=[tuple(int(v) for v in x.split(":")) for x in
           tok["rows"].split(",") if x]
    need(len(pairs)==int(tok["count"]) and len(set(pairs))==len(pairs),
         "H1977 proxy mapping ambiguous")
    source_port=direct["source_port"]
    proxies={proxy for proxy,src in pairs if src==source_port}
    need(len(proxies)==1,"H1977 real original app port to NAT proxy mismatch")
    proxy=next(iter(proxies))
    ing=[r for r in ing if r[0]==source_port]
    legs=[r for r in legs if r[0]==source_port]
    tx=[r for r in tx if r[0]==proxy and r[1]==source_port]
    rx=[r for r in rx if r[0]==proxy and r[1]==0]
    fd=[r for r in fd if r[0]==source_port and r[1]==0]
    need(len(tx)>=MIN_COUNT and len(rx)>=MIN_COUNT,
         "H1977 original translated TCP DATA missing from TX/RX")
    for r in tx+rx:
        need(r[3]==SIZE and 0<r[4]<=r[5],
             "H1977 wrong 1024B TCP packet or nonmonotonic QPC")
    out={k:[] for k in ("nat_to_mailbox_tx","mailbox_tx_to_rx_before_send",
        "rx_wintun_send_call","rx_send_return_to_inner_kernel_read",
        "nat_to_inner_kernel_read","full_app_rtt")}
    retrans=[];long=[];fd_gap=[]
    windows=direct["app_qpc"]
    for i,(a,b,c) in enumerate(windows):
        need(0<a<=b<=c and (i==0 or windows[i-1][2]<a),
             "H1977 request windows overlap")
        in_win=[r for r in ing if a<=r[3]<=c]
        need(len(in_win)>=1 and all(r[2]==SIZE for r in in_win) and
             len({r[1] for r in in_win})==1,
             "H1977 ambiguous original TCP sequence/payload")
        seq=in_win[0][1]
        nat=min(r[5] for r in in_win)
        tx_win=sorted((r for r in tx if r[2]==seq and a<=r[4]<=c),
                      key=lambda r:r[5])
        rx_win=sorted((r for r in rx if r[2]==seq and a<=r[4]<=c),
                      key=lambda r:r[5])
        need(tx_win and rx_win,"H1977 missing genuine TX/RX for app TCP seq")
        first_tx=tx_win[0]
        sent=[r for r in rx_win if r[4]>=first_tx[4] and r[5]<=c]
        need(sent,"H1977 Wintun SendPacket call missing")
        first_rx=sent[0]
        leg=[r for r in legs if a<=r[1]<=c and r[7]>0]
        need(sum(r[7] for r in leg)==SIZE,
             "H1977 real inner kernel read not exact 1024B")
        inner=min(r[2] for r in leg)
        need(nat<=first_tx[4]<=first_tx[5]<=first_rx[4]<=first_rx[5]<=inner<=c,
             "H1977 causal boundary ordering invalid")
        values=(first_tx[5]-nat,first_rx[4]-first_tx[5],
                first_rx[5]-first_rx[4],inner-first_rx[5],
                inner-nat,c-a)
        for k,v in zip(out,values):out[k].append(v)
        repeats=len(in_win)-1
        if repeats:
            retrans.append(dict(index=i,seq=seq,count=repeats))
        event=[r[2] for r in fd if first_rx[5]<=r[2]<=inner]
        if event:fd_gap.append((inner-max(event))*1_000_000/f)
        if (c-a)*1000/f>=8:
            long.append(dict(index=i,seq=seq,app_rtt_ms=round((c-a)*1000/f,3),
                nat_to_tx_ms=round(values[0]*1000/f,3),
                tx_to_rx_ms=round(values[1]*1000/f,3),
                send_call_ms=round(values[2]*1000/f,3),
                after_wintun_send_to_inner_read_ms=round(values[3]*1000/f,3),
                inner_fd_read_signal_seen=bool(event),
                repeated_tcp_payload_count=repeats))
    need(len(out["full_app_rtt"])==MIN_COUNT,
         "H1977 missing 2048 original app request windows")
    return dict(source_sha=source,
      status="DIAGNOSTIC_ONLY_ORIGINAL_NATIVE_NOT_PERFORMANCE_QUALIFICATION",
      original_app_source_port=source_port,original_kernel_proxy_port=proxy,
      qpc_frequency=f,matched_2048=MIN_COUNT,
      original_ingress_count=len(ing),original_tx_mailbox_count=len(tx),
      original_rx_wintun_send_count=len(rx),original_inner_fd_read_count=len(fd),
      retransmission_windows=retrans,
      boundary_gap_us={k:us_dist(v,f) for k,v in out.items()},
      severe_ge8ms_windows=long,fd_read_before_kernel_recv_n=len(fd_gap),
      unknown=["Wintun SendPacket return is not Windows kernel TCP consume/ACK",
               "FD_READ can coalesce, zero events does not prove no wake",
               "No pure Rust CPU time from WinSock wall waits"],
      owner_stop="REQUIRES_ORIGINAL_PASS_BOTH_OWNED",
      full_plan029="IN_PROGRESS")
