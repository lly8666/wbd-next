#!/usr/bin/env python3
"""Read TRUE classic PCAP frames; rebuild actual client-to-server TCP streams.

No scapy or other package required. A separate tshark decode is archived by CI.
The TLS-looking custom records are not genuine negotiated TLS1.3 records.
"""
import argparse, collections, json, pathlib, struct

CUSTOM=38443
REAL_TLS=38444
KEY64=(1<<64)-1
def roll64(k,n):
    return ((k<<n)|(k>>(64-n)))&KEY64
def tailword(seq):
    return roll64(((seq*0x9e3779b97f4a7c15)&KEY64)^0x6c616e5f6e6f7365,17)
def marker(seq,aes):
    v=(seq*137+59)&0xffff
    return (0xf000|(v&0x0fff)) if aes else (v%0xf000)
def each_packet(path):
    raw=path.read_bytes()
    magic=raw[:4]
    order={b'\xd4\xc3\xb2\xa1':'<', b'\xa1\xb2\xc3\xd4':'>',
           b'\x4d\x3c\xb2\xa1':'<', b'\xa1\xb2\x3c\x4d':'>'}.get(magic)
    if not order:raise AssertionError(f'unsupported capture format magic {magic.hex()}')
    _,maj,minv,tz,sig,snap,linktype=struct.unpack_from(order+'IHHIIII',raw,0)
    assert maj==2 and minv==4, (maj,minv)
    pos=24
    while pos+16<=len(raw):
        sec,micro,length,orig=struct.unpack_from(order+'IIII',raw,pos)
        pos+=16
        if pos+length>len(raw):raise AssertionError('truncated packet capture')
        frame=memoryview(raw)[pos:pos+length]
        pos+=length
        if linktype==1:
            if len(frame)<14:continue
            protocol=struct.unpack_from('>H',frame,12)[0]
            offset=14
        elif linktype==113: # Linux cooked v1
            if len(frame)<16:continue
            protocol=struct.unpack_from('>H',frame,14)[0]
            offset=16
        elif linktype==276: # Linux cooked v2
            if len(frame)<20:continue
            protocol=struct.unpack_from('>H',frame,0)[0]
            offset=20
        elif linktype==101:
            protocol=0x0800
            offset=0
        else:
            raise AssertionError(f'unsupported pcap linktype={linktype}')
        if protocol!=0x0800 or len(frame)<offset+20:continue
        ip=frame[offset:]
        if ip[0]>>4!=4 or ip[9]!=6:continue
        ihl=(ip[0]&0xf)*4
        total=struct.unpack_from('>H',ip,2)[0]
        if ihl<20 or len(ip)<ihl+20:continue
        tcp=ip[ihl:]
        src,dst=struct.unpack_from('>HH',tcp,0)
        if dst not in (CUSTOM,REAL_TLS):continue
        seq=struct.unpack_from('>I',tcp,4)[0]
        tcphl=(tcp[12]>>4)*4
        if tcphl<20:continue
        datalen=max(0,min(total,len(ip))-ihl-tcphl)
        if datalen==0:continue
        payload=bytes(tcp[tcphl:tcphl+datalen])
        if not payload:continue
        yield dict(src=src,dst=dst,seq=seq,data=payload,frame_len=orig)
def reconstruct(pkts):
    # One source TCP port for each fixture; TCP records can cross segments.
    streams=collections.defaultdict(list)
    for p in pkts:streams[(p['src'],p['dst'])].append(p)
    assert len(streams)==2, {str(k):len(v) for k,v in streams.items()}
    complete={}
    meta={}
    for key,segments in streams.items():
        byseq={}
        for p in segments:
            pos=p['seq']
            if pos not in byseq or len(p['data'])>len(byseq[pos]):
                byseq[pos]=p['data']
        stream=bytearray()
        wanted=None
        gap_bytes=0
        for seq,data in sorted(byseq.items()):
            if wanted is None:wanted=seq
            if seq>wanted:
                gap_bytes+=seq-wanted
                wanted=seq
            if seq+len(data)<=wanted:continue
            offset=max(0,wanted-seq)
            stream.extend(data[offset:])
            wanted=seq+len(data)
        assert gap_bytes==0,(key,gap_bytes)
        complete[key[1]]=bytes(stream)
        meta[str(key[1])]=dict(observed_tcp_payload_packets=len(segments),
             unique_tcp_sequence_segments=len(byseq),total_tcp_stream_bytes=len(stream),
             bytes_lost_in_capture=gap_bytes,
             tcp_payload_segment_sizes=dict(collections.Counter(len(p['data']) for p in segments)))
    return complete,meta
