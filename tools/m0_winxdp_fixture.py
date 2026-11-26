"""Low-perturbation measurements shared by both WinXDP comparisons.
Raw evidence belongs in the case directory/artifact, not the Actions stream.
"""
import json, threading, time
def start_observers(clock,stop,start,case,snapshot,wsl):
    def boundaries():
        for target,key in ((10,"steady_before"),(55,"steady_after")):
            if stop.wait(max(0,start+target-time.monotonic())):return
            clock[key+"_mono"]=time.monotonic()
            try:clock[key]=snapshot()
            except Exception as e:clock[key+"_error"]=repr(e)
    def diagnostic():
        if stop.wait(max(0,start+25-time.monotonic())):return
        port=5202 if case<0 else 5400
        # Only the measured TCP flow. No full-host socket dump or concurrent
        # tcpdump of thousands of packets on a CPU-limited benchmark.
        selector=f"( sport = :{port} or dport = :{port} )"
        for key,prefix in (("active_ss",()),("active_origin_ss",("ip","netns","exec","h2442origin"))):
            if stop.is_set():return
            try:clock[key]=wsl(*prefix,"ss","-tinm","state","established",selector,timeout=8)
            except Exception as e:clock[key+"_error"]=repr(e)
    threads=[threading.Thread(target=f,daemon=True) for f in (boundaries,diagnostic)]
    for t in threads:t.start()
    return threads
def concise(row):
    keys=("case","mode","rate_mbps","status","bytes","end","rx_mbps","client_ready","client_stop","client_panic","mode_ok","cold_attempts","cold_first_try","same_cold_handoff","xdp_stop","xdp_rx_stop","netem_active","netem_drops","steady_cpu","comparable","functional","clean_candidate","error","shape_clear_error","steady_before_error","steady_after_error")
    out={k:row[k] for k in keys if k in row}
    for k in ("steady_drops","business_drops"):
        if k in row:
            d=row[k]
            out[k]={**{n:d[n] for n in ("available","zero","error") if n in d},"nonzero":{n:v for n,v in d.get("deltas",{}).items() if v}}
    return out
def functional(row):
    return (row.get("status")=="MEASURED_EXACT" and row.get("netem_active",{}).get("both_used") is True and row.get("mode_ok") is True and row.get("client_stop") is True)
if __name__=="__main__":
    test={"case":1,"mode":"B","status":"MEASURED_EXACT","netem_active":{"both_used":True},"mode_ok":True,"client_stop":True,"active_ss":"x"*1000000}
    assert functional(test) and len(json.dumps(concise(test)))<512
