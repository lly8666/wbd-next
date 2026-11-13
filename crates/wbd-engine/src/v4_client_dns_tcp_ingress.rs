//! PLAN029 original Windows Wintun application TCP/53 request framing.
//! Bounded pure per-stream parser only; product kernel TCP listener, QNAME
//! routing to the sole Direct/Tunnel resolver and exact inverse mapping
//! remain separate, and are NOT claimed by this source module.
use crate::v4_client_split_wire::dns_question;

const MAX_QUESTION_WIRE:usize=2048-42; // one Wintun L3 TCP + DNS length
#[derive(Debug,Clone,PartialEq,Eq)]
pub(crate) struct TcpClientDnsQuestion{
    pub wire:Vec<u8>,
    pub original_id:u16,
    pub qname:String,
    pub qtype:u16,
}
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub(crate) enum TcpClientDnsFramingError{
    InvalidLength,MalformedQuestion,ExtraPayload,AlreadyComplete,
}
#[derive(Default)]
pub(crate) struct TcpClientDnsAssembler{
    buffer:Vec<u8>,expected:Option<usize>,complete:bool,
}
impl TcpClientDnsAssembler{
    pub(crate) fn new()->Self{Self::default()}
    pub(crate) fn pending_bytes(&self)->usize{self.buffer.len()}
    /// One original kernel TCP stream, one length-prefixed question. Never
    /// waits, schedules a thread, or silently selects a new resolver.
    pub(crate) fn ingest(&mut self,chunk:&[u8])
        ->Result<Option<TcpClientDnsQuestion>,TcpClientDnsFramingError>{
        if self.complete{return Err(TcpClientDnsFramingError::AlreadyComplete)}
        if chunk.len()>MAX_QUESTION_WIRE+2-self.buffer.len(){
            return Err(TcpClientDnsFramingError::ExtraPayload)
        }
        self.buffer.extend_from_slice(chunk);
        if self.expected.is_none()&&self.buffer.len()>=2{
            let n=u16::from_be_bytes([self.buffer[0],self.buffer[1]]) as usize;
            if !(17..=MAX_QUESTION_WIRE).contains(&n){
                return Err(TcpClientDnsFramingError::InvalidLength)
            }
            self.expected=Some(n);
        }
        let Some(n)=self.expected else{return Ok(None)};
        if self.buffer.len()<n+2{return Ok(None)}
        if self.buffer.len()!=n+2{
            return Err(TcpClientDnsFramingError::ExtraPayload)
        }
        let raw=&self.buffer[2..];
        let (original_id,qname,qtype)=dns_question(raw)
            .map_err(|_|TcpClientDnsFramingError::MalformedQuestion)?;
        self.complete=true;
        Ok(Some(TcpClientDnsQuestion{wire:raw.to_vec(),
            original_id,qname,qtype}))
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn query(name:&str)->Vec<u8>{
        let mut raw=vec![0u8;12];
        raw[0..2].copy_from_slice(&0x1769u16.to_be_bytes());
        raw[2..4].copy_from_slice(&0x0100u16.to_be_bytes());
        raw[4..6].copy_from_slice(&1u16.to_be_bytes());
        for label in name.split('.'){
            raw.push(label.len() as u8);
            raw.extend_from_slice(label.as_bytes());
        }
        raw.extend_from_slice(&[0,0,1,0,1]);
        let mut frame=(raw.len() as u16).to_be_bytes().to_vec();
        frame.extend(raw);frame
    }
    #[test]
    fn plan029_client_tcp53_fragmented_length_and_qname_same_original_ticket(){
        let msg=query("globalx.example");
        let mut p=TcpClientDnsAssembler::new();
        assert_eq!(p.ingest(&[]),Ok(None));
        assert_eq!(p.ingest(&msg[..1]),Ok(None));
        assert_eq!(p.ingest(&msg[1..2]),Ok(None));
        assert_eq!(p.ingest(&msg[2..12]),Ok(None));
        let r=p.ingest(&msg[12..]).unwrap().unwrap();
        assert_eq!(r.original_id,0x1769);
        assert_eq!(r.qname,"globalx.example");
        assert_eq!(r.qtype,1);
        assert_eq!(r.wire.as_slice(),&msg[2..]);
        assert_eq!(p.ingest(&msg),Err(TcpClientDnsFramingError::AlreadyComplete));
    }
    #[test]
    fn plan029_client_tcp53_rejects_bad_lengths_replies_and_pipelined_query(){
        let raw=query("globalx.example");
        for prefix in [[0,0],[0,16],[0x07,0xff]]{
            let mut p=TcpClientDnsAssembler::new();
            assert_eq!(p.ingest(&prefix),Err(TcpClientDnsFramingError::InvalidLength));
        }
        let mut piped=raw.clone();
        piped.extend_from_slice(&raw);
        let mut p=TcpClientDnsAssembler::new();
        assert_eq!(p.ingest(&piped),Err(TcpClientDnsFramingError::ExtraPayload));
        let mut response=raw.clone();response[2+2]|=0x80;
        let mut p=TcpClientDnsAssembler::new();
        assert_eq!(p.ingest(&response),Err(TcpClientDnsFramingError::MalformedQuestion));
        let mut compress=raw.clone();compress[2+12]=0xc0;
        let mut p=TcpClientDnsAssembler::new();
        assert_eq!(p.ingest(&compress),Err(TcpClientDnsFramingError::MalformedQuestion));
    }
}
