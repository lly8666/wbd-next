"""Single source-locked WL workload for the real Windows/WSL2 product harness.

V2 is observational, not a qualification waiver. Existing N0/P200 profiles
remain unchanged; only explicit v2 selects this parser.
"""
import hashlib,json,pathlib,re

def read_scenario(path):
    p=pathlib.Path(path)
    cfg=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(cfg,dict) or cfg.get("schema_version")!=1:
        raise ValueError("WL_V2_BAD_SCHEMA")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}",str(cfg.get("scenario_id",""))):
        raise ValueError("WL_V2_BAD_NAME")
    # Opt-in per-mode scenario. Historical V2 scenes without this field
    # remain exactly Normal, including their canonical scenario SHA.
    mode=cfg.get("public_mode","normal")
    if mode not in ("normal","fixed","game2","game4","game2-fec","game4-fec","auto"):
        raise ValueError("WL_V2_UNSUPPORTED_PUBLIC_MODE")
    for field,minimum,maximum in (("duration_s",10,300),("warmup_s",0,30),("drain_s",2,30),("tun_mtu",1280,1500)):
        value=cfg.get(field)
        if type(value) is not int or not minimum<=value<=maximum:
            raise ValueError("WL_V2_BAD_"+field)
    if cfg["tun_mtu"] not in (1280,1400,1500):
        raise ValueError("WL_V2_UNSUPPORTED_TUN_MTU")
    if type(cfg.get("seed")) is not int or not 0<=cfg["seed"]<2**32:
        raise ValueError("WL_V2_BAD_SEED")
    for direction in ("windows_to_linux","linux_to_windows"):
        d=cfg.get(direction)
        if not isinstance(d,dict):raise ValueError("WL_V2_MISSING_"+direction)
        for field,lo,hi in (("offered_mbps",0,350),("delay_ms",0,2000),("loss_pct",0,60)):
            value=d.get(field)
            if type(value) not in (int,float) or not lo<=value<=hi:
                raise ValueError("WL_V2_BAD_"+direction+"_"+field)
        limit=d.get("tc_rate_mbps")
        if limit is not None and (type(limit) not in (int,float) or not 1<=limit<=500):
            raise ValueError("WL_V2_BAD_TC_RATE")
        mix=d.get("packet_mix")
        if not isinstance(mix,list) or not 1<=len(mix)<=12:
            raise ValueError("WL_V2_BAD_PACKET_MIX")
        total=0
        for row in mix:
            if not isinstance(row,dict) or type(row.get("udp_payload_bytes")) is not int or not 48<=row["udp_payload_bytes"]<=min(1200,cfg["tun_mtu"]-80):
                raise ValueError("WL_V2_BAD_PACKET_SIZE")
            n=row.get("packets_weight")
            if type(n) is not int or not 1<=n<=100:raise ValueError("WL_V2_BAD_PACKET_WEIGHT")
            total+=n
        if total>100:raise ValueError("WL_V2_PACKET_MIX_TOO_LARGE")
    tun_queue=cfg.get("linux_tun_txqlen_packets")
    if tun_queue is not None:
        if (mode!="normal" or cfg["duration_s"] not in (60,300) or
            type(tun_queue) is not int or tun_queue not in (1024,2048,4096) or
            any(cfg[d]["loss_pct"]!=0 for d in
                ("windows_to_linux","linux_to_windows"))):
            raise ValueError("WL_V2_TUN_QLEN_BOUNDED_NORMAL_LOSS0_ONLY")
    stages=cfg.get("impairment_stages")
    if stages is not None:
        if mode!="auto" or not isinstance(stages,list) or not 3<=len(stages)<=12:
            raise ValueError("WL_V2_BAD_AUTO_STAGE_SCOPE")
        previous=-1
        for i,stage in enumerate(stages):
            if not isinstance(stage,dict) or set(stage)!={"start_s","windows_to_linux","linux_to_windows"}:
                raise ValueError("WL_V2_BAD_AUTO_STAGE_SHAPE")
            start=stage["start_s"]
            if type(start) is not int or not previous<start<cfg["duration_s"] or (i==0 and start!=0):
                raise ValueError("WL_V2_BAD_AUTO_STAGE_CLOCK")
            previous=start
            for direction in ("windows_to_linux","linux_to_windows"):
                point=stage[direction]
                if not isinstance(point,dict) or set(point)!={"delay_ms","loss_pct"}:
                    raise ValueError("WL_V2_BAD_AUTO_STAGE_PROFILE")
                for field,upper in (("delay_ms",2000),("loss_pct",60)):
                    v=point[field]
                    if type(v) not in (int,float) or not 0<=v<=upper:
                        raise ValueError("WL_V2_BAD_AUTO_STAGE_VALUE")
                if i==0 and any(point[field]!=cfg[direction][field] for field in ("delay_ms","loss_pct")):
                    raise ValueError("WL_V2_AUTO_STAGE_ZERO_MISMATCH")
        if stages[-1]["start_s"]>cfg["duration_s"]-120:
            raise ValueError("WL_V2_AUTO_NO_120S_FINAL_OBSERVATION")
    encoded=json.dumps(cfg,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    cfg["scenario_sha256"]=hashlib.sha256(encoded).hexdigest()
    return cfg

def profile(cfg,side):
    if side not in ("windows","linux"):raise ValueError("WL_V2_BAD_SIDE")
    d=cfg["windows_to_linux" if side=="windows" else "linux_to_windows"]
    return {"delay_ms":d["delay_ms"],"loss_pct":d["loss_pct"],
            "tc_mbit":d["tc_rate_mbps"],"offered_mbps":d["offered_mbps"],
            "duration_s":cfg["duration_s"],
            "packet_mix":d["packet_mix"],
            "scenario_sha256":cfg["scenario_sha256"]}
