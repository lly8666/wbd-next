"""Fixed stress case table; rate is offered application Mbps per active direction, not wire throughput."""
SECONDS=65
CASES=[
 dict(name="fixed-max-up",rate=250,loss=5,profile=6,direction="up",streams=1,delay=80,mtu=1400),
 dict(name="fixed-max-down",rate=400,loss=5,profile=6,direction="down",streams=1,delay=80,mtu=1400),
 dict(name="fixed-max-duplex",rate=250,loss=5,profile=6,direction="duplex",streams=2,delay=80,mtu=1400),
 dict(name="fixed-balanced-loss",rate=400,loss=10,profile=3,direction="duplex",streams=2,delay=200,mtu=1160),
 dict(name="fixed-max-burst",rate=250,loss=10,profile=6,direction="duplex",streams=4,delay=20,mtu=1400,correlation=25),
 dict(name="off-clean-duplex",rate=650,loss=0,profile=-1,direction="duplex",streams=1,delay=20,mtu=1400),
]
CASES=[dict(c,budget=c["rate"],isolate=True,rcvbuf=67108864) for c in CASES]

import os
if os.environ.get("WBD_XDP_PRESSURE_LAB")=="1":
    base=dict(CASES[2],name="capacity-base",rate=400,loss=5,streams=2)
    # Exact same offered workload; isolated capacity and scheduler deltas.
    variants=[
      ("base-first",16384,2048,32,"original"),
      ("rx8192",8192,2048,32,"original"),
      ("rx4096",4096,2048,32,"original"),
      ("tx1024",16384,1024,32,"original"),
      ("rxquantum16",16384,2048,16,"original"),
      ("feedback-first",16384,2048,32,"feedback"),
      ("base-last",16384,2048,32,"original"),
    ]
    CASES=[dict(base,name=name,rx_slots=rx,tx_slots=tx,quantum=q,policy=policy) for name,rx,tx,q,policy in variants]

PATH_MODE=os.environ.get("WBD_XDP_PRESSURE_PATH","bbr")
assert PATH_MODE in ("nat","bbr")
CASES=[dict(c,path_mode=PATH_MODE) for c in CASES]
if PATH_MODE=="nat" and os.environ.get("WBD_XDP_PRESSURE_LAB")=="1":
    for c in (
        dict(name="upload-max",rate=400,direction="up",streams=2,loss=5,delay=80,mtu=1400,profile=6),
        dict(name="download-max",rate=400,direction="down",streams=2,loss=5,delay=80,mtu=1400,profile=6),
        dict(name="duplex-burst",rate=300,direction="duplex",streams=4,loss=10,correlation=25,delay=20,mtu=1400,profile=6),
    ):
        CASES.append(dict(CASES[0],**c))

if os.environ.get("WBD_XDP_STRESS_PHASE")=="upload":
    assert PATH_MODE=="nat" and os.environ.get("WBD_XDP_PRESSURE_LAB")=="1"
    base=dict(CASES[0],direction="up",rate=400,loss=5,profile=6,delay=80,streams=2)
    CASES=[dict(base,name=name,streams=streams,sndbuf=buf,delay=delay,loss=loss) for name,streams,buf,delay,loss in (
      ("default-sendbuf-first",2,0,80,5),
      ("sendbuf4m",2,4194304,80,5),
      ("sendbuf16m",2,16777216,80,5),
      ("eight-streams",8,4194304,80,5),
      ("eight-streams-low-rtt",8,4194304,20,5),
      ("eight-streams-clean",8,4194304,20,0),
      ("default-sendbuf-last",2,0,80,5),
    )]

if os.environ.get("WBD_XDP_STRESS_PHASE")=="carrier-abba":
    assert PATH_MODE=="nat"
    base=dict(CASES[0],sndbuf=4194304)
    workloads=[
        dict(name="clean-down250",direction="down",rate=250,streams=1,loss=0,delay=200,profile=-1,mtu=1160),
        dict(name="clean-down350",direction="down",rate=350,streams=1,loss=0,delay=200,profile=-1,mtu=1160),
        dict(name="lossy-duplex",direction="duplex",rate=400,streams=4,loss=5,delay=80,profile=6,mtu=1400),
    ]
    CASES=[dict(base,**c,arm=arm,group=c["name"]) for c in workloads for arm in "ABBA"]
    # Prior A/C both completed ABBA. Deliberately reverse all main replicas
    # for this follow-up; S repeats the historical lossy ABBA exactly.
    if os.environ.get("H2478_REPLICA")!="S":
        CASES=[dict(c,arm="B" if c["arm"]=="A" else "A") for c in CASES]

