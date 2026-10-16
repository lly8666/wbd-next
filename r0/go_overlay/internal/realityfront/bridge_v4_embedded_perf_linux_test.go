//go:build linux && cgo && wbd_v4_embedded_go

// One deliberately fixed Normal/off development scenario; NOT product
// qualification. The Go control entry is real credential-checked TLS and the
// original Rust owner runs two independent kernel-device worker threads.
// Go runs the *independent* application/raw injectors and observers, never
// calls the per-packet Rust bridge helper during the measurement window.
package realityfront

import (
    "bytes"
    "encoding/binary"
    "encoding/json"
    "fmt"
    "net"
    "os"
    "os/exec"
    "sort"
    "strings"
    "sync"
    "sync/atomic"
    "syscall"
    "testing"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/tlsrecord"
)

const (
    m0Perf10TargetBits = 10_000_000
    m0PerfC2SMagic uint32 = 0x43325331
    m0PerfS2CMagic uint32 = 0x53324331
)
var m0PerfIPv4Sizes = []int{64,256,1200,1369}

type m0PerfDir struct {
    sentPackets atomic.Uint64
    sentIPBytes atomic.Uint64
    sentUDPBytes atomic.Uint64
    receivedPackets atomic.Uint64
    receivedIPBytes atomic.Uint64
    receivedUDPBytes atomic.Uint64
    invalid atomic.Uint64
    duplicated atomic.Uint64
    sendErrors atomic.Uint64
    // Only ONE receiving goroutine writes these two structures.
    seen map[uint64]bool
    latencyMicros []int64
}
func m0PerfFill(b []byte,magic uint32,id uint64,phase byte) {
    binary.BigEndian.PutUint32(b[:4],magic)
    binary.BigEndian.PutUint64(b[4:12],id)
    binary.BigEndian.PutUint64(b[12:20],uint64(time.Now().UnixNano()))
    b[20]=phase
    for i:=21;i<len(b);i++{b[i]=byte(id)^byte(i)}
}
func m0PerfVerify(p []byte,magic uint32,expectedSize int,stats *m0PerfDir){
    if len(p)<21||binary.BigEndian.Uint32(p[:4])!=magic{
        stats.invalid.Add(1);return
    }
    id:=binary.BigEndian.Uint64(p[4:12])
    if expectedSize!=m0PerfIPv4Sizes[id%uint64(len(m0PerfIPv4Sizes))]||len(p)!=expectedSize-28{
        stats.invalid.Add(1);return
    }
    for i:=21;i<len(p);i++{
        if p[i]!=byte(id)^byte(i){stats.invalid.Add(1);return}
    }
    if stats.seen[id]{stats.duplicated.Add(1);return}
    stats.seen[id]=true
    if p[20]!=1{return} // warmup, not part of 60s denominator
    stats.receivedPackets.Add(1)
    stats.receivedIPBytes.Add(uint64(expectedSize))
    stats.receivedUDPBytes.Add(uint64(len(p)))
    if id%16==0 {
        elapsed:=time.Now().UnixNano()-int64(binary.BigEndian.Uint64(p[12:20]))
        if elapsed>=0&&elapsed<30_000_000_000{
            stats.latencyMicros=append(stats.latencyMicros,elapsed/1000)
        }
    }
}
func m0PerfPercentile(samples []int64,centile int) int64{
    if len(samples)==0{return -1}
    sort.Slice(samples,func(i,j int)bool{return samples[i]<samples[j]})
    idx:=(len(samples)*centile+99)/100-1
    if idx<0{idx=0}
    if idx>=len(samples){idx=len(samples)-1}
    return samples[idx]
}
func m0PerfRusage() (uint64,uint64){
    var ru syscall.Rusage
    if syscall.Getrusage(syscall.RUSAGE_SELF,&ru)!=nil{return 0,0}
    user:=uint64(ru.Utime.Sec)*1_000_000_000+uint64(ru.Utime.Usec)*1000
    system:=uint64(ru.Stime.Sec)*1_000_000_000+uint64(ru.Stime.Usec)*1000
    return user,system
}
func m0PerfRead(path string)string{
    b,err:=os.ReadFile(path);if err!=nil{return "UNAVAILABLE"}
    v:=strings.TrimSpace(string(b))
    if len(v)>420{v=v[:420]}
    return v
}
func m0PerfReadRSS()string{
    v,err:=os.ReadFile("/proc/self/status")
    if err!=nil{return "UNAVAILABLE"}
    rows:=strings.Split(string(v),"\n")
    var vals []string
    for _,line:=range rows{
        if strings.HasPrefix(line,"VmRSS:")||strings.HasPrefix(line,"VmHWM:")||
            strings.HasPrefix(line,"Threads:"){
            vals=append(vals,strings.TrimSpace(line))
        }
    }
    return strings.Join(vals,"; ")
}
func m0PerfDevCounters()map[string]string{
    p:="/sys/class/net/lo/statistics/"
    return map[string]string{
        "lo_rx_packets":m0PerfRead(p+"rx_packets"),
        "lo_tx_packets":m0PerfRead(p+"tx_packets"),
        "lo_rx_dropped":m0PerfRead(p+"rx_dropped"),
        "lo_tx_dropped":m0PerfRead(p+"tx_dropped"),
        "cpu_quota":m0PerfRead("/sys/fs/cgroup/cpu.max"),
        "cpu_stat":m0PerfRead("/sys/fs/cgroup/cpu.stat"),
        "cpu_psi":m0PerfRead("/proc/pressure/cpu"),
        "memory_current":m0PerfRead("/sys/fs/cgroup/memory.current"),
        "memory_peak":m0PerfRead("/sys/fs/cgroup/memory.peak"),
        "rss_status":m0PerfReadRSS(),
    }
}

