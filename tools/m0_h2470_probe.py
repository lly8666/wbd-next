"""Short, single-thread guest-visible CPU probes. Never overlap business traffic."""
import hashlib,json,os,pathlib,platform,ssl,statistics,sys,time,zlib

def measure(fn,batch=256,seconds=.65):
    start=time.perf_counter();cpu=time.thread_time();n=0
    while time.perf_counter()-start<seconds:
        fn(batch);n+=batch
    elapsed=time.perf_counter()-start;active=time.thread_time()-cpu
    return {"operations":n,"wall_s":elapsed,"thread_cpu_s":active,
            "ops_per_wall_s":n/elapsed,"ops_per_cpu_s":n/active if active>0 else None,
            "cpu_wall_ratio":active/elapsed}

def run(role,seconds=.65,repeats=3):
    assert role in ("windows","wsl","relay","server")
    short=bytes(range(64));packet=(bytes(range(256))*5)[:1160]
    def crc(n):
        for _ in range(n):zlib.crc32(short)
    def sha(n):
        for _ in range(n):hashlib.sha256(packet).digest()
    def integer(n):
        x=1
        for _ in range(n):x=(x*1664525+1013904223)&0xffffffff
        return x
    workloads={}
    for name,fn in (("crc32_64B",crc),("sha256_1160B",sha),("integer32",integer)):
        fn(1024)
        samples=[measure(fn,seconds=seconds) for _ in range(repeats)]
        workloads[name]={"samples":samples,
            "median_ops_per_wall_s":statistics.median(x["ops_per_wall_s"] for x in samples),
            "median_ops_per_cpu_s":statistics.median(x["ops_per_cpu_s"] for x in samples if x["ops_per_cpu_s"] is not None),
            "median_cpu_wall_ratio":statistics.median(x["cpu_wall_ratio"] for x in samples)}
    return {"schema":"m0-h2470-cpu-probe-v1","role":role,"run_id":os.environ.get("GITHUB_RUN_ID"),
            "source_sha":os.environ.get("GITHUB_SHA"),"machine":platform.machine(),"system":platform.system(),
            "processor":platform.processor(),"python":platform.python_version(),"openssl":ssl.OPENSSL_VERSION,
            "zlib":zlib.ZLIB_RUNTIME_VERSION,"logical_cpu_count":os.cpu_count(),
            "seconds_per_sample":seconds,"repeats":repeats,"workloads":workloads,
            "scope":"single Python thread; C library hashing/CRC and Python integer loop proxies, not WBD throughput or physical host capacity"}

if __name__=="__main__":
    row=run(sys.argv[1])
    if len(sys.argv)>2:
        path=pathlib.Path(sys.argv[2]);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(row,indent=2)+"\n")
    else:print(json.dumps(row))