# Normal-only tuning, same instrumented WinXDP binary in every arm.
if os.environ.get("WBD_XDP_STRESS_PHASE")=="normal-tune":
    assert PATH_MODE=="nat" and os.environ.get("WBD_XDP_PRESSURE_LAB")=="1"
    base=dict(CASES[0],profile=-1,loss=0,mtu=1460,tx_slots=2048,quantum=32,policy="original",sndbuf=16777216)
    # Hold MTU, socket supply and other parameters fixed within each group.
    workloads=[
        dict(name="normal-down350",direction="down",rate=350,streams=1,delay=200,mtu=1160),
        dict(name="normal-duplex175",direction="duplex",rate=175,streams=4,delay=20),
    ]
    order="BAAB" if os.environ.get("H2478_REPLICA") in "BDFHJL" else "ABBA"
    CASES=[dict(base,**w,arm=arm,group=w["name"],rx_slots=16384 if arm=="A" else 8192) for w in workloads for arm in order]
    for w in (
        dict(name="normal-up350",direction="up",rate=350,streams=4,delay=20),
        dict(name="normal-duplex100-loss1",direction="duplex",rate=100,streams=4,delay=80,loss=1),
        dict(name="normal-duplex50-loss5",direction="duplex",rate=50,streams=4,delay=200,loss=5),
        dict(name="normal-duplex10-loss10",direction="duplex",rate=10,streams=2,delay=200,loss=10),
    ):
        CASES.append(dict(base,**w,rx_slots=16384,arm="A",group=w["name"]))
    CASES=[dict(c,budget=c["rate"]) for c in CASES]

# Same ring and quantum; isolate inactive RSS event syscall cost.
if os.environ.get("WBD_XDP_STRESS_PHASE")=="normal-efficiency":
    assert PATH_MODE=="nat" and os.environ.get("WBD_XDP_PRESSURE_LAB")=="1"
    base=dict(CASES[0],profile=-1,loss=0,mtu=1460,rx_slots=16384,tx_slots=2048,quantum=32,sndbuf=16777216)
    workloads=[
        dict(name="normal-down350",direction="down",rate=350,streams=1,delay=200,mtu=1160),
        dict(name="normal-duplex175",direction="duplex",rate=175,streams=4,delay=20),
        dict(name="normal-up350",direction="up",rate=350,streams=4,delay=20),
    ]
    seq="BAAB" if os.environ.get("H2478_REPLICA") in "BDFHJL" else "ABBA"
    CASES=[dict(base,**w,arm=arm,group=w["name"],policy="original" if arm=="A" else "rx-pending",budget=w["rate"]) for w in workloads for arm in seq]

# Single lane, Maximum fixed FEC in every lossy case; vary only RX capacity.
if os.environ.get("WBD_XDP_STRESS_PHASE")=="maximum-memory":
    assert PATH_MODE=="nat" and os.environ.get("WBD_XDP_PRESSURE_LAB")=="1"
    base=dict(CASES[0],profile=6,mtu=1400,tx_slots=2048,quantum=32,policy="original",sndbuf=16777216,streams=4)
    workloads=[
        dict(name="maximum-loss1-duplex100",direction="duplex",rate=100,delay=80,loss=1),
        dict(name="maximum-loss5-duplex50",direction="duplex",rate=50,delay=200,loss=5),
        dict(name="maximum-loss10-duplex10",direction="duplex",rate=10,delay=200,loss=10),
    ]
    seq="BAAB" if os.environ.get("H2478_REPLICA") in "BDFHJL" else "ABBA"
    CASES=[dict(base,**w,arm=arm,group=w["name"],rx_slots=16384 if arm=="A" else 4096,budget=w["rate"]) for w in workloads for arm in seq]
    # A separate high-pressure asymmetric case: keep reverse ACK traffic real.
    CASES += [dict(base,name="maximum-loss5-up150",direction="up",rate=150,delay=20,loss=5,rx_slots=4096,budget=150,arm="B",group="maximum-loss5-up150"),
              dict(base,name="maximum-loss5-down150",direction="down",rate=150,delay=20,loss=5,rx_slots=4096,budget=150,arm="B",group="maximum-loss5-down150")]

# Same DLL, same descriptor limit; only backing/posted ownership changes.
if os.environ.get("WBD_XDP_STRESS_PHASE")=="pool-qualification":
    assert PATH_MODE=="nat" and os.environ.get("WBD_XDP_PRESSURE_LAB")=="1"
    base=dict(CASES[0],rx_slots=16384,tx_slots=2048,quantum=32,sndbuf=16777216,streams=1,profile=-1,loss=0,mtu=1160)
    workloads=[dict(name="pool-down350",direction="down",rate=350,delay=200)]
    if os.environ.get("WBD_XDP_SINGLE_WIDE")=="1":
        workloads=[
            dict(name="single-down350-mtu1460",direction="down",rate=350,delay=200,mtu=1460),
            dict(name="single-up350",direction="up",rate=350,delay=20,streams=4,mtu=1460),
            dict(name="single-duplex175",direction="duplex",rate=175,delay=20,streams=4,mtu=1460),
            dict(name="single-max-loss1",direction="duplex",rate=100,delay=80,streams=4,mtu=1400,profile=6,loss=1),
            dict(name="single-max-loss5",direction="duplex",rate=50,delay=200,streams=4,mtu=1400,profile=6,loss=5),
            dict(name="single-max-loss10",direction="duplex",rate=10,delay=200,streams=4,mtu=1400,profile=6,loss=10),
        ]
    if os.environ.get("WBD_XDP_SINGLE_WIDE")=="gap":
        workloads=[
            dict(name="single-duplex175",direction="duplex",rate=175,delay=20,streams=4,mtu=1460),
            dict(name="single-max-loss10",direction="duplex",rate=10,delay=200,streams=4,mtu=1400,profile=6,loss=10),
        ]
    seq="BAAB" if os.environ.get("H2478_REPLICA") in "BDFHJL" else "ABBA"
    CASES=[dict(base,**w,arm=arm,group=w["name"],policy="original" if arm=="A" else ("rx-single" if os.environ.get("WBD_XDP_SINGLE_RSS")=="1" else "rx-pool-recycle"),budget=w["rate"]) for w in workloads for arm in seq]

