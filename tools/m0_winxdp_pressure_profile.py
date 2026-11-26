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
