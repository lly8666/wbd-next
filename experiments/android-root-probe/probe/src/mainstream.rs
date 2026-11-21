//! One real unprivileged App's DNS UDP/53 and TCP HTTP through an owned TUN.
//! Only the previously scoped UID + synthetic /32 can reach this test peer.
//! Not Android system DNS, real Internet, or a production TCP/IP stack.
use super::{ip_header,pseudo_checksum,udp_packet,wait_read};
use serde_json::{json,Value};
use std::io::{self,ErrorKind};
use std::os::fd::RawFd;
use std::time::{Duration,Instant};
const IP:[u8;4]=[198,18,254,2];
const DNS_QUESTION:&[u8]=b"\x05probe\x03wbd\x04test\x00\x00\x01\x00\x01";
fn packet_write(fd:RawFd,pkt:&[u8])->io::Result<usize>{
 let n=unsafe{libc::write(fd,pkt.as_ptr().cast(),pkt.len())};
 if n<0{return Err(io::Error::last_os_error())}
 if n as usize !=pkt.len(){return Err(io::Error::new(ErrorKind::WriteZero,"TUN short packet write"))}
 Ok(n as usize)
}
fn ipv4<'a>(buf:&'a [u8])->Option<(u8,[u8;4],&'a [u8])>{
 if buf.len()<28||buf[0]>>4!=4{return None}
 let h=(buf[0]&15) as usize*4;
 let total=u16::from_be_bytes([buf[2],buf[3]]) as usize;
 if h!=20||total>buf.len()||total<h+8||buf[16..20]!=IP{return None}
 Some((buf[9],[buf[12],buf[13],buf[14],buf[15]],&buf[h..total]))
}
fn dns(fd:RawFd)->io::Result<Value>{
 let deadline=Instant::now()+Duration::from_secs(7);
 let mut buf=[0u8;2048];
 while Instant::now()<deadline{
  let n=match wait_read(fd,&mut buf,350){Ok(n)=>n,
    Err(e) if e.kind()==ErrorKind::TimedOut=>continue,Err(e)=>return Err(e)};
  let Some((proto,src,udp))=ipv4(&buf[..n])else{continue};
  if proto!=17||udp.len()<20||u16::from_be_bytes([udp[2],udp[3]])!=53{continue}
  let q=&udp[8..];
  if q.len()!=12+DNS_QUESTION.len()||q[2..4]!=[1,0]||
   q[4..6]!=[0,1]||&q[12..]!=DNS_QUESTION{continue}
  let mut answer=Vec::with_capacity(q.len()+16);
  answer.extend_from_slice(&q[0..2]); // exact DNS transaction ID from App
  answer.extend_from_slice(&[0x81,0x80,0,1,0,1,0,0,0,0]); // NOERROR, 1 A
  answer.extend_from_slice(DNS_QUESTION);
  answer.extend_from_slice(&[0xc0,0x0c,0,1,0,1,0,0,0,30,0,4,198,18,254,2]);
  let sport=u16::from_be_bytes([udp[0],udp[1]]);
  let pkt=udp_packet(IP,src,53,sport,&answer);
  let written=packet_write(fd,&pkt)?;
  return Ok(json!({"status":"SUPPORTED_IN_SCOPE","transport":"ordinary App UDP/53",
    "qname":"probe.wbd.test.","answer":"198.18.254.2",
    "query_bytes":q.len(),"response_bytes":answer.len(),
    "tun_reply_ip_bytes":written,"app_source_port":sport}));
 }
 Err(io::Error::new(ErrorKind::TimedOut,"real App UDP53 DNS query not observed on TUN"))
}
fn tcp_packet(src:[u8;4],dst:[u8;4],sport:u16,dport:u16,
              seq:u32,ack:u32,flags:u8,payload:&[u8])->Vec<u8>{
 let mut pkt=vec![0u8;40+payload.len()];
 ip_header(&mut pkt,6,src,dst);
 pkt[20..22].copy_from_slice(&sport.to_be_bytes());
 pkt[22..24].copy_from_slice(&dport.to_be_bytes());
 pkt[24..28].copy_from_slice(&seq.to_be_bytes());
 pkt[28..32].copy_from_slice(&ack.to_be_bytes());
 pkt[32]=0x50;
 pkt[33]=flags;
 pkt[34..36].copy_from_slice(&65535u16.to_be_bytes());
 pkt[40..].copy_from_slice(payload);
 let c=pseudo_checksum(src,dst,6,&pkt[20..]);
 pkt[36..38].copy_from_slice(&c.to_be_bytes());
 pkt
}
fn tcp(fd:RawFd,token:&str)->io::Result<Value>{
 let deadline=Instant::now()+Duration::from_secs(9);
 let mut buf=[0u8;2048];
 let mut client:Option<([u8;4],u16,u32,u32)>=None;
 let server_isn=0x4d_32_51_00u32;
 let mut reply_info:Option<(u32,usize,usize,usize)>=None;
 let request_start=format!("GET /wbd/{token} HTTP/1.0\r\n");
 while Instant::now()<deadline{
  let n=match wait_read(fd,&mut buf,400){Ok(n)=>n,
    Err(e) if e.kind()==ErrorKind::TimedOut=>continue,Err(e)=>return Err(e)};
  let Some((proto,src,seg))=ipv4(&buf[..n])else{continue};
  if proto!=6||seg.len()<20||u16::from_be_bytes([seg[2],seg[3]])!=49493{continue}
  let sport=u16::from_be_bytes([seg[0],seg[1]]);
  let seq=u32::from_be_bytes([seg[4],seg[5],seg[6],seg[7]]);
  let ack=u32::from_be_bytes([seg[8],seg[9],seg[10],seg[11]]);
  let h=((seg[12]>>4) as usize)*4;
  if h<20||h>seg.len(){continue}
  let flags=seg[13];
  if flags&0x04!=0{return Err(io::Error::new(ErrorKind::ConnectionReset,"App TCP reset"))}
  if flags&0x02!=0{
    if client.is_none(){client=Some((src,sport,seq,0))}
    let pkt=tcp_packet(IP,src,49493,sport,server_isn,seq.wrapping_add(1),0x12,&[]);
    packet_write(fd,&pkt)?;
    continue;
  }
  let Some((peer,port,syn,_))=client else{continue};
  if peer!=src||port!=sport{continue}
  if let Some((expected_ack,request_bytes,http_bytes,reply_ip_bytes))=reply_info{
    if flags&0x10!=0&&ack==expected_ack{
      let fin=tcp_packet(IP,src,49493,sport,expected_ack,seq,0x11,&[]);
      let _=packet_write(fd,&fin)?;
      return Ok(json!({"status":"SUPPORTED_IN_SCOPE","real_app_tcp_syn_seen":true,
        "real_app_http_get_seen":true,"normal_app_acked_tun_response":true,
        "request_bytes":request_bytes,"http_response_bytes":http_bytes,
        "tun_http_ip_packet_bytes":reply_ip_bytes,"source_port":port,
        "destination":"198.18.254.2:49493","http_status":200}));
    }
    continue;
  }
  let payload=&seg[h..];
  if payload.is_empty(){continue}
  if seq!=syn.wrapping_add(1)||!payload.starts_with(request_start.as_bytes()){
     return Err(io::Error::new(ErrorKind::InvalidData,"unexpected TCP segment or HTTP path"))
  }
  let body=format!("wbd-ok-{token}");
  let response=format!("HTTP/1.0 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",body.len());
  let client_ack=seq.wrapping_add(payload.len() as u32);
  let pkt=tcp_packet(IP,src,49493,sport,server_isn.wrapping_add(1),client_ack,0x18,response.as_bytes());
  let written=packet_write(fd,&pkt)?;
  let expected_ack=server_isn.wrapping_add(1+response.len() as u32);
  reply_info=Some((expected_ack,payload.len(),response.len(),written));
 }
 Err(io::Error::new(ErrorKind::TimedOut,
     format!("TCP App SYN/HTTP/ACK incomplete: syn_seen={},response_written={}",
        client.is_some(),reply_info.is_some())))
}
fn underlay_completion(fd:RawFd,token:&str)->io::Result<Value>{
 // App sends this marker ONLY after a netd-bound TCP socket has received an
 // actual response from emulator host 10.0.2.2. The root-owned /32 rule is
 // still active until this packet is observed on the TUN.
 let expected=format!("wbd-underlay-{token}");
 let deadline=Instant::now()+Duration::from_secs(34);
 let mut buf=[0u8;2048];
 while Instant::now()<deadline{
  let n=match wait_read(fd,&mut buf,300){Ok(n)=>n,
      Err(e) if e.kind()==ErrorKind::TimedOut=>continue,Err(e)=>return Err(e)};
  let Some((proto,_src,seg))=ipv4(&buf[..n])else{continue};
  if proto!=17||seg.len()<8||u16::from_be_bytes([seg[2],seg[3]])!=49494{continue}
  if &seg[8..]==expected.as_bytes(){
   return Ok(json!({"status":"SUPPORTED_IN_SCOPE",
      "real_app_underlay_completed_before_rule_release":true,
      "marker_bytes":expected.len(),"marker_udp_ip_bytes":n}));
  }
 }
 Err(io::Error::new(ErrorKind::TimedOut,
     "ordinary App host-underlay completion marker absent while UID route active"))
}
pub fn serve(fd:RawFd,token:&str)->io::Result<Value>{
 let dns=dns(fd)?;
 let tcp=tcp(fd,token)?;
 let marker=underlay_completion(fd,token)?;
 Ok(json!({"status":"SUPPORTED_IN_SCOPE","dns_udp53":dns,"tcp_http":tcp,
     "underlay_marker":marker,
     "scope":"one normal App synthetic IPv4 /32 to root TUN; netd host underlay is separate, no system DNS/Internet"}))
}
