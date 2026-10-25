//! FEC2 RS16 scheme-local codec. Operates ONLY on already-authenticated
//! record payloads. Record kind (2/3), capability, tunnel epoch, direction,
//! monotonic block id and first-delivery dedup are enforced by the caller/M0.
//! No V1 WF magic sniffing, Go V1 format, timers, threads, PN or AEAD here.
#![forbid(unsafe_code)]

use std::collections::{BTreeMap, VecDeque};

pub const SOURCE_HEADER: usize = 10;
pub const REPAIR_HEADER: usize = 12;
pub const RECORD_RESERVATION: usize = 14;
pub const MAX_K: usize = 16;
pub const MAX_R: usize = 20;
pub const MAX_SYMBOL_LEN: usize = u16::MAX as usize;
pub const MAX_ORIGINAL_LEN: usize = MAX_SYMBOL_LEN - 2;
pub const DECODE_CACHE_LIMIT: usize = 64;
pub const MAX_BATCH_ROWS: usize = 4;

// The native coefficient table depends ONLY on (k, row offset, row count),
// never on source bytes, wire length, epoch, direction, or revision.
// Immutable lazy slots avoid rebuilding the five ISA-L tables for every
// k16/r20 Maximum block. Fixed max: 1280 slots, <=777600 table payload
// bytes across all valid shapes (k>=2), no hot-path global mutex.
#[cfg(feature="native-isal")]
static SHARED_ENCODE_TABLES:
    [std::sync::OnceLock<Option<wbd_isal_safe::Tables>>;
     MAX_K*MAX_R*MAX_BATCH_ROWS] =
    [const { std::sync::OnceLock::new() }; MAX_K*MAX_R*MAX_BATCH_ROWS];

/// Record kinds are reserved; these are not wired into the public AEAD kind
/// selector or negotiated admission feature. M0 alone activates them.
pub const AUTHENTICATED_FEC2_SOURCE_KIND: u8 = 2;
pub const AUTHENTICATED_FEC2_REPAIR_KIND: u8 = 3;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    UnsupportedProfile,
    InvalidK,
    InvalidRow,
    InvalidIndex,
    InvalidLength,
    NonzeroFlags,
    BudgetExceeded,
    DuplicateParity,
    ConflictingMeta,
    TooManyMissing,
    Singular,
    CorruptProtectedLength,
    NativeUnavailable,
    NativeFailure,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BackendChoice { Scalar, PreferNative, RequireNative }
// Public/runtime policy prefers a verified compiled backend; scalar when absent.
// RequireNative remains a strict diagnostic rather than a product default.
impl Default for BackendChoice { fn default() -> Self { Self::PreferNative } }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BackendUsed { Scalar, NativeIsaL }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Profile { Light, Mild, Medium, Balanced, High, Strong, Maximum }
impl Profile {
    pub const ALL: [Profile; 7] = [
        Profile::Light, Profile::Mild, Profile::Medium, Profile::Balanced,
        Profile::High, Profile::Strong, Profile::Maximum,
    ];
    pub fn name(self) -> &'static str {
        match self {
            Self::Light => "light", Self::Mild => "mild",
            Self::Medium => "medium", Self::Balanced => "balanced",
            Self::High => "high", Self::Strong => "strong",
            Self::Maximum => "maximum",
        }
    }
    pub fn ratio(self) -> (usize, usize) {
        match self {
            Self::Light => (1,8), Self::Mild => (1,4),
            Self::Medium => (3,8), Self::Balanced => (1,2),
            Self::High => (3,4), Self::Strong => (1,1),
            Self::Maximum => (5,4),
        }
    }
    pub fn parity_count(self, k: usize) -> Result<usize, Error> {
        if !(1..=MAX_K).contains(&k) { return Err(Error::InvalidK); }
        let (n,d) = self.ratio();
        Ok(((k*n+d-1)/d).min(MAX_R))
    }
}
impl std::str::FromStr for Profile {
    type Err = Error;
    fn from_str(s: &str) -> Result<Self,Self::Err> {
        Self::ALL.into_iter().find(|p| p.name() == s)
            .ok_or(Error::UnsupportedProfile)
    }
}

