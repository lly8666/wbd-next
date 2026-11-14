//! PLAN029 portable FakeIP journal: ONLY the single owning cold/sparse
//! DNS worker appends bounded batches and gets a real filesystem sync
//! before acknowledging any client-visible synthetic IPv4 answer.
//! No per-packet persistence, background writer thread, system registry,
//! Go FFI packet pump or DNS/network fallback. An incomplete/corrupt file
//! stops NEW FakeIP issuance rather than silently reusing a stale address.
//! The host passes its owned portable application-directory absolute path.
use std::collections::{HashMap,HashSet};
use std::sync::mpsc::{sync_channel,channel,SyncSender,Receiver,TrySendError,TryRecvError};
use std::thread::{self,JoinHandle};
use std::fs::{self,File,OpenOptions};
use std::io::{self,Read,Write};
use std::path::{Path,PathBuf};
use crate::v4_client_fake_pool::{FakeAllocator,FakeSnapshotEntry,FakeKey,FakeError};

const MAGIC:&[u8;8]=b"WBD029F1";
const MAX_JOURNAL_BYTES:usize=16*1024*1024;
const MAX_BATCH_BYTES:usize=256*1024;
const MAX_BATCH_ENTRIES:usize=128;
// One per-owner durable writer, not per-flow threads. Bounded input queue;
// acknowledgements remain owned by the original Rust TX generation.
const ASYNC_QUEUE_JOBS:usize=8;
const ASYNC_QUEUE_BYTES:usize=512*1024;
// Compact before the 16-MiB history cap is reached, once per coarse
// scheduler epoch only. This is NOT an allocation/queue latency target.
const COMPACT_TRIGGER_BYTES:usize=12*1024*1024;
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
// Keep image encoding/CRC round-trip OFF the shared Wintun/Tunnel TX turn.
 // The TX owner only takes a low-frequency bounded live mapping snapshot;
 // the ONE existing disk worker builds/verifies/atomically replaces the WAL.
enum JournalTask {
    Append(u64,Vec<u8>),
    Compact(u64,Vec<FakeSnapshotEntry>),
}
struct AsyncWrite{
    // Completion reports actual synced bytes for either exact task type.
    tx:Option<SyncSender<JournalTask>>,
    rx:Receiver<(u64,bool,usize,bool)>,
    thread:Option<JoinHandle<()>>,
    pending:HashMap<u64,(Vec<FakeSnapshotEntry>,usize)>,
    results:HashMap<u64,bool>,
    queued_bytes:usize,
    next_id:u64,
    next_compact_ms:u64,
}
// Generate a COMPLETE compact image only on a low-frequency high-water
// event. It includes every still-live or quarantined durable mapping,
// regardless of its current DNS cache presence. An uncertain unissued
// mapping remains unannounced and is not allowed to become visible here.
// Called only on coarse high-water tick; copy the protected identities,
 // but DO NOT encode the multi-MiB journal or replay/check CRC on TX.