# Same single RSS and Maximum FEC, NAT vs existing transparent BBR.
if os.environ.get("WBD_XDP_SINGLE_WIDE")=="bbr-path":
    workloads=[
        dict(name="single-bbr-loss5-duplex100",direction="duplex",rate=100,delay=80,streams=4,mtu=1400,profile=6,loss=5),
        dict(name="single-bbr-loss10-duplex50",direction="duplex",rate=50,delay=200,streams=4,mtu=1400,profile=6,loss=10),
    ]
    CASES=[dict(base,**w,arm=arm,group=w["name"],policy="rx-single",path_mode="nat" if arm=="A" else "bbr",budget=w["rate"]) for w in workloads for arm in seq]

# Three independent single-variable candidates; identical real RSS mapping
# and outer repair enabled in both arms.
arch=os.environ.get("WBD_XDP_SINGLE_WIDE","")
if arch in ("arch-reclaim","arch-wake","arch-cipher"):
    workloads={
        "arch-reclaim":[dict(name="reclaim-up350",direction="up",rate=350,delay=20,streams=4,mtu=1460),
            dict(name="reclaim-max-duplex100",direction="duplex",rate=100,delay=80,streams=4,mtu=1400,profile=6,loss=1)],
        "arch-wake":[dict(name="wake-down350",direction="down",rate=350,delay=200,mtu=1460),
            dict(name="wake-duplex175",direction="duplex",rate=175,delay=20,streams=4,mtu=1460)],
        "arch-cipher":[dict(name="cipher-up350",direction="up",rate=350,delay=20,streams=4,mtu=1460),
            dict(name="cipher-duplex175",direction="duplex",rate=175,delay=20,streams=4,mtu=1460)],
    }[arch]
    CASES=[dict(base,**w,arm=arm,group=w["name"],policy="rx-single" if arm=="A" else "rx-single-"+arch[5:],budget=w["rate"]) for w in workloads for arm in seq]

# Repeat both counterbalanced orders on each qualified runner. Distinct
# group names retain the original per-quartet receipts without averaging
# across orders. Use the exact already-built candidate DLL.
if os.environ.get("WBD_XDP_ARCH_REPEAT")=="1":
    assert arch in ("arch-reclaim","arch-cipher")
    if arch=="arch-reclaim" and os.environ.get("WBD_XDP_PUBLISH_RECLAIM")!="1":
        # Earlier Maximum TCP was neutral; prioritize upload replication.
        workloads=[w for w in workloads if w["name"]=="reclaim-up350"]
    orders=("BAAB","ABBA") if seq=="BAAB" else ("ABBA","BAAB")
    CASES=[dict(dict(base,**w),name=w["name"]+"-"+order.lower(),
                group=w["name"]+"-"+order.lower(),arm=arm,
                policy="rx-single" if arm=="A" else "rx-single-"+arch[5:],
                budget=w["rate"])
           for w in workloads for order in orders for arm in order]

# Cross-FEC completion study. Frozen candidate DLL, only the TX reclaim
# policy differs. Each qualified runner executes both orders per workload.
if os.environ.get("WBD_XDP_RECLAIM_FEC_GROUP"):
    shard=os.environ["WBD_XDP_RECLAIM_FEC_GROUP"]
    assert arch=="arch-reclaim" and os.environ.get("WBD_XDP_ARCH_REPEAT")=="1"
    profiles={"fixed-low":(0,1),"fixed-mid":(2,3),"fixed-high":(4,5),"fixed-max":(6,)}[shard]
    grades=("light","mild","medium","balanced","high","strong","maximum")
    workloads=[dict(name="reclaim-fixed-"+grades[p]+"-up150",direction="up",
                    rate=150,delay=20,streams=4,mtu=1400,profile=p,loss=0)
               for p in profiles]
    if shard=="fixed-max":
        workloads.append(dict(name="reclaim-max-duplex100",direction="duplex",
                              rate=100,delay=80,streams=4,mtu=1400,profile=6,loss=1))
    orders=("BAAB","ABBA") if seq=="BAAB" else ("ABBA","BAAB")
    CASES=[dict(dict(base,**w),name=w["name"]+"-"+order.lower(),
                group=w["name"]+"-"+order.lower(),arm=arm,
                policy="rx-single" if arm=="A" else "rx-single-reclaim",
                budget=w["rate"])
           for w in workloads for order in orders for arm in order]
