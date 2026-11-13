//! PLAN029 portable FakeIP journal: ONLY the single owning cold/sparse
//! DNS worker appends bounded batches and gets a real filesystem sync
//! before acknowledging any client-visible synthetic IPv4 answer.
//! No per-packet persistence, background writer thread, system registry,
//! Go FFI packet pump or DNS/network fallback. An incomplete/corrupt file
//! stops NEW FakeIP issuance rather than silently reusing a stale address.
//! The host passes its owned portable application-directory absolute path.
use std::collections::{HashMap,HashSet};
use std::fs::{self,File,OpenOptions};
use std::io::{self,Read,Write};
use std::path::{Path,PathBuf};
use crate::v4_client_fake_pool::{FakeAllocator,FakeSnapshotEntry,FakeKey,FakeError};

const MAGIC:&[u8;8]=b"WBD029F1";
const MAX_JOURNAL_BYTES:usize=16*1024*1024;
const MAX_BATCH_BYTES:usize=256*1024;
const MAX_BATCH_ENTRIES:usize=128;
#[derive(Debug)]
pub(crate) enum FakeJournalError{
    InvalidPath,Corrupt,ForeignFile,Limit,Conflict,
    File(io::Error),Pool(FakeError),
}
impl PartialEq for FakeJournalError{
    fn eq(&self,other:&Self)->bool{
        matches!((self,other),
            (Self::InvalidPath,Self::InvalidPath)|
            (Self::Corrupt,Self::Corrupt)|
            (Self::ForeignFile,Self::ForeignFile)|
            (Self::Limit,Self::Limit)|
            (Self::Conflict,Self::Conflict))
    }
}
impl Eq for FakeJournalError{}
fn ioe(e:io::Error)->FakeJournalError{FakeJournalError::File(e)}
fn u16be(d:&[u8])->u16{u16::from_be_bytes([d[0],d[1]])}
fn u32be(d:&[u8])->u32{u32::from_be_bytes([d[0],d[1],d[2],d[3]])}
fn u64be(d:&[u8])->u64{
    u64::from_be_bytes(d[..8].try_into().expect("checked length"))
}
fn crc32(data:&[u8])->u32{
    let mut crc=!0u32;
    for &b in data{
        crc^=u32::from(b);
        for _ in 0..8{
            crc=(crc>>1)^if crc&1!=0{0xedb8_8320}else{0};
        }
    }
    !crc
}
fn encode(entries:&[FakeSnapshotEntry])->Result<Vec<u8>,FakeJournalError>{
    if entries.is_empty()||entries.len()>MAX_BATCH_ENTRIES{
        return Err(FakeJournalError::Limit)
    }
    let mut body=Vec::with_capacity(entries.len()*96);
    body.extend_from_slice(&(entries.len() as u16).to_be_bytes());
    let mut dedupe=HashSet::with_capacity(entries.len());
    for e in entries{
        if !dedupe.insert(e.fake4)||e.key.qname.len()>253||
            e.key.canonical.len()>253||e.key.qname.is_empty()||
            e.key.canonical.is_empty()||
            e.key.real4==0||e.key.real4==u32::MAX||
            e.quarantine_until_ms<e.issued_until_ms ||
            e.quarantine_until_ms-e.issued_until_ms<600_000{
            return Err(FakeJournalError::Corrupt)
        }
        body.extend_from_slice(&e.fake4.to_be_bytes());
        body.extend_from_slice(&e.key.real4.to_be_bytes());
        body.extend_from_slice(&e.key.policy_rev.to_be_bytes());
        body.extend_from_slice(&e.key.resolver_rev.to_be_bytes());
        body.extend_from_slice(&e.issued_until_ms.to_be_bytes());
        body.extend_from_slice(&e.quarantine_until_ms.to_be_bytes());
        body.extend_from_slice(&(e.key.qname.len() as u16).to_be_bytes());
        body.extend_from_slice(&(e.key.canonical.len() as u16).to_be_bytes());
        body.extend_from_slice(e.key.qname.as_bytes());
        body.extend_from_slice(e.key.canonical.as_bytes());
        if body.len()>MAX_BATCH_BYTES{return Err(FakeJournalError::Limit)}
    }
    let mut frame=Vec::with_capacity(body.len()+8);
    frame.extend_from_slice(&(body.len() as u32).to_be_bytes());
    frame.extend_from_slice(&crc32(&body).to_be_bytes());
    frame.extend_from_slice(&body);
    Ok(frame)
}
fn read_batch(payload:&[u8])->Result<Vec<FakeSnapshotEntry>,FakeJournalError>{
    if payload.len()<2{return Err(FakeJournalError::Corrupt)}
    let count=usize::from(u16be(&payload[..2]));
    if count==0||count>MAX_BATCH_ENTRIES{return Err(FakeJournalError::Corrupt)}
    let mut cursor=2usize;
    let mut found=Vec::with_capacity(count);
    for _ in 0..count{
        if payload.len().saturating_sub(cursor)<44{
            return Err(FakeJournalError::Corrupt)
        }
        let d=&payload[cursor..];
        let fake4=u32be(&d[0..4]);
        let real4=u32be(&d[4..8]);
        let policy_rev=u64be(&d[8..16]);
        let resolver_rev=u64be(&d[16..24]);
        let issued_until_ms=u64be(&d[24..32]);
        let quarantine_until_ms=u64be(&d[32..40]);
        let n1=usize::from(u16be(&d[40..42]));
        let n2=usize::from(u16be(&d[42..44]));
        cursor+=44;
        if n1==0||n2==0||n1>253||n2>253||
            payload.len().saturating_sub(cursor)<n1+n2{
            return Err(FakeJournalError::Corrupt)
        }
        let qname=std::str::from_utf8(&payload[cursor..cursor+n1])
            .map_err(|_|FakeJournalError::Corrupt)?.to_string();
        cursor+=n1;
        let canonical=std::str::from_utf8(&payload[cursor..cursor+n2])
            .map_err(|_|FakeJournalError::Corrupt)?.to_string();
        cursor+=n2;
        if quarantine_until_ms<issued_until_ms||
            quarantine_until_ms-issued_until_ms<600_000{
            return Err(FakeJournalError::Corrupt)
        }
        found.push(FakeSnapshotEntry{
            fake4,
            key:FakeKey{qname,canonical,real4,policy_rev,resolver_rev},
            issued_until_ms,quarantine_until_ms,
        });
    }
    if cursor!=payload.len(){return Err(FakeJournalError::Corrupt)}
    Ok(found)
}
/// Exact owned file parse with identity checks, before the caller invokes
/// FakeAllocator::restore(now_unix_ms). No repairing/silently truncating
/// corrupt WAL tails: an acknowledged stale fake may still be cached by OS.
pub(crate) fn load_journal(data:&[u8])
    ->Result<Vec<FakeSnapshotEntry>,FakeJournalError>{
    if data.len()<MAGIC.len()||&data[..MAGIC.len()]!=MAGIC{
        return Err(FakeJournalError::ForeignFile)
    }
    if data.len()>MAX_JOURNAL_BYTES{return Err(FakeJournalError::Limit)}
    let mut pos=MAGIC.len();
    let mut by_fake=HashMap::<u32,FakeSnapshotEntry>::new();
    let mut by_key=HashMap::<FakeKey,u32>::new();
    while pos<data.len(){
        if data.len()-pos<8{return Err(FakeJournalError::Corrupt)}
        let size=u32be(&data[pos..pos+4]) as usize;
        let expected=u32be(&data[pos+4..pos+8]);
        pos+=8;
        if size<2||size>MAX_BATCH_BYTES||size>data.len()-pos{
            return Err(FakeJournalError::Corrupt)
        }
        let body=&data[pos..pos+size];
        if crc32(body)!=expected{return Err(FakeJournalError::Corrupt)}
        for row in read_batch(body)? {
            if let Some(old_fake)=by_key.get(&row.key){
                if *old_fake!=row.fake4{
                    return Err(FakeJournalError::Conflict)
                }
            }
            if let Some(old)=by_fake.get(&row.fake4){
                if old.key!=row.key{
                    // The old key's quarantine must end before this
                    // new allocation was issued. No in-place rebind of
                    // an active DNS/flow mapping during the protection.
                    if old.quarantine_until_ms>row.issued_until_ms{
                        return Err(FakeJournalError::Conflict)
                    }
                    by_key.remove(&old.key);
                }else if old.issued_until_ms>row.issued_until_ms ||
                         old.quarantine_until_ms>row.quarantine_until_ms{
                    return Err(FakeJournalError::Conflict)
                }
            }
            by_key.insert(row.key.clone(),row.fake4);
            by_fake.insert(row.fake4,row);
        }
        pos+=size;
    }
    let mut rows=by_fake.into_values().collect::<Vec<_>>();
    rows.sort_by_key(|e|e.fake4);
    Ok(rows)
}
pub(crate) struct FakeJournal{
    path:PathBuf,
    file:File,
    bytes:usize,
    poisoned:bool,
}
impl FakeJournal {
    /// Current Windows application directory path, not a temp profile or
    /// global machine store. The file must be owned, regular and have the
    /// strict record magic. Never overwrite a foreign file.
    pub fn open(path:&Path)->Result<(Self,Vec<FakeSnapshotEntry>),FakeJournalError>{
        if !path.is_absolute()||path.file_name().is_none(){
            return Err(FakeJournalError::InvalidPath)
        }
        let parent=path.parent().ok_or(FakeJournalError::InvalidPath)?;
        if !parent.is_dir(){return Err(FakeJournalError::InvalidPath)}
        if path.exists(){
            let meta=fs::symlink_metadata(path).map_err(ioe)?;
            if !meta.is_file()||meta.file_type().is_symlink(){
                return Err(FakeJournalError::ForeignFile)
            }
        }else{
            let mut new=OpenOptions::new().create_new(true).write(true)
                .open(path).map_err(ioe)?;
            new.write_all(MAGIC).map_err(ioe)?;
            new.sync_all().map_err(ioe)?;
        }
        let bytes=fs::read(path).map_err(ioe)?;
        let rows=load_journal(&bytes)?;
        let file=OpenOptions::new().append(true).open(path).map_err(ioe)?;
        Ok((Self{path:path.to_path_buf(),file,bytes:bytes.len(),poisoned:false},rows))
    }
    /// One batch = one durable commit. The caller coalesces sparse DNS
    /// allocations in the existing native scheduler: NEVER fsync per Wintun
    /// packet or per DATA, and never announce an entry until this returns.
    /// A failure leaves unacknowledged fakes unusable; no DNS side fallback.
    pub fn persist_batch(&mut self,pool:&mut FakeAllocator,ips:&[u32])
        ->Result<(),FakeJournalError>{
        if self.poisoned{return Err(FakeJournalError::Corrupt)}
        if ips.is_empty()||ips.len()>MAX_BATCH_ENTRIES{
            return Err(FakeJournalError::Limit)
        }
        let mut rows=Vec::with_capacity(ips.len());
        let mut seen=HashSet::new();
        for &ip in ips{
            if !seen.insert(ip){return Err(FakeJournalError::Conflict)}
            rows.push(pool.pending_snapshot(ip).ok_or(FakeJournalError::Pool(
                FakeError::NotDurable))?);
        }
        let frame=encode(&rows)?;
        if frame.len()>MAX_JOURNAL_BYTES.saturating_sub(self.bytes){
            return Err(FakeJournalError::Limit)
        }
        if let Err(err)=self.file.write_all(&frame){
            self.poisoned=true;
            return Err(ioe(err))
        }
        // The OS confirms this bounded batch reached the file; a failing
        // sync poisons the journal for this generation. No new FakeIP is
        // issued or silently redirected, and original cached fakes are
        // still reserved until the next validated recovery.
        if let Err(err)=self.file.sync_data(){
            self.poisoned=true;
            return Err(ioe(err))
        }
        self.bytes+=frame.len();
        for &ip in ips {
            pool.acknowledge_durable(ip).map_err(FakeJournalError::Pool)?;
        }
        Ok(())
    }
    pub fn written_bytes(&self)->usize{self.bytes}
    pub fn path(&self)->&Path{&self.path}
}
#[cfg(test)]
mod tests{
    use super::*;
    use std::sync::atomic::{AtomicU64,Ordering};
    static NONCE:AtomicU64=AtomicU64::new(1);
    fn temp_path()->PathBuf{
        std::env::temp_dir().join(format!("wbd-p029-journal-{}-{}.db",
            std::process::id(),NONCE.fetch_add(1,Ordering::Relaxed)))
    }
    fn pool()->FakeAllocator{
        FakeAllocator::new(u32::from_be_bytes([198,18,0,1]),
            u32::from_be_bytes([198,18,0,120]),&[],120,1024*1024).unwrap()
    }
    fn key(name:&str,real:u32)->FakeKey{
        FakeKey{qname:name.into(),canonical:"cdn.example".into(),
            real4:real,policy_rev:11,resolver_rev:1}
    }
    #[test]
    fn plan029_fake_journal_real_os_batch_sync_then_restore_same_cn_fakes(){
        let path=temp_path();
        let (mut journal,empty)=FakeJournal::open(&path).unwrap();
        assert!(empty.is_empty());
        let mut p=pool();
        let a=p.prepare(key("a.cn.example",0x08080808),25,1000).unwrap();
        let b=p.prepare(key("b.cn.example",0x08080404),18,1000).unwrap();
        assert!(p.announced_real(a.fake4).is_none());
        journal.persist_batch(&mut p,&[a.fake4,b.fake4]).unwrap();
        assert_eq!(p.issued_for(&key("a.cn.example",0x08080808),1001),Some(a.fake4));
        assert!(journal.written_bytes()>MAGIC.len()+8);
        let first_size=journal.written_bytes();
        let renew=p.prepare(key("a.cn.example",0x08080808),45,5000).unwrap();
        assert_eq!(renew.fake4,a.fake4);
        journal.persist_batch(&mut p,&[renew.fake4]).unwrap();
        assert!(journal.written_bytes()>first_size); // append only, not overwrite whole snapshot
        drop(journal);
        let (reopened,rows)=FakeJournal::open(&path).unwrap();
        assert_eq!(rows.len(),2);
        assert_eq!(reopened.written_bytes(),fs::metadata(&path).unwrap().len() as usize);
        let mut restored=pool();
        restored.restore(&rows,6000).unwrap();
        assert_eq!(restored.issued_for(&key("a.cn.example",0x08080808),6001),Some(a.fake4));
        assert_eq!(restored.announced_real(b.fake4),Some(0x08080404));
        drop(reopened);
        fs::remove_file(&path).unwrap();
    }
    #[test]
    fn plan029_fake_journal_corrupt_or_foreign_file_never_unblocks_fake_answer(){
        let path=temp_path();
        let (mut journal,_)=FakeJournal::open(&path).unwrap();
        let mut p=pool();
        let fake=p.prepare(key("a.cn.example",0x08080808),10,1000).unwrap();
        journal.persist_batch(&mut p,&[fake.fake4]).unwrap();
        drop(journal);
        let mut broken=fs::read(&path).unwrap();
        *broken.last_mut().unwrap()^=0x12;
        fs::write(&path,&broken).unwrap();
        assert!(matches!(FakeJournal::open(&path),Err(FakeJournalError::Corrupt)));
        let mut wrong=broken;
        wrong[0]=b'?';
        fs::write(&path,&wrong).unwrap();
        assert!(matches!(FakeJournal::open(&path),Err(FakeJournalError::ForeignFile)));
        fs::remove_file(&path).unwrap();
    }
    #[test]
    fn plan029_fake_journal_real_filesystem_commit_precedes_cn_wire_reply_and_restart(){
        use crate::v4_client_dns_answer::{DnsAResolution,DnsAnswerStatus,ResolvedA};
        use crate::v4_client_dns_wire::{synthesize_cn_a,FakeDnsWireError};
        let path=temp_path();
        let mut p=pool();
        let real=0xcb00712cu32;
        let k=FakeKey{qname:"cn.example".into(),canonical:"cdn.example".into(),
            real4:real,policy_rev:11,resolver_rev:1};
        let candidate=p.prepare(k.clone(),30,1000).unwrap();
        let resolved=DnsAResolution{status:DnsAnswerStatus::Answered,
            canonical:"cdn.example".into(),
            cname_chain:vec!["cn.example".into()],
            candidates:vec![ResolvedA{address:real,ttl:30}]};
        assert_eq!(synthesize_cn_a(77,"cn.example",&resolved,&p,11,1,1000),
            Err(FakeDnsWireError::MissingDurableMapping));
        let (mut journal,_) = FakeJournal::open(&path).unwrap();
        journal.persist_batch(&mut p,&[candidate.fake4]).unwrap();
        let wire=synthesize_cn_a(77,"cn.example",&resolved,&p,11,1,1001).unwrap();
        assert_eq!(wire.fakes,vec![candidate.fake4]);
        assert!(!wire.packet.windows(4).any(|w|w==real.to_be_bytes()));
        assert!(wire.packet.windows(4).any(|w|w==candidate.fake4.to_be_bytes()));
        drop(journal);
        let (_journal,restored)=FakeJournal::open(&path).unwrap();
        let mut cold=pool();
        cold.restore(&restored,1002).unwrap();
        assert_eq!(synthesize_cn_a(78,"cn.example",&resolved,&cold,11,1,1003)
            .unwrap().fakes,vec![candidate.fake4]);
        fs::remove_file(path).unwrap();
    }
    #[test]
    fn plan029_fake_journal_never_acks_if_batch_validation_failed(){
        let path=temp_path();
        let (mut journal,_)=FakeJournal::open(&path).unwrap();
        let mut p=pool();
        let candidate=p.prepare(key("cn.example",0x01020304),30,1000).unwrap();
        assert!(matches!(journal.persist_batch(&mut p,&[candidate.fake4,candidate.fake4]),
            Err(FakeJournalError::Conflict)));
        assert!(p.issued_for(&key("cn.example",0x01020304),1001).is_none());
        assert_eq!(journal.written_bytes(),MAGIC.len());
        drop(journal);
        fs::remove_file(path).unwrap();
    }
}