fn compact_rows(pool:&FakeAllocator)->Result<Vec<FakeSnapshotEntry>,FakeJournalError>{
    let rows=pool.durable_candidate();
    // Unacknowledged renewal must never erase the older durable identity.
    if rows.iter().any(|row|pool.pending_snapshot(row.fake4).is_some()){
        return Err(FakeJournalError::Limit)
    }
    Ok(rows)
}
fn compact_image_from_rows(rows:&[FakeSnapshotEntry])->Result<Vec<u8>,FakeJournalError>{
    let mut image=MAGIC.to_vec();
    for group in rows.chunks(MAX_BATCH_ENTRIES){
        let batch=encode(group)?;
        if batch.len()>MAX_JOURNAL_BYTES.saturating_sub(image.len()){
            return Err(FakeJournalError::Limit)
        }
        image.extend_from_slice(&batch);
    }
    let verified=load_journal(&image)?;
    if verified!=rows{return Err(FakeJournalError::Conflict)}
    Ok(image)
}
// The writer alone replaces the known owned journal. create_new never
// follows/reuses a foreign temp path. The original WAL is not removed
// until a complete verified image has been flushed and synced.
// A crash before rename leaves the old journal recoverable; afterwards
// the new one is already a valid self-contained owned snapshot.
fn compact_on_writer(path:&Path,file:&mut Option<File>,
    image:&[u8],id:u64)->io::Result<()>{
    if load_journal(image).is_err(){
        return Err(io::Error::new(io::ErrorKind::InvalidData,
            "invalid FakeIP compact image"))
    }
    let name=path.file_name().and_then(|n|n.to_str())
        .ok_or_else(||io::Error::new(io::ErrorKind::InvalidInput,
            "non-utf8 journal name"))?;
    let nonce=std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|x|x.as_nanos()).unwrap_or(0);
    let temp=path.with_file_name(format!(
        "{name}.wbd029-compact-{}-{id}-{nonce}",std::process::id()));
    let mut staged=OpenOptions::new().write(true).create_new(true).open(&temp)?;
    let attempt=(||->io::Result<()>{
        staged.write_all(image)?;
        staged.sync_all()?;
        drop(staged);
        // Windows replacement can require releasing the source handle.
        // On failed rename the original owned path stays intact.
        file.take();
        fs::rename(&temp,path)?;
        *file=Some(OpenOptions::new().append(true).open(path)?);
        Ok(())
    })();
    if attempt.is_err(){
        // This exact temp filename was create_new'd by our writer above;
        // do not enumerate or delete third-party/legacy files.
        let _=fs::remove_file(&temp);
        if file.is_none(){*file=OpenOptions::new().append(true).open(path).ok();}
    }
    attempt
}
pub(crate) struct FakeJournal{
    path:PathBuf,
    // Once async starts the owned file is moved to the ONE writer. The
    // original TX never calls write_all/sync_data on that path again.
    file:Option<File>,
    async_writer:Option<AsyncWrite>,
    bytes:usize,
    poisoned:bool,
}
impl Drop for FakeJournal{
    fn drop(&mut self){
        if let Some(writer)=self.async_writer.as_mut(){
            writer.tx.take();
            if let Some(handle)=writer.thread.take(){let _=handle.join();}
        }
    }
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
        Ok((Self{path:path.to_path_buf(),file:Some(file),async_writer:None,
            bytes:bytes.len(),poisoned:false},rows))
    }
    /// Production installs a single bounded blocking writer at cold
    /// startup, including when a valid old WAL is close to its 16-MiB cap.
    /// Pure journal tests retain open() + persist_batch() synchronous API.
    pub fn open_async(path:&Path)->Result<(Self,Vec<FakeSnapshotEntry>),FakeJournalError>{
        let (mut journal,rows)=Self::open(path)?;
        journal.ensure_async_writer()?;
        Ok((journal,rows))
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
        // The legacy synchronous helper remains for pure journal tests.
        // Production DNS always uses enqueue_batch + poll_completed below.
        // It must never race an already-owned async file handle.
        let file=self.file.as_mut().ok_or(FakeJournalError::Limit)?;
        if let Err(err)=file.write_all(&frame){
            self.poisoned=true;
            return Err(ioe(err))
        }
        // The OS confirms this bounded batch reached the file; a failing
        // sync poisons the journal for this generation. No new FakeIP is
        // issued or silently redirected, and original cached fakes are
        // still reserved until the next validated recovery.
        if let Err(err)=file.sync_data(){
            self.poisoned=true;
            return Err(ioe(err))
        }
        self.bytes+=frame.len();
        for &ip in ips {
            pool.acknowledge_durable(ip).map_err(FakeJournalError::Pool)?;
        }
        Ok(())
    }
    // One blocking writer thread per *cold DNS owner*, not per query/flow.
    // Startup code may use this for an old journal already near 16MiB.
    fn ensure_async_writer(&mut self)->Result<(),FakeJournalError>{
        if self.async_writer.is_none(){
            let path=self.path.clone();
            let file=self.file.take().ok_or(FakeJournalError::Corrupt)?;
            let (tx,requests)=sync_channel::<JournalTask>(ASYNC_QUEUE_JOBS);
            // Unbounded *completion* channel contains at most the eight
            // outstanding bounded input jobs; avoids deadlock at Stop.
            let (done_tx,rx)=channel::<(u64,bool,usize,bool)>();
            let thread=thread::Builder::new()
                .name("wbd-fakeip-journal".to_string())
                .spawn(move||{
                    let mut file=Some(file);
                    let mut failed=false;
                    while let Ok(task)=requests.recv(){
                        let (id,ok,written,compact)=match task{
                            JournalTask::Append(id,bytes)=>{
                                let ok=!failed && file.as_mut().is_some_and(|f|
                                    f.write_all(&bytes).and_then(|_|f.sync_data()).is_ok());
                                (id,ok,bytes.len(),false)
                            },
                            JournalTask::Compact(id,rows)=>{
                                // Snapshot bytes, CRC verification and slow filesystem
                                // writes are all on this ONE bounded worker, never TX.
                                let image=compact_image_from_rows(&rows);
                                let written=image.as_ref().map_or(0,|b|b.len());
                                let ok=!failed && image.as_ref().is_ok_and(|bytes|
                                    compact_on_writer(&path,&mut file,bytes,id).is_ok());
                                (id,ok,written,true)
                            },
                        };
                        // Failed compaction keeps the previous exact WAL;
                        // append IO failure poisons this generation.
                        if !ok&&!compact{failed=true}
                        if file.is_none(){failed=true}
                        if done_tx.send((id,ok,written,compact)).is_err(){break}
                    }
                }).map_err(ioe)?;
            self.async_writer=Some(AsyncWrite{
                tx:Some(tx),rx,thread:Some(thread),
                pending:HashMap::new(),results:HashMap::new(),
                queued_bytes:0,next_id:1,next_compact_ms:0,
            });
        }
        Ok(())
    }
    /// Nonblocking cold DNS submission. Only the originating DNS reply
    /// waits on its own exact ticket. All filesystem IO runs on ONE
    /// bounded per-generation worker, never the shared TX forwarding turn.
    pub fn enqueue_batch(&mut self,pool:&FakeAllocator,ips:&[u32])
        ->Result<u64,FakeJournalError>{
        if self.poisoned{return Err(FakeJournalError::Corrupt)}
        if ips.is_empty()||ips.len()>MAX_BATCH_ENTRIES{return Err(FakeJournalError::Limit)}
        let mut seen=HashSet::new();
        let mut rows=Vec::with_capacity(ips.len());
        for &ip in ips{
            if !seen.insert(ip){return Err(FakeJournalError::Conflict)}
            rows.push(pool.pending_snapshot(ip).ok_or(FakeJournalError::Pool(
                FakeError::NotDurable))?);
        }
        let frame=encode(&rows)?;
        let queued=self.async_writer.as_ref().map_or(0,|w|w.queued_bytes);
        if frame.len()>MAX_JOURNAL_BYTES.saturating_sub(self.bytes.saturating_add(queued))||
            frame.len()>ASYNC_QUEUE_BYTES.saturating_sub(queued){
            return Err(FakeJournalError::Limit)
        }
        self.ensure_async_writer()?;
        let w=self.async_writer.as_mut().ok_or(FakeJournalError::Corrupt)?;
        if w.pending.len()>=ASYNC_QUEUE_JOBS{return Err(FakeJournalError::Limit)}
        let id=w.next_id;
        w.next_id=w.next_id.checked_add(1).ok_or(FakeJournalError::Limit)?;
        let frame_len=frame.len();
        match w.tx.as_ref().ok_or(FakeJournalError::Corrupt)?.try_send(JournalTask::Append(id,frame)){
            Ok(())=>{
                w.queued_bytes+=frame_len;
                w.pending.insert(id,(rows,frame_len));
                Ok(id)
            },
            Err(TrySendError::Full(_))=>Err(FakeJournalError::Limit),
            Err(TrySendError::Disconnected(_))=>{
                self.poisoned=true;Err(FakeJournalError::Corrupt)
            },
        }
    }
    /// Poll at most a few completed IO jobs on the owned TX turn; checks
    /// the *same* pending mapping identity before durable ACK. No answer
    /// may contain an unacknowledged FakeIP, even on crash/late worker IO.
    pub fn poll_completed(&mut self,pool:&mut FakeAllocator,limit:usize){
        let Some(w)=self.async_writer.as_mut()else{return};
        for _ in 0..limit{
            let (id,ok,written,compacted)=match w.rx.try_recv(){
                Ok(x)=>x,
                Err(TryRecvError::Empty)=>break,
                Err(TryRecvError::Disconnected)=>{
                    self.poisoned=true;break
                },
            };
            let Some((rows,n))=w.pending.remove(&id)else{
                self.poisoned=true;break
            };
            if compacted{
                if !rows.is_empty()||n!=0{self.poisoned=true;break}
                // The same worker serializes future appends AFTER the
                // compact rename, so their later receipts add to this
                // new exact file size rather than the old history bytes.
                if ok{self.bytes=written}
                continue
            }
            w.queued_bytes=w.queued_bytes.saturating_sub(n);
            let valid=ok && rows.iter().all(|row|
                pool.pending_snapshot(row.fake4).as_ref()==Some(row));
            if ok{self.bytes=self.bytes.saturating_add(n)}
            if !ok{self.poisoned=true}
            if valid{
                for row in &rows{
                    if pool.acknowledge_durable(row.fake4).is_err(){
                        self.poisoned=true;break
                    }
                }
            }
            // DNS tickets are kept separately; an IO failure is local
            // SERVFAIL, not an alternate physical/tunnel resolver.
            w.results.insert(id,valid&&!self.poisoned);
            // A timed-out DNS waiter may never consume its completion.
            // Bound old statuses; current outstanding jobs are only <=8.
            if w.results.len()>1024{
                if let Some(old)=w.results.keys().copied().min(){
                    w.results.remove(&old);
                }
            }
        }
    }
    // Called only on an existing coarse 1-second owner tick. A full pool
    // snapshot is NOT scanned on normal DATA/DNS reads or every 10ms.
    // Background worker alone writes and atomically replaces this WAL.
    pub fn maybe_compact(&mut self,pool:&FakeAllocator,now_ms:u64){
        self.maybe_compact_after(pool,now_ms,COMPACT_TRIGGER_BYTES)
    }
    fn maybe_compact_after(&mut self,pool:&FakeAllocator,now_ms:u64,
        trigger:usize){
        if self.poisoned||self.bytes<trigger{return}
        let Some(w)=self.async_writer.as_mut()else{return};
        if !w.pending.is_empty()||now_ms<w.next_compact_ms{return}
        w.next_compact_ms=now_ms.saturating_add(60_000);
        let Ok(rows)=compact_rows(pool)else{return};
        let id=w.next_id;
        let Some(next)=id.checked_add(1)else{return};
        if w.tx.as_ref().is_some_and(|tx|
            tx.try_send(JournalTask::Compact(id,rows)).is_ok()){
            w.next_id=next;
            w.pending.insert(id,(Vec::new(),0));
        }
    }
    pub fn take_async_status(&mut self,id:u64)->Option<bool>{
        self.async_writer.as_mut()?.results.remove(&id)
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
    fn async_dns_file_sync_requires_receipt_before_fakeip_announcement(){
        let path=temp_path();
        let (mut journal,_) =FakeJournal::open_async(&path).unwrap();
        // Pool hard cap must fit the explicitly tiny nine-address
        // synthetic range. A 100-entry cap with nine slots is invalid.
        let mut pool=FakeAllocator::new(u32::from_be_bytes([198,18,0,1]),
            u32::from_be_bytes([198,18,0,9]),&[],9,1024*1024).unwrap();
        let candidate=pool.prepare(FakeKey{
            qname:"cn.example".into(),canonical:"cn.example".into(),
            real4:u32::from_be_bytes([198,51,100,1]),
            policy_rev:1,resolver_rev:1,
        },60,10).unwrap();
        let ticket=journal.enqueue_batch(&pool,&[candidate.fake4]).unwrap();
        assert!(pool.announced_real(candidate.fake4).is_none());
        let mut success=false;
        for _ in 0..1000{
            journal.poll_completed(&mut pool,4);
            if let Some(done)=journal.take_async_status(ticket){
                assert!(done);success=true;break
            }
            std::thread::sleep(std::time::Duration::from_millis(1));
        }
        assert!(success,"bounded test writer did not complete");
        assert_eq!(pool.announced_real(candidate.fake4),
            Some(u32::from_be_bytes([198,51,100,1])));
        drop(journal);
        let (reopened,rows)=FakeJournal::open(&path).unwrap();
        assert_eq!(rows.len(),1);
        drop(reopened);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn async_compact_keeps_quarantine_and_only_latest_mapping(){
        let path=temp_path();
        let (mut j,_) =FakeJournal::open_async(&path).unwrap();
        let mut p=pool();
        let key=key("compact.cn.example",0x08080404);
        let first=p.prepare(key.clone(),20,1000).unwrap();
        for (ttl,now) in [(20,1000),(30,3000),(40,5000)]{
            if now!=1000{p.prepare(key.clone(),ttl,now).unwrap();}
            let id=j.enqueue_batch(&p,&[first.fake4]).unwrap();
            let mut ack=false;
            for _ in 0..1000{
                j.poll_completed(&mut p,8);
                if let Some(result)=j.take_async_status(id){
                    assert!(result);ack=true;break
                }
                std::thread::sleep(std::time::Duration::from_millis(1));
            }
            assert!(ack);
        }
        let prior=j.written_bytes();
        j.maybe_compact_after(&p,6000,1); // test-only tiny trigger
        let mut shrunk=false;
        for _ in 0..1000{
            j.poll_completed(&mut p,8);
            if j.written_bytes()<prior{shrunk=true;break}
            std::thread::sleep(std::time::Duration::from_millis(1));
        }
        assert!(shrunk,"exact owned WAL compact did not finish");
        drop(j);
        let (reopen,rows)=FakeJournal::open(&path).unwrap();
        assert_eq!(rows.len(),1);
        assert_eq!(rows[0].fake4,first.fake4);
        assert!(rows[0].quarantine_until_ms>=rows[0].issued_until_ms+600_000);
        let mut restored=pool();
        restored.restore(&rows,7000).unwrap();
        assert_eq!(restored.announced_real(first.fake4),Some(0x08080404));
        drop(reopen);
        fs::remove_file(&path).unwrap();
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