/// The limit is authenticated RECORD PAYLOAD bytes, *not* outer IP MTU and
/// not the LINK/Game capacity. M0 calls path_budget once, then passes it here.
pub fn max_original_for_record_budget(record_payload_budget: usize) -> Result<usize,Error> {
    record_payload_budget.checked_sub(RECORD_RESERVATION)
        .map(|n| n.min(MAX_ORIGINAL_LEN)).ok_or(Error::BudgetExceeded)
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Source<'a> {
    pub block_id: u64,
    pub source_index: u8,
    pub frame: &'a [u8],
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Repair<'a> {
    pub block_id: u64,
    pub parity_row: u8,
    pub actual_k: u8,
    pub symbol_len: u16,
    pub body: &'a [u8],
}
pub fn source_into(block_id: u64, index: u8, frame: &[u8],
                   record_payload_budget: usize, out: &mut [u8])
                   -> Result<usize,Error> {
    if block_id == 0 || usize::from(index) >= MAX_K { return Err(Error::InvalidIndex); }
    if frame.len() > max_original_for_record_budget(record_payload_budget)? {
        return Err(Error::BudgetExceeded);
    }
    let needed = SOURCE_HEADER + frame.len();
    if needed > record_payload_budget || out.len() < needed { return Err(Error::BudgetExceeded); }
    out[..8].copy_from_slice(&block_id.to_be_bytes());
    out[8] = index;
    out[9] = 0;
    out[SOURCE_HEADER..needed].copy_from_slice(frame);
    Ok(needed)
}
pub fn source_owned(block_id: u64, index: u8, frame: &[u8],
                    budget: usize) -> Result<Vec<u8>,Error> {
    if frame.len() > max_original_for_record_budget(budget)? {
        return Err(Error::BudgetExceeded);
    }
    let mut out = vec![0; SOURCE_HEADER + frame.len()];
    let n = source_into(block_id,index,frame,budget,&mut out)?;
    out.truncate(n);
    Ok(out)
}
pub fn parse_source(data: &[u8], record_payload_budget: usize) -> Result<Source<'_>,Error> {
    if data.len() > record_payload_budget { return Err(Error::BudgetExceeded); }
    if data.len() < SOURCE_HEADER { return Err(Error::InvalidLength); }
    let block_id = u64::from_be_bytes(data[..8].try_into().map_err(|_|Error::InvalidLength)?);
    if block_id == 0 || usize::from(data[8]) >= MAX_K { return Err(Error::InvalidIndex); }
    if data[9] != 0 { return Err(Error::NonzeroFlags); }
    let frame=&data[SOURCE_HEADER..];
    if frame.len() > max_original_for_record_budget(record_payload_budget)? {
        return Err(Error::BudgetExceeded);
    }
    Ok(Source { block_id, source_index:data[8], frame })
}
pub fn parse_repair(data: &[u8], record_payload_budget: usize) -> Result<Repair<'_>,Error> {
    if data.len() > record_payload_budget { return Err(Error::BudgetExceeded); }
    if data.len() < REPAIR_HEADER { return Err(Error::InvalidLength); }
    let block_id=u64::from_be_bytes(data[..8].try_into().map_err(|_|Error::InvalidLength)?);
    if block_id==0 || usize::from(data[8])>=MAX_R { return Err(Error::InvalidRow); }
    if !(1..=MAX_K as u8).contains(&data[9]) { return Err(Error::InvalidK); }
    let len = u16::from_be_bytes([data[10],data[11]]) as usize;
    if len < 2 || len > record_payload_budget.saturating_sub(REPAIR_HEADER) ||
       data.len() != REPAIR_HEADER+len {
        return Err(Error::InvalidLength);
    }
    Ok(Repair {block_id, parity_row:data[8], actual_k:data[9],
        symbol_len:len as u16,body:&data[REPAIR_HEADER..]})
}

