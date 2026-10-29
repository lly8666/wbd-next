//! PLAN027: direction-scoped mature quality summaries, not per-record receipts.
//! Pure low-frequency accounting. M0 must provide authenticated, replay-checked
//! reports and actual definitely-sent originals; missing reports mean UNKNOWN.
use wbd_types::{LaneKey,MonoNs,RecordPn};
use crate::budget::WireDirection;

pub const MAX_WINDOW_PNS:u64=1024;
pub const EXPIRE_NS:u64=10_000_000_000;
pub const WIRE_LEN:usize=36;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct WindowKey {
    pub lane:LaneKey,pub epoch:[u8;16],pub direction:WireDirection,
    pub id:u64,pub first:RecordPn,pub last:RecordPn,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct ClosedWindow {
    pub key:WindowKey,pub first_sent:u16,pub closed_at:MonoNs,
    pub complete:bool,pub capacity_limited:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct MatureReport {
    pub key:WindowKey,pub received_unique:u16,pub possibly_repaired:u16,
    pub mature:bool,pub complete:bool,pub capacity_limited:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum QualityError {
    WrongWindow,InvalidRange,InvalidCounts,Empty,Stale,ClockReversed,
    NotMature,Unknown,InvalidWire,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct LossBounds {pub first:u16,pub lower:u16,pub upper:u16}
impl LossBounds {
    pub fn lower_bps(self)->u32{u32::from(self.lower)*10_000/u32::from(self.first)}
    pub fn upper_bps(self)->u32{u32::from(self.upper)*10_000/u32::from(self.first)}
}
pub fn assess(sent:&ClosedWindow,report:&MatureReport,now:MonoNs)
    ->Result<LossBounds,QualityError>{
    if sent.key!=report.key{return Err(QualityError::WrongWindow);}
    let span=sent.key.last.0.checked_sub(sent.key.first.0)
        .and_then(|v|v.checked_add(1))
        .filter(|&n|n<=MAX_WINDOW_PNS).ok_or(QualityError::InvalidRange)?;
    if sent.first_sent==0{return Err(QualityError::Empty);}
    if u64::from(sent.first_sent)>span||report.received_unique>sent.first_sent
        ||report.possibly_repaired>sent.first_sent {
        return Err(QualityError::InvalidCounts);
    }
    if now.0<sent.closed_at.0{return Err(QualityError::ClockReversed);}
    if now.0-sent.closed_at.0>EXPIRE_NS{return Err(QualityError::Stale);}
    if !report.mature{return Err(QualityError::NotMature);}
    if !sent.complete||!report.complete||sent.capacity_limited
        ||report.capacity_limited{return Err(QualityError::Unknown);}
    let lower=sent.first_sent-report.received_unique;
    let upper=lower.saturating_add(report.possibly_repaired).min(sent.first_sent);
    Ok(LossBounds{first:sent.first_sent,lower,upper})
}

/// Compact 36-byte v2 Quality TLV body. Native AEAD/epoch/lane authentication
/// is mandatory and EXTERNAL; a decoded body is never independent authority.
/// Flags: mature, full coverage, receiver capacity, possible repair.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct WireReport {
    pub id:u64,pub first:u64,pub last:u64,pub first_sent:u16,
    pub received_unique:u16,pub possibly_repaired:u16,
    pub mature:bool,pub complete:bool,pub capacity_limited:bool,
}
impl WireReport {
    fn valid(self)->Result<(),QualityError>{
        let span=self.last.checked_sub(self.first)
            .and_then(|v|v.checked_add(1))
            .filter(|&v|v<=MAX_WINDOW_PNS).ok_or(QualityError::InvalidRange)?;
        if u64::from(self.first_sent)>span||self.received_unique>self.first_sent
            ||self.possibly_repaired>self.first_sent {
            return Err(QualityError::InvalidCounts);
        }
        Ok(())
    }
    pub fn encode(self)->Result<[u8;WIRE_LEN],QualityError>{
        self.valid()?;
        let mut b=[0u8;WIRE_LEN];
        b[0]=2;
        b[1]=u8::from(self.mature)|u8::from(self.complete)<<1
            |u8::from(self.capacity_limited)<<2
            |u8::from(self.possibly_repaired!=0)<<3;
        b[2..10].copy_from_slice(&self.id.to_be_bytes());
        b[10..18].copy_from_slice(&self.first.to_be_bytes());
        b[18..26].copy_from_slice(&self.last.to_be_bytes());
        b[26..28].copy_from_slice(&self.first_sent.to_be_bytes());
        b[28..30].copy_from_slice(&self.received_unique.to_be_bytes());
        b[30..32].copy_from_slice(&self.possibly_repaired.to_be_bytes());
        Ok(b)
    }
    pub fn decode(b:&[u8])->Result<Self,QualityError>{
        if b.len()!=WIRE_LEN||b[0]!=2||b[1]&!15!=0||
            b[32..].iter().any(|&v|v!=0){return Err(QualityError::InvalidWire);}
        let u64at=|n:usize|{
            let mut a=[0u8;8];a.copy_from_slice(&b[n..n+8]);u64::from_be_bytes(a)
        };
        let u16at=|n:usize|{
            let mut a=[0u8;2];a.copy_from_slice(&b[n..n+2]);u16::from_be_bytes(a)
        };
        let out=Self{id:u64at(2),first:u64at(10),last:u64at(18),
            first_sent:u16at(26),received_unique:u16at(28),
            possibly_repaired:u16at(30),mature:b[1]&1!=0,
            complete:b[1]&2!=0,capacity_limited:b[1]&4!=0};
        if (b[1]&8!=0)!=(out.possibly_repaired!=0){
            return Err(QualityError::InvalidWire);
        }
        out.valid()?;
        Ok(out)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use wbd_types::TunnelKey;
    fn key()->WindowKey{WindowKey{
        lane:LaneKey{tunnel:TunnelKey{slot:2,generation:3},slot:4,generation:5},
        epoch:[7;16],direction:WireDirection::ServerToClient,
        id:9,first:RecordPn(100),last:RecordPn(109)}}
    fn pair()->(ClosedWindow,MatureReport){
        let key=key();(ClosedWindow{key,first_sent:10,closed_at:MonoNs(0),
            complete:true,capacity_limited:false},
            MatureReport{key,received_unique:9,possibly_repaired:1,mature:true,
                complete:true,capacity_limited:false})
    }
    #[test]
    fn r2_plan027_quality_mature_bounds_and_wire_roundtrip(){
        let (s,r)=pair();let b=assess(&s,&r,MonoNs(3_500_000_000)).unwrap();
        assert_eq!((b.lower,b.upper,b.lower_bps(),b.upper_bps()),
            (1,2,1000,2000));
        let w=WireReport{id:9,first:100,last:109,first_sent:10,
            received_unique:9,possibly_repaired:1,mature:true,complete:true,
            capacity_limited:false};
        assert_eq!(WireReport::decode(&w.encode().unwrap()),Ok(w));
    }
    #[test]
    fn r2_plan027_quality_unknown_never_zero_and_wrong_epoch_rejected(){
        let (s,r)=pair();let mut q=r;q.key.epoch[0]^=1;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::WrongWindow));
        q=r;q.mature=false;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::NotMature));
        q=r;q.complete=false;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::Unknown));
        q=r;q.capacity_limited=true;
        assert_eq!(assess(&s,&q,MonoNs(1)),Err(QualityError::Unknown));
        assert_eq!(assess(&s,&r,MonoNs(EXPIRE_NS+1)),Err(QualityError::Stale));
        let mut t=s;t.first_sent=0;
        assert_eq!(assess(&t,&r,MonoNs(1)),Err(QualityError::Empty));
    }
    #[test]
    fn r2_plan027_quality_malformed_wire_and_range_fail_closed(){
        let (s,r)=pair();
        let w=WireReport{id:9,first:100,last:109,first_sent:10,
            received_unique:9,possibly_repaired:1,mature:true,complete:true,
            capacity_limited:false};
        let mut b=w.encode().unwrap();b[0]=3;
        assert_eq!(WireReport::decode(&b),Err(QualityError::InvalidWire));
        b=w.encode().unwrap();b[32]=1;
        assert_eq!(WireReport::decode(&b),Err(QualityError::InvalidWire));
        b=w.encode().unwrap();b[1]^=8;
        assert_eq!(WireReport::decode(&b),Err(QualityError::InvalidWire));
        assert_eq!(WireReport{last:1200,..w}.encode(),Err(QualityError::InvalidRange));
        assert_eq!(WireReport{received_unique:11,..w}.encode(),
            Err(QualityError::InvalidCounts));
        let t=ClosedWindow{closed_at:MonoNs(10),..s};
        assert_eq!(assess(&t,&r,MonoNs(9)),Err(QualityError::ClockReversed));
    }
}