def extract_records(stream, label):
    records=[]
    off=0
    while off<len(stream):
        assert off+5<=len(stream),(label,off,'partial head')
        ct=stream[off]
        maj,minv=stream[off+1],stream[off+2]
        body=int.from_bytes(stream[off+3:off+5],'big')
        assert 0<body<17000,(label,off,'size',body)
        n=5+body
        assert off+n<=len(stream),(label,off,'truncated',n,len(stream)-off)
        records.append(stream[off:off+n])
        off+=n
    return records
def parse_custom(records):
    assert len(records)==100, len(records)
    modes=[]
    sizes=[]
    record_types=collections.Counter()
    old_header_redundancy=0
    for i,wire in enumerate(records):
        seq=i+1
        assert wire[:3]==b'\x17\x03\x03',(i,wire[:3])
        record_types[wire[0]]+=1
        tail_mask=tailword(seq).to_bytes(8,'big')
        restored=bytearray(wire)
        for j in range(8):restored[-8+j]^=tail_mask[j]
        val=int.from_bytes(restored[-2:],'big')
        aes=val>=0xf000
        assert val==marker(seq,aes),(i,hex(val),aes)
        expected=1368 if aes else 1347
        assert len(wire)==expected,(i,len(wire),expected)
        if wire[5:8]==b'\x17\x03\x03':old_header_redundancy+=1
        modes.append('AES_FALLBACK' if aes else 'PASS_THROUGH')
        sizes.append(len(wire))
    assert modes.count('PASS_THROUGH')==80
    assert modes.count('AES_FALLBACK')==20
    assert old_header_redundancy==0,old_header_redundancy
    counts=collections.Counter(modes)
    return dict(record_count=len(records),record_type_counts=dict(record_types),
        record_sizes=dict(collections.Counter(sizes)),first_5B_all_TLS_like=True,
        correct_outer_lengths=len(records),known_mode_counts=dict(counts),
        high_level_mode_visible_after_unkeyed_tail_inverse=True,
        byte5_nested_tls_header_count=old_header_redundancy,
        mode_marker_all_recovered=True,actual_tls13_cryptographic_validity=False)
def parse_real_tls(records):
    types=collections.Counter()
    versions=collections.Counter()
    for r in records:
        types[str(r[0])]+=1
        versions[r[1:3].hex()]+=1
    assert int(types['22'])>=1, ('reference TLS13 handshake record absent',types)
    assert int(types['23'])>=30, ('reference TLS13 application records absent',types)
    return dict(record_count=len(records),content_types=types,legacy_version_fields=versions,
      genuine_TLS13_handshake_was_performed_by_Go_tls=True,
      app_payload_sent_count=30)
def main():
    arg=argparse.ArgumentParser()
    arg.add_argument('--pcap',required=True,type=pathlib.Path)
    arg.add_argument('--output',required=True,type=pathlib.Path)
    a=arg.parse_args()
    packets=list(each_packet(a.pcap))
    streams,meta=reconstruct(packets)
    result={
      'scope':'Actual CI native loopback TCP+pcap with tcpdump. NOT 2-host physical LAN; no native WBD production wire.',
      'method':'Independent stdlib classic pcap IPv4/TCP parser, full application stream reassembly; tshark parsed separately.',
      'capture_size_bytes':a.pcap.stat().st_size,
      'link_ip_tcp_frame_count_to_server':len(packets),
      'tcp':meta,
      'custom':parse_custom(extract_records(streams[CUSTOM],'custom')),
      'real_go_tls13_reference':parse_real_tls(extract_records(streams[REAL_TLS],'genuine tls13')),
      'security_limitations':[
         'A TLS-looking 17 03 03 content_type23 frame is not a standards-compliant TLS 1.3 session',
         'The real TLS 1.3 capture includes authenticated handshake records; custom fast records have no handshake',
         'Tail XOR mutates original TLS AEAD tag and length until custom receiver restores them',
         '2B mode marker is reversible via public rolling 8B XOR; AES vs fast packet length differs by 21 bytes',
         'Implicit counter assumes lossless ordered stream; fast record has no WBD authenticated MAC',
         'Real LAN PMTU, packet loss, RTT, retransmission and wire throughput not measured'
      ],
    }
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