/// Before accepting a known systematic source into a block with authoritative
/// parity metadata, check block identity, index < actual_k and L bounds.
/// Tunnel epoch/direction are authenticated owner scope, not wire fields.
pub fn validate_source_against_repair(source:&Source<'_>,repair:&Repair<'_>)
    ->Result<(),Error> {
    if source.block_id!=repair.block_id {return Err(Error::ConflictingMeta);}
    if source.source_index>=repair.actual_k {return Err(Error::InvalidIndex);}
    if source.frame.len()+2>usize::from(repair.symbol_len) {
        return Err(Error::ConflictingMeta);
    }
    Ok(())
}

/// Local-only GF256 0x11d oracle; no Go/V1 generator normalization.
struct Gf {
    exp:[u8;512], log:[u8;256],
}
impl Gf {
    fn new()->Self {
        let mut gf=Self {exp:[0;512],log:[0;256]};
        let mut x=1u16;
        for i in 0..255 {
            gf.exp[i]=x as u8;gf.log[x as usize]=i as u8;
            x<<=1;if x&256!=0 { x^=0x11d; }
        }
        for i in 255..512 {gf.exp[i]=gf.exp[i-255];}
        gf
    }
    fn mul(&self,a:u8,b:u8)->u8 {
        if a==0 || b==0 { 0 } else {
            self.exp[usize::from(self.log[a as usize])+usize::from(self.log[b as usize])]
        }
    }
    fn div(&self,a:u8,b:u8)->u8 {
        if a==0 {0} else {
            let index=(255 + usize::from(self.log[a as usize])
                - usize::from(self.log[b as usize]))%255;
            self.exp[index]
        }
    }
    fn inverse(&self, a:&[Vec<u8>])->Result<Vec<Vec<u8>>,Error> {
        let n=a.len();
        if n==0 || n>MAX_K || a.iter().any(|r|r.len()!=n) {return Err(Error::InvalidLength);}
        let mut aug=vec![vec![0u8;2*n];n];
        for (i,row) in a.iter().enumerate() {
            aug[i][..n].copy_from_slice(row);
            aug[i][n+i]=1;
        }
        for col in 0..n {
            let pivot=(col..n).find(|&r|aug[r][col]!=0).ok_or(Error::Singular)?;
            aug.swap(col,pivot);
            let p=self.div(1,aug[col][col]);
            for x in 0..2*n { aug[col][x]=self.mul(aug[col][x],p); }
            for row in 0..n {
                if row==col {continue;}
                let factor=aug[row][col];
                if factor==0 {continue;}
                for x in 0..2*n {aug[row][x]^=self.mul(factor,aug[col][x]);}
            }
        }
        Ok(aug.into_iter().map(|r|r[n..].to_vec()).collect())
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq,Ord,PartialOrd)]
struct CacheKey {k:u8, missing:u16, selected_rows:u32}
/// A single owned mathematical copy retained for a block, independent of
/// fresh first-send/AEAD ownership. Reusable by <=4-row encoding quanta, so
/// ISA-L does NOT pad/copy k full source symbols for each quantum.
pub struct PreparedBlock {
    symbols: Vec<Vec<u8>>,
    symbol_len: usize,
    #[cfg(feature="native-isal")]
    // Immutable shared native coefficient tables indexed by bounded
    // (first_row,row_count) references. No per-block BTreeMap nodes.
    native_tables: [Option<&'static wbd_isal_safe::Tables>;MAX_R*MAX_BATCH_ROWS],
}
impl PreparedBlock {
    pub fn from_frames(frames:&[&[u8]],record_payload_budget:usize)->Result<Self,Error> {
        let len=Rs16::validate_sources(frames,record_payload_budget)?;
        let symbols=frames.iter().map(|frame|{
            let mut out=vec![0u8;len];
            out[..2].copy_from_slice(&(frame.len() as u16).to_be_bytes());
            out[2..2+frame.len()].copy_from_slice(frame);
            out
        }).collect();
        Ok(Self{symbols,symbol_len:len,
            #[cfg(feature="native-isal")]
            native_tables:[None;MAX_R*MAX_BATCH_ROWS],
        })
    }
    pub fn k(&self)->usize{self.symbols.len()}
    pub fn symbol_len(&self)->usize{self.symbol_len}
    /// Native table references used by this block; matrix allocation is
    /// independent of authenticated source symbols and bounded globally.
    pub fn cached_native_tables(&self)->usize {
        #[cfg(feature="native-isal")]
        {self.native_tables.iter().filter(|v|v.is_some()).count()}
        #[cfg(not(feature="native-isal"))]
        {0}
    }
}

/// Retained decode heap payload counts. Excludes BTree nodes, Vec headers,
/// allocator overhead, and caller-owned recovered output allocations.
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub struct DecodeCacheStats {
    pub inverses:usize,
    pub inverse_payload_bytes:usize,
    pub native_tables:usize,
    pub native_table_payload_bytes:usize,
    pub source_workspace_capacity_bytes:usize,
}
pub struct Rs16 {
    gf:Gf,
    inverses:BTreeMap<CacheKey,Vec<Vec<u8>>>,
    order:VecDeque<CacheKey>,
    #[cfg(feature="native-isal")]
    native_tables:BTreeMap<CacheKey,wbd_isal_safe::Tables>,
    #[cfg(feature="native-isal")]
    native_source_workspace:Vec<Vec<u8>>,
}
impl Default for Rs16 {fn default()->Self{Self::new()}}
impl Rs16 {
    pub fn new()->Self {
        Self {gf:Gf::new(),inverses:BTreeMap::new(),order:VecDeque::new(),
            #[cfg(feature="native-isal")]
            native_tables:BTreeMap::new(),
            #[cfg(feature="native-isal")]
            native_source_workspace:Vec::new(),
        }
    }
    pub fn cache_entries(&self)->usize {self.inverses.len()}
    /// Exact ISA-L table payload is 32 bytes per decoding coefficient.
    /// Other counts exclude allocation metadata and caller-owned outputs.
    pub fn decode_cache_stats(&self)->DecodeCacheStats {
        let inverse_payload_bytes=self.inverses.values()
            .map(|m|m.iter().map(Vec::capacity).sum::<usize>()).sum();
        #[cfg(feature="native-isal")]
        let (native_tables,native_table_payload_bytes,source_workspace_capacity_bytes)=(
            self.native_tables.len(),
            self.native_tables.keys().map(|key|
                usize::from(key.k)*key.missing.count_ones() as usize*32).sum(),
            self.native_source_workspace.iter().map(Vec::capacity).sum());
        #[cfg(not(feature="native-isal"))]
        let (native_tables,native_table_payload_bytes,source_workspace_capacity_bytes)=(0,0,0);
        DecodeCacheStats {inverses:self.inverses.len(),inverse_payload_bytes,
            native_tables,native_table_payload_bytes,source_workspace_capacity_bytes}
    }
    /// GF Cauchy row: first row XOR, remaining y_j/(x_i XOR y_j).
    /// k1 is a repetition code for ALL rows.
    pub fn coefficient(&self, row:usize, col:usize, k:usize)->Result<u8,Error> {
        if !(1..=MAX_K).contains(&k) {return Err(Error::InvalidK);}
        if row>=MAX_R {return Err(Error::InvalidRow);}
        if col>=k {return Err(Error::InvalidIndex);}
        if row==0 || k==1 {return Ok(1);}
        let y=32+col as u8;
        Ok(self.gf.div(y,(row as u8)^y))
    }
    fn validate_sources(sources:&[&[u8]],budget:usize)->Result<usize,Error> {
        if !(1..=MAX_K).contains(&sources.len()) { return Err(Error::InvalidK); }
        let limit=max_original_for_record_budget(budget)?;
        if sources.iter().any(|s|s.len()>limit) { return Err(Error::BudgetExceeded); }
        Ok(sources.iter().map(|s|s.len()).max().unwrap_or(0)+2)
    }
    fn symbol_byte(frame:&[u8], pos:usize)->u8 {
        if pos<2 {(frame.len() as u16).to_be_bytes()[pos]}
        else {frame.get(pos-2).copied().unwrap_or(0)}
    }
    fn scalar_row(&self,sources:&[&[u8]], row:usize, output:&mut [u8]) -> Result<(),Error>{
        output.fill(0);let k=sources.len();
        for (col,src) in sources.iter().enumerate() {
            let c=self.coefficient(row,col,k)?;
            for (at,d) in output.iter_mut().enumerate() {
                let b=Self::symbol_byte(src,at);
                *d^=if c==1 {b} else {self.gf.mul(c,b)};
            }
        }
        Ok(())
    }
    /// Exactly one owner polling quantum. The caller allocates final 12+L
    /// outputs, this method writes their bodies directly (no parity staging).
    /// All sources borrowed, no output aliases a source in safe Rust.
    /// Returning NativeIsaL requires an ACTUAL Tables::encode invocation.
    pub fn encode_into(&self,block_id:u64,sources:&[&[u8]],profile:Profile,
        first_row:usize,outputs:&mut [&mut [u8]],
        record_payload_budget:usize,backend:BackendChoice)
        ->Result<BackendUsed,Error> {
        let symbol_len=Self::validate_sources(sources,record_payload_budget)?;
        let total=profile.parity_count(sources.len())?;
        if block_id==0 || outputs.is_empty() || outputs.len()>MAX_BATCH_ROWS ||
           first_row>=total || outputs.len()>total-first_row {
            return Err(Error::InvalidRow);
        }
        let needed=REPAIR_HEADER+symbol_len;
        if needed>record_payload_budget || outputs.iter().any(|o|o.len()!=needed) {
            return Err(Error::BudgetExceeded);
        }
        // Reject unsupported native BEFORE mutating output.
        let run_native=backend!=BackendChoice::Scalar && symbol_len>=64 && sources.len()>1;
        if backend==BackendChoice::RequireNative {
            #[cfg(not(feature="native-isal"))]
            {return Err(Error::NativeUnavailable);}
            if !run_native {return Err(Error::NativeUnavailable);}
        }
        let mut used=BackendUsed::Scalar;
        if run_native {
            #[cfg(feature="native-isal")]
            {
                let k=sources.len();
                let mut coefs=Vec::with_capacity(k*outputs.len());
                for row in first_row..first_row+outputs.len() {
                    for col in 0..k {coefs.push(self.coefficient(row,col,k)?);}
                }
                // The 2B protected length must be part of the mathematical
                // input. Allocate one bounded, length-exact temporary per
                // source; never expose dirty arena capacity to ISA-L.
                let mut owned=vec![vec![0u8;symbol_len];k];
                for (o,src) in owned.iter_mut().zip(sources) {
                    o[..2].copy_from_slice(&(src.len() as u16).to_be_bytes());
                    o[2..2+src.len()].copy_from_slice(src);
                }
                let inputs=owned.iter().map(Vec::as_slice).collect::<Vec<_>>();
                let tables=wbd_isal_safe::Tables::new(k,outputs.len(),&coefs)
                    .map_err(|_|Error::NativeFailure)?;
                let mut dst=outputs.iter_mut().map(|o|&mut o[REPAIR_HEADER..])
                    .collect::<Vec<_>>();
                tables.encode(&inputs,&mut dst).map_err(|_|Error::NativeFailure)?;
                used=BackendUsed::NativeIsaL;
            }
        }
        if used==BackendUsed::Scalar {
            for (index,out) in outputs.iter_mut().enumerate() {
                self.scalar_row(sources,first_row+index,&mut out[REPAIR_HEADER..])?;
            }
        }
        for (index,out) in outputs.iter_mut().enumerate() {
            out[..8].copy_from_slice(&block_id.to_be_bytes());
            out[8]=(first_row+index) as u8;
            out[9]=sources.len() as u8;
            out[10..12].copy_from_slice(&(symbol_len as u16).to_be_bytes());
        }
        Ok(used)
    }
    pub fn encode_owned(&self,block_id:u64,sources:&[&[u8]],profile:Profile,
        first_row:usize,count:usize,budget:usize,backend:BackendChoice)
        ->Result<(Vec<Vec<u8>>,BackendUsed),Error> {
        let len=Self::validate_sources(sources,budget)?;
        if count==0 || count>MAX_BATCH_ROWS {return Err(Error::InvalidRow);}
        let mut rows=vec![vec![0u8;REPAIR_HEADER+len];count];
        let used={
            let mut dest=rows.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
            self.encode_into(block_id,sources,profile,first_row,&mut dest,budget,backend)?
        };
        Ok((rows,used))
    }
    /// Block-reusable encoder: consumes a PreparedBlock built once. The
    /// prepared symbol already includes original_len:u16 and zero tail.
    /// Produces exact final 12B+L repair slices. Native immutable coefficients
    /// are shared only for the validated (k, first_row, row_count) shape.
    pub fn encode_prepared_into(&self, block_id:u64,prepared:&mut PreparedBlock,
        profile:Profile,first_row:usize,outputs:&mut [&mut [u8]],
        record_payload_budget:usize,backend:BackendChoice)->Result<BackendUsed,Error> {
        let k=prepared.k();
        let len=prepared.symbol_len();
        let total=profile.parity_count(k)?;
        if block_id==0 || outputs.is_empty() || outputs.len()>MAX_BATCH_ROWS ||
            first_row>=total || outputs.len()>total-first_row {return Err(Error::InvalidRow);}
        if REPAIR_HEADER+len>record_payload_budget ||
            outputs.iter().any(|o|o.len()!=REPAIR_HEADER+len) {
            return Err(Error::BudgetExceeded);
        }
        let native_ok=backend!=BackendChoice::Scalar && len>=64 && k>1;
        if backend==BackendChoice::RequireNative {
            #[cfg(not(feature="native-isal"))]
            {return Err(Error::NativeUnavailable);}
            if !native_ok {return Err(Error::NativeUnavailable);}
        }
        let mut used=BackendUsed::Scalar;
        if native_ok {
            #[cfg(feature="native-isal")]
            {
                let shape=first_row*MAX_BATCH_ROWS+outputs.len()-1;
                if prepared.native_tables[shape].is_none() {
                    // Source bytes and FEC epoch never enter coefficient
                    // identity; the shared slot includes the verified k.
                    let slot=((k-1)*MAX_R+first_row)*MAX_BATCH_ROWS+outputs.len()-1;
                    let table=SHARED_ENCODE_TABLES[slot].get_or_init(|| {
                        let mut coeff=Vec::with_capacity(k*outputs.len());
                        for row in first_row..first_row+outputs.len() {
                            for col in 0..k {
                                let Ok(c)=self.coefficient(row,col,k) else {return None};
                                coeff.push(c);
                            }
                        }
                        wbd_isal_safe::Tables::new(k,outputs.len(),&coeff).ok()
                    }).as_ref().ok_or(Error::NativeFailure)?;
                    prepared.native_tables[shape]=Some(table);
                }
                let tables=prepared.native_tables[shape].ok_or(Error::NativeFailure)?;
                // Native k<=16, rows<=4: pass stack-backed borrowed views,
                // eliminating two short-lived per-quantum Vec allocations.
                let mut src:[&[u8];MAX_K]=[&[];MAX_K];
                for (dst,sym) in src.iter_mut().zip(prepared.symbols.iter()) {
                    *dst=sym.as_slice();
                }
                let mut e0=[];let mut e1=[];let mut e2=[];let mut e3=[];
                let mut dest:[&mut [u8];MAX_BATCH_ROWS]=[
                    &mut e0,&mut e1,&mut e2,&mut e3
                ];
                let row_count=outputs.len();
                for (dst,out) in dest.iter_mut().zip(outputs.iter_mut()) {
                    *dst=&mut out[REPAIR_HEADER..];
                }
                tables.encode(&src[..k],&mut dest[..row_count])
                    .map_err(|_|Error::NativeFailure)?;
                used=BackendUsed::NativeIsaL;
            }
        }
        if used==BackendUsed::Scalar {
            for (i,o) in outputs.iter_mut().enumerate() {
                let dst=&mut o[REPAIR_HEADER..];
                dst.fill(0);
                for (col,src) in prepared.symbols.iter().enumerate() {
                    let c=self.coefficient(first_row+i,col,k)?;
                    for (b,&x) in dst.iter_mut().zip(src.iter()) {
                        *b^=if c==1{x}else{self.gf.mul(c,x)};
                    }
                }
            }
        }
        for (i,o) in outputs.iter_mut().enumerate() {
            o[..8].copy_from_slice(&block_id.to_be_bytes());
            o[8]=(first_row+i) as u8;
            o[9]=k as u8;
            o[10..12].copy_from_slice(&(len as u16).to_be_bytes());
        }
        Ok(used)
    }