func TestR0V4EmbeddedNormalOff10MbpsDevelopment(t *testing.T) {
    if os.Getenv("WBD_REAL_TUN")!="1"||os.Getenv("WBD_M0_PERF_BASELINE")!="1"{
        t.Skip("explicit real Linux kernel owned namespace performance Action only")
    }
    // Always the SAME predefined scenario, no variable seed / packet mix
    // or dynamic MTU change to rescue a failing throughput gate.
    // Paired-only workload, old Go emits UDP payload 64/256/1200B;
    // new actual IPv4 inner packet is payload+28B. Equal 10Mbps app
    // offered rates, identical 1:1:1 mix. Default standalone unchanged.
    paired:=os.Getenv("WBD_M0_PAIRED_OLD_NEW")=="1"
    rateBits:=m0Perf10TargetBits
    if paired {
        m0PerfIPv4Sizes=[]int{92,284,1228}
        rateBits=m0Perf10TargetBits*(92+284+1228)/(64+256+1200)
    }
    const name="wbdperf0"
    const warmup=10*time.Second
    const measure=60*time.Second
    dev,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{t.Fatal(err)}
    defer dev.Close()
    var req [40]byte
    copy(req[:16],[]byte(name))
    binary.LittleEndian.PutUint16(req[16:18],0x1001)
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,dev.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&req[0])))
    if errno!=0{t.Fatalf("real IFF_TUN/NO_PI creation: %v",errno)}
    for _,args:=range [][]string{
        {"addr","add","10.241.24.1/24","dev",name},
        {"link","set","dev",name,"up"},
    }{
        if out,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("real kernel TUN setup %v: %v %s",args,e,out)
        }
    }
    lo,e:=net.InterfaceByName("lo")
    if e!=nil||lo.Index<1{t.Fatalf("real loopback interface: %v",e)}
    src:=net.IPv4(10,241,24,2)
    dst:=net.IPv4(10,241,24,1)
    app,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:dst,Port:0})
    if e!=nil{t.Fatal(e)}
    defer app.Close()
    store,e:=NewV4EpochStore(1)
    if e!=nil{t.Fatal(e)}
    b:=&v4EmbeddedNativeBridge{}
    client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,CipherChaCha)
    if ce!=nil||se!=nil||client==nil||server==nil||!b.committed{
        t.Fatalf("original protected credential-checked Go TLS: client=%v server=%v",ce,se)
    }
    t.Cleanup(func(){
        if err:=b.stopRelease();err!=nil{t.Errorf("Rust Stop/join/release: %v",err)}
        if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);err!=nil{
            t.Errorf("Go protected lane Release: %v",err)
        }
    })
    if e:=b.attachRawRx(uint32(lo.Index));e!=nil{t.Fatal(e)}
    if e:=b.attachKernelTun(dev.Fd(),name);e!=nil{t.Fatal(e)}
    raw,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_RAW)
    if e!=nil{t.Fatal(e)}
    defer syscall.Close(raw)
    if e:=syscall.SetsockoptInt(raw,syscall.IPPROTO_IP,syscall.IP_HDRINCL,1);e!=nil{t.Fatal(e)}
    peer,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
    if e!=nil{t.Fatal(e)}
    defer syscall.Close(peer)
    if e:=syscall.Bind(peer,&syscall.SockaddrInet4{Addr:b.originalFlow.ClientIP});e!=nil{t.Fatal(e)}
    tv:=syscall.NsecToTimeval((120*time.Millisecond).Nanoseconds())
    if e:=syscall.SetsockoptTimeval(peer,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&tv);e!=nil{t.Fatal(e)}
    cold,e:=client.ColdSnapshot()
    if e!=nil{t.Fatal(e)}
    clientLimit,serverLimit:=cold.RecordLimits()
    if int(serverLimit)!=1400{
        t.Fatalf("original C2S negotiated record wire limit must be 1400 got=%d",serverLimit)
    }
    // Do NOT assume the C2S record limit (1400-31=1369) is also the
    // S2C effective M4 carrier route/advertised peer MSS budget.
    // Query the same original ACTIVE Rust scoped owner and actual Linux
    // route: the selected last size class is the intersection of BOTH
    // legal directional budgets, fixed once for this exact measurement.
    observedS2C,err:=b.observedRealRustTxIPv4MTU(uint32(lo.Index))
    if err!=nil{t.Fatal(err)}
    effectiveMax:=int(observedS2C)
    if effectiveMax>int(serverLimit)-31{effectiveMax=int(serverLimit)-31}
    if effectiveMax<=1200{
        t.Fatalf("observed genuine normal/off inner MTU %d cannot fit declared 1200 size class",effectiveMax)
    }
    if !paired {m0PerfIPv4Sizes[3]=effectiveMax}
    if paired&&effectiveMax<1228{t.Fatalf("paired real MTU %d cannot fit shared UDP1200",effectiveMax)}
    t.Logf("M0_DEV_EFFECTIVE_INNER_MTU observed_rust_s2c_ipv4=%d c2s_record_ip_max=%d mixed_fourth_ipv4=%d",
        observedS2C,int(serverLimit)-31,effectiveMax)
    c2sSealer,e:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().C2S,int(serverLimit),CipherChaCha)
    if e!=nil{t.Fatal(e)}
    s2cOpener,e:=tlsrecord.NewOpenerForCipher(cold.DirectionKeys().S2C,int(clientLimit),CipherChaCha)
    if e!=nil{t.Fatal(e)}
    if e:=b.startRustOwnerLoop(uint32(lo.Index));e!=nil{t.Fatal(e)}
    // Record exact Linux peer scope for kernel incoming and outgoing.
    appPort:=uint16(app.LocalAddr().(*net.UDPAddr).Port)
    inbound:=&m0PerfDir{seen:make(map[uint64]bool)}
    outbound:=&m0PerfDir{seen:make(map[uint64]bool)}
    start:=time.Now().Add(200*time.Millisecond)
    measuring:=start.Add(warmup)
    end:=measuring.Add(measure)
    drainEnd:=end.Add(3*time.Second)
    errorC:=make(chan string,32)
    var wg sync.WaitGroup
    send:=func(stats *m0PerfDir,magic uint32,c2s bool){
        defer wg.Done()
        next:=time.Now()
        for time.Now().Before(start){time.Sleep(1*time.Millisecond)}
        // 10Mbps each logical IPv4 business direction; count *all* inner
        // IP header bytes in target, not ciphertext/raw TCP wire bytes.
        credits:=float64(0)
        var sequence uint64
        var tcpSeq=b.rxBoundary
        for time.Now().Before(end){
            now:=time.Now()
            credits+=float64(now.Sub(next).Nanoseconds())*
                float64(rateBits)/8/1e9
            next=now
            // Bounded 20ms local pacing credit; no unbounded catch-up queue.
            if credits>25000{credits=25000}
            size:=m0PerfIPv4Sizes[sequence%uint64(len(m0PerfIPv4Sizes))]
            if credits<float64(size){time.Sleep(500*time.Microsecond);continue}
            credits-=float64(size)
            inner:=make([]byte,size-28)
            phase:=byte(0)
            if !now.Before(measuring){phase=1}
            m0PerfFill(inner,magic,sequence,phase)
            if c2s{
                ip:=make([]byte,size)
                ip[0]=0x45;ip[8]=64;ip[9]=17
                binary.BigEndian.PutUint16(ip[2:4],uint16(size))
                binary.BigEndian.PutUint16(ip[4:6],uint16(sequence))
                copy(ip[12:16],src.To4());copy(ip[16:20],dst.To4())
                binary.BigEndian.PutUint16(ip[10:12],v4RawCheckSum(ip[:20]))
                binary.BigEndian.PutUint16(ip[20:22],40001)
                binary.BigEndian.PutUint16(ip[22:24],appPort)
                binary.BigEndian.PutUint16(ip[24:26],uint16(size-20))
                copy(ip[28:],inner)
                rec,pn,err:=c2sSealer.Seal(ip)
                if err!=nil||pn!=sequence {
                    stats.sendErrors.Add(1)
                    select{case errorC<-fmt.Sprintf("Go original C2S TLS seal pn=%d seq=%d err=%v",pn,sequence,err):default:}
                    return
                }
                packet:=v4RawC2STestPacket(rec,tcpSeq,b.originalFlow)
                if err:=syscall.Sendto(raw,packet,0,
                    &syscall.SockaddrInet4{Addr:b.originalFlow.ServerIP});err!=nil{
                    stats.sendErrors.Add(1)
                    select{case errorC<-fmt.Sprintf("kernel C2S raw send: %v",err):default:}
                    return
                }
                tcpSeq+=uint32(len(rec))
            }else{
                n,err:=app.WriteToUDP(inner,&net.UDPAddr{IP:src,Port:42001})
                if err!=nil||n!=len(inner){
                    stats.sendErrors.Add(1)
                    select{case errorC<-fmt.Sprintf("kernel S2C UDP app n=%d err=%v",n,err):default:}
                    return
                }
            }
            if phase==1 {
                stats.sentPackets.Add(1)
                stats.sentIPBytes.Add(uint64(size))
                stats.sentUDPBytes.Add(uint64(len(inner)))
            }
            sequence++
        }
    }
    receiveC2S:=func(){
        defer wg.Done()
        for time.Now().Before(drainEnd){
            if e:=app.SetReadDeadline(time.Now().Add(130*time.Millisecond));e!=nil{
                select{case errorC<-e.Error():default:};return
            }
            p:=make([]byte,1600)
            n,who,err:=app.ReadFromUDP(p)
            if err!=nil{
                if ne,yes:=err.(net.Error);yes&&ne.Timeout(){continue}
                select{case errorC<-fmt.Sprintf("C2S independent UDP reader: %v",err):default:};return
            }
            if who==nil||!who.IP.Equal(src){inbound.invalid.Add(1);continue}
            m0PerfVerify(p[:n],m0PerfC2SMagic,n+28,inbound)
        }
    }
    receiveS2C:=func(){
        defer wg.Done()
        for time.Now().Before(drainEnd){
            rawbuf:=make([]byte,2048)
            n,_,err:=syscall.Recvfrom(peer,rawbuf,0)
            if err!=nil{
                if err==syscall.EAGAIN||err==syscall.EWOULDBLOCK||err==syscall.EINTR {continue}
                select{case errorC<-fmt.Sprintf("S2C independent raw reader: %v",err):default:};return
            }
            if n<41||rawbuf[0]>>4!=4||rawbuf[9]!=6{continue}
            ihl:=int(rawbuf[0]&0x0f)*4
            if ihl<20||ihl+20>n{continue}
            if !bytes.Equal(rawbuf[12:16],b.originalFlow.ServerIP[:])||
                !bytes.Equal(rawbuf[16:20],b.originalFlow.ClientIP[:])||
                binary.BigEndian.Uint16(rawbuf[ihl:ihl+2])!=b.originalFlow.ServerPort||
                binary.BigEndian.Uint16(rawbuf[ihl+2:ihl+4])!=b.originalFlow.ClientPort||
                rawbuf[ihl+13]&0x08==0{continue}
            h:=int(rawbuf[ihl+12]>>4)*4
            if h<20||ihl+h+32>n{continue}
            opened,e:=s2cOpener.OpenRecord(rawbuf[ihl+h:n])
            if e!=nil||opened.Kind!=tlsrecord.KindLINK||len(opened.Payload)<28{
                outbound.invalid.Add(1);continue
            }
            ip:=opened.Payload
            if ip[0]>>4!=4||ip[9]!=17||!bytes.Equal(ip[12:16],dst.To4())||
                !bytes.Equal(ip[16:20],src.To4())||len(ip)<28{
                outbound.invalid.Add(1);continue
            }
            m0PerfVerify(ip[28:],m0PerfS2CMagic,len(ip),outbound)
        }
    }
    wg.Add(4)
    go send(inbound,m0PerfC2SMagic,true)
    go send(outbound,m0PerfS2CMagic,false)
    go receiveC2S()
    go receiveS2C()
    time.Sleep(time.Until(measuring))
    cpuBeforeUser,cpuBeforeSys:=m0PerfRusage()
    ownerRxBefore,ownerTxBefore,err:=b.rustOwnerWorkerCPU()
    if err!=nil{t.Fatal(err)}
    kernelBefore:=m0PerfDevCounters()
    time.Sleep(time.Until(end))
    cpuAfterUser,cpuAfterSys:=m0PerfRusage()
    ownerRxAfter,ownerTxAfter,err:=b.rustOwnerWorkerCPU()
    if err!=nil{t.Fatal(err)}
    kernelAfter:=m0PerfDevCounters()
    wg.Wait()
    var failures []string
    for len(errorC)>0{failures=append(failures,<-errorC)}
    loopStats,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    seconds:=measure.Seconds()
    mbps:=func(bytes uint64)float64{return float64(bytes)*8/seconds/1e6}
    samples:=func(d *m0PerfDir)map[string]any{
        offered:=d.sentPackets.Load();got:=d.receivedPackets.Load()
        missing:=uint64(0);if offered>got{missing=offered-got}
        return map[string]any{
            "offered_ipv4_business_packets":offered,
            "delivered_ipv4_business_packets":got,
            "missing_or_not_delivered":missing,
            "offered_ipv4_bytes":d.sentIPBytes.Load(),
            "delivered_ipv4_bytes":d.receivedIPBytes.Load(),
            "offered_udp_payload_bytes":d.sentUDPBytes.Load(),
            "delivered_udp_payload_bytes":d.receivedUDPBytes.Load(),
            "offered_ipv4_mbps":mbps(d.sentIPBytes.Load()),
            "delivered_ipv4_mbps":mbps(d.receivedIPBytes.Load()),
            "invalid_received":d.invalid.Load(),
            "duplicate_received":d.duplicated.Load(),
            "injector_send_errors":d.sendErrors.Load(),
            "sampled_oneway_same_host_app_delivery_age_p50_us":m0PerfPercentile(d.latencyMicros,50),
            "sampled_oneway_same_host_app_delivery_age_p99_us":m0PerfPercentile(d.latencyMicros,99),
            "latency_samples":len(d.latencyMicros),
        }
    }
    offeredC:=mbps(inbound.sentIPBytes.Load())
    offeredS:=mbps(outbound.sentIPBytes.Load())
    deliveredC:=mbps(inbound.receivedIPBytes.Load())
    deliveredS:=mbps(outbound.receivedIPBytes.Load())
    status:="MEASUREMENT_RECORDED_NOT_PRODUCT_PASS"
    lowerBound:=9.5*float64(rateBits)/float64(m0Perf10TargetBits)
    if offeredC<lowerBound||offeredS<lowerBound {status="INVALID_INJECTOR"}
    if offeredC>=lowerBound&&offeredS>=lowerBound&&(deliveredC<lowerBound||deliveredS<lowerBound){
        status="OBSERVED_DELIVERY_SHORTFALL_CAUSE_UNDETERMINED"
    }
    if len(failures)>0||inbound.invalid.Load()>0||outbound.invalid.Load()>0{
        status="INVALID_MEASUREMENT"
    }
    const processNotSeparate="Original Rust worker CPU clocks are independent Linux CLOCK_THREAD_CPUTIME_ID; total process CPU includes Go injector/receivers, runtime and original Rust; subtracting worker clocks yields non-worker residual, not isolated Go injector-process CPU. Full separated host/veth product baseline NOT_RUN."
    res:=map[string]any{
        "scope":"GOV005_FIRST_DEVELOPER_PERF_DIAGNOSTIC_SAME_GO_PROCESS_ORIGINAL_RUST_OWNER",
        "result":status,"normal_lane_count":1,"fec":"fixed_off",
        "cipher":"chacha20_poly1305_original_go_tls", "diagnostic_logging":false,
        "backend":"real_linux_network_namespace_loopback_raw_ipv4_tcp_and_tun",
        "production_features":0,"product_qualification":"NOT_RUN",
        "desired_rate_mbps_each_direction_ipv4_inner_business":float64(rateBits)/1e6,
        "paired_legacy_app_payload_mbps":map[bool]any{true:10.0,false:"NOT_APPLICABLE"}[paired],
        "experiment_profile":map[bool]string{true:"PAIRED_OLD_GO_VS_NEW_RUST_SAME_VM_DIAGNOSTIC",false:"NORMAL_OFF_SINGLE_SOURCE_10MBPS_DEVELOPMENT"}[paired],
        "mix_packet_ipv4_lengths_bytes":m0PerfIPv4Sizes,
        "original_rust_observed_s2c_effective_ipv4_mtu_bytes":observedS2C,
        "original_go_c2s_record_wire_limit_bytes":serverLimit,
        "packet_mix_by_count":map[bool]string{true:"1:1:1_UDP_APPLICATION_PAYLOAD_64_256_1200",false:"1:1:1:1_IPV4_64_256_1200_EFFECTIVE_MAX"}[paired],
        "warmup_seconds":10,"measure_seconds":60,
        "receiver_drain_seconds":3,"timing":"wall_monotonic_scheduled_window",
        "c2s":samples(inbound),"s2c":samples(outbound),
        "original_rust_worker_rx_cpu_seconds":float64(ownerRxAfter-ownerRxBefore)/1e9,
        "original_rust_worker_tx_cpu_seconds":float64(ownerTxAfter-ownerTxBefore)/1e9,
        "combined_process_user_cpu_seconds":float64(cpuAfterUser-cpuBeforeUser)/1e9,
        "combined_process_system_cpu_seconds":float64(cpuAfterSys-cpuBeforeSys)/1e9,
        "cpu_attribution_limitation":processNotSeparate,
        "linux_before":kernelBefore,"linux_after":kernelAfter,
        "rust_owner_loop_stats":loopStats,
        "independent_RTT_p99":"NOT_MEASURED",
        "full_queue_age_p99":"NOT_INSTRUMENTED",
        "interprocess_injector_cpu":"NOT_RUN",
        "host_capacity_diagnosis":"REQUIRES_CGROUP_STAT_INTERPRETATION",
        "true_external_received_SYN":"NOT_RUN",
        "held_async_driver_stop_B04":"NOT_RUN",
        "injector_errors":failures,
    }
    encoded,e:=json.MarshalIndent(res,"","  ")
    if e!=nil{t.Fatal(e)}
    out:=os.Getenv("WBD_M0_PERF_RECEIPT")
    if out==""{t.Fatal("missing owned exact performance receipt path")}
    if e:=os.WriteFile(out,append(encoded,'\n'),0600);e!=nil{t.Fatal(e)}
    t.Logf("M0_DEV_NORMAL_OFF_10MBPS_RECEIPT result=%s C2S_offered=%.3f C2S_delivered=%.3f S2C_offered=%.3f S2C_delivered=%.3f worker_rx_cpu_s=%.4f worker_tx_cpu_s=%.4f source_window=10s+60s",
        status,offeredC,deliveredC,offeredS,deliveredS,
        float64(ownerRxAfter-ownerRxBefore)/1e9,float64(ownerTxAfter-ownerTxBefore)/1e9)
    // Workflow does not convert measurement receipt success to 10Mbps PASS.
    // INVALID cases stay explicit. No artificially unbounded retries.
    if len(failures)>0{t.Errorf("real baseline failed integrity/io: %v",failures)}
    if status=="INVALID_MEASUREMENT"{t.Error("baseline data invalid; see exact JSON")}
    // Legitimate capacity/injector insufficiency is a recorded NOT_QUALIFIED
    // developer diagnostic, never an automatic product PASS.
}