    /// Cache hit returns a key, not a cloned e-by-e inverse.
    fn ensure_inverse_cached(&mut self,k:usize,missing:&[usize],selected:&[Repair<'_>])
        ->Result<CacheKey,Error> {
        let mask=missing.iter().fold(0u16,|m,&col|m|(1u16<<col));
        let rows=selected.iter().fold(0u32,|m,r|m|(1u32<<r.parity_row));
        let key=CacheKey {k:k as u8,missing:mask,selected_rows:rows};
        if self.inverses.contains_key(&key) {return Ok(key);}
        let mut matrix=Vec::with_capacity(missing.len());
        for repair in selected {
            let mut line=Vec::with_capacity(missing.len());
            for &col in missing {
                line.push(self.coefficient(repair.parity_row as usize,col,k)?);
            }
            matrix.push(line);
        }
        let inverse=self.gf.inverse(&matrix)?;
        if self.order.len()==DECODE_CACHE_LIMIT {
            if let Some(old)=self.order.pop_front() {
                self.inverses.remove(&old);
                #[cfg(feature="native-isal")]
                self.native_tables.remove(&old);
            }
        }
        self.order.push_back(key);
        self.inverses.insert(key,inverse);
        Ok(key)
    }
    /// Recover only e missing originals. Sources may be absent, but all
    /// surviving original frames are authenticated, never mathematical symbols.
    /// Parity is authenticated by the caller and strictly parsed using
    /// parse_repair. Caller retains epoch/direction/late/Stop and dedup.
    /// No output is deliverable until protected original_len and zero tail
    /// are validated. No len-array exists on V2 wire.
    pub fn recover_missing(&mut self,block_id:u64,
        sources:&[Option<&[u8]>],repairs:&[Repair<'_>],
        record_payload_budget:usize,backend:BackendChoice)
        ->Result<(Vec<(u8,Vec<u8>)>,BackendUsed),Error> {
        if block_id==0 || !(1..=MAX_K).contains(&sources.len()){return Err(Error::InvalidK);}
        let k=sources.len();
        let mut sorted=repairs.to_vec();sorted.sort_by_key(|r|r.parity_row);
        let mut len=None;
        for (i,r) in sorted.iter().enumerate() {
            if r.block_id!=block_id || r.actual_k as usize!=k {
                return Err(Error::ConflictingMeta);
            }
            if r.parity_row as usize>=MAX_R {return Err(Error::InvalidRow);}
            if i>0 && sorted[i-1].parity_row==r.parity_row {return Err(Error::DuplicateParity);}
            if r.body.len()!=r.symbol_len as usize || r.symbol_len<2 ||
               REPAIR_HEADER+r.body.len()>record_payload_budget {
                return Err(Error::InvalidLength);
            }
            if len.is_some_and(|l|l!=r.body.len()) {return Err(Error::ConflictingMeta);}
            len=Some(r.body.len());
        }
        let missing=(0..k).filter(|&i|sources[i].is_none()).collect::<Vec<_>>();
        if missing.is_empty() {return Ok((Vec::new(),BackendUsed::Scalar));}
        let e=missing.len();
        if sorted.len()<e {return Err(Error::TooManyMissing);}
        let symbol_len=len.ok_or(Error::TooManyMissing)?;
        if sources.iter().flatten().any(|s|s.len()>symbol_len-2 ||
            s.len()>MAX_ORIGINAL_LEN) {return Err(Error::ConflictingMeta);}
        let chosen=&sorted[..e];
        let key=self.ensure_inverse_cached(k,&missing,chosen)?;
        let known=(0..k).filter_map(|j|sources[j].map(|s|(j,s))).collect::<Vec<_>>();
        let mut recovered=vec![vec![0u8;symbol_len];e];
        let run_native=backend!=BackendChoice::Scalar && symbol_len>=64 && k>1;
        if backend==BackendChoice::RequireNative {
            #[cfg(not(feature="native-isal"))]
            {return Err(Error::NativeUnavailable);}
            if !run_native {return Err(Error::NativeUnavailable);}
        }
        let mut used=BackendUsed::Scalar;
        if run_native {
            #[cfg(feature="native-isal")]
            {
                // Sorted repairs and increasing source indices make the
                // entire final e-by-k decoding table stable per cache key.
                if !self.native_tables.contains_key(&key) {
                    let inverse=self.inverses.get(&key).ok_or(Error::Singular)?;
                    let mut coeff=Vec::with_capacity(e*k);
                    for out in 0..e {
                        coeff.extend_from_slice(&inverse[out]);
                        for &(col,_) in &known {
                            let mut c=0u8;
                            for (i,r) in chosen.iter().enumerate() {
                                c^=self.gf.mul(inverse[out][i],
                                    self.coefficient(r.parity_row as usize,col,k)?);
                            }
                            coeff.push(c);
                        }
                    }
                    let tables=wbd_isal_safe::Tables::new(k,e,&coeff)
                        .map_err(|_|Error::NativeFailure)?;
                    self.native_tables.insert(key,tables);
                }
                // Private owned padding reused across authenticated blocks.
                // No source borrow survives this synchronous call.
                if self.native_source_workspace.len()<known.len() {
                    self.native_source_workspace.resize_with(known.len(),Vec::new);
                }
                for (space, &(_,frame)) in self.native_source_workspace.iter_mut().zip(&known) {
                    if space.capacity()<symbol_len {
                        *space=vec![0u8;symbol_len];
                    } else {
                        space.resize(symbol_len,0);
                        space.fill(0);
                    }
                    space[..2].copy_from_slice(&(frame.len() as u16).to_be_bytes());
                    space[2..2+frame.len()].copy_from_slice(frame);
                }
                let mut inputs=chosen.iter().map(|r|r.body).collect::<Vec<_>>();
                inputs.extend(self.native_source_workspace[..known.len()]
                    .iter().map(Vec::as_slice));
                let tables=self.native_tables.get(&key).ok_or(Error::NativeFailure)?;
                let mut dst=recovered.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
                tables.encode(&inputs,&mut dst).map_err(|_|Error::NativeFailure)?;
                used=BackendUsed::NativeIsaL;
            }
        }
        if used==BackendUsed::Scalar {
            let inverse=self.inverses.get(&key).ok_or(Error::Singular)?;
            for (out,row) in recovered.iter_mut().enumerate() {
                for (p,r) in chosen.iter().enumerate() {
                    let c=inverse[out][p];
                    for (j,d) in row.iter_mut().enumerate(){
                        *d^=if c==1 {r.body[j]} else {self.gf.mul(c,r.body[j])};
                    }
                }
                for &(col,frame) in &known {
                    let mut c=0u8;
                    for (p,r) in chosen.iter().enumerate() {
                        c^=self.gf.mul(inverse[out][p],
                            self.coefficient(r.parity_row as usize,col,k)?);
                    }
                    for (j,d) in row.iter_mut().enumerate() {
                        let b=Self::symbol_byte(frame,j);
                        *d^=if c==1 {b} else {self.gf.mul(c,b)};
                    }
                }
            }
        }
        let mut outputs=Vec::with_capacity(e);
        for (&index,mut bytes) in missing.iter().zip(recovered) {
            let n=u16::from_be_bytes([bytes[0],bytes[1]]) as usize;
            if n>symbol_len-2 || bytes[2+n..].iter().any(|&b|b!=0) {
                return Err(Error::CorruptProtectedLength);
            }
            // Return the SAME owned result allocation, shifting only the 2B
            // protected prefix. Do not allocate/copy a second full frame.
            bytes.copy_within(2..2+n,0);
            bytes.truncate(n);
            outputs.push((index as u8,bytes));
        }
        Ok((outputs,used))
    }
}

// Compile the source-locked FEC2 oracle suite as real library tests. Keeping
// this declaration in the owned codec module ensures CI cannot silently
// filter out the companion tests even when a shared harness overlays the two
// files from one immutable worker SOURCE.
#[cfg(test)]
#[path = "fec_v2_tests.rs"]
mod fec_v2_tests;
