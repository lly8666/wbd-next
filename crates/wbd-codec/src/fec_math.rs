//! Genuine pinned-Go GF(256) Reed-Solomon 20:R, scalar reference backend.
//! GF primitive polynomial 0x11d; G = V(1..40) * inverse(V(1..20)).
//! Partial parity reads only active source columns. Missing-only e x e inverse
//! builds direct output coefficients; no twenty-row parity reconstruction.
//! Not SIMD, not a timed FEC owner, not a product FEC-on pipeline.
#![forbid(unsafe_code)]

use crate::link_fec_wire::{FEC_DATA_SHARDS, FEC_HEADER, FEC_PARITY_PROFILES, FecHeader};
const TOTAL_ROWS: usize = 40;
const MAX_SOURCE_SIZE: usize = 65535;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FecMathError {
    UnsupportedProfile,
    InvalidSource,
    InvalidLength,
    InvalidIndex,
    DuplicateParity,
    TooManyMissing,
    SingularMatrix,
    NoCapacity,
}

struct Gf256 {
    exp: [u8; 512],
    log: [u8; 256],
}
impl Gf256 {
    fn new() -> Self {
        let mut out = Self { exp:[0;512], log:[0;256] };
        let mut x=1u16;
        for i in 0..255 {
            out.exp[i]=x as u8;
            out.log[x as usize]=i as u8;
            x <<= 1;
            if x & 0x100 != 0 {x ^= 0x11d;}
        }
        for i in 255..512 {out.exp[i]=out.exp[i-255];}
        out
    }
    fn mul(&self,a:u8,b:u8)->u8 {
        if a==0 || b==0 {0} else {self.exp[usize::from(self.log[a as usize])+usize::from(self.log[b as usize])]}
    }
    fn inv(&self,a:u8)->Option<u8> {
        if a==0{None}else{Some(self.exp[255-usize::from(self.log[a as usize])])}
    }
    fn pow(&self,a:u8,n:usize)->u8 {
        if n==0 {1} else if a==0 {0} else {self.exp[(usize::from(self.log[a as usize])*n)%255]}
    }
    fn invert(&self, input:&[Vec<u8>])->Result<Vec<Vec<u8>>,FecMathError>{
        let n=input.len();
        if n==0 || n>FEC_DATA_SHARDS || input.iter().any(|r|r.len()!=n) {
            return Err(FecMathError::InvalidLength);
        }
        let mut aug=vec![vec![0u8;2*n];n];
        for (row,values) in input.iter().enumerate(){
            aug[row][..n].copy_from_slice(values);
            aug[row][n+row]=1;
        }
        for col in 0..n {
            let Some(pivot)=(col..n).find(|&r|aug[r][col]!=0) else{
                return Err(FecMathError::SingularMatrix);
            };
            aug.swap(pivot,col);
            let inv=self.inv(aug[col][col]).ok_or(FecMathError::SingularMatrix)?;
            for c in 0..2*n {aug[col][c]=self.mul(aug[col][c],inv);}
            for row in 0..n {
                if row==col || aug[row][col]==0{continue;}
                let factor=aug[row][col];
                for c in 0..2*n {
                    aug[row][c]^=self.mul(factor,aug[col][c]);
                }
            }
        }
        Ok(aug.iter().map(|row|row[n..].to_vec()).collect())
    }
}

pub struct ReedSolomon20 {
    gf: Gf256,
    generator: [[u8;FEC_DATA_SHARDS];TOTAL_ROWS],
}

impl ReedSolomon20 {
    pub fn new()->Result<Self,FecMathError> {
        let gf=Gf256::new();
        let mut v=[[0u8;FEC_DATA_SHARDS];TOTAL_ROWS];
        for (row,values) in v.iter_mut().enumerate(){
            for (col,coefficient) in values.iter_mut().enumerate(){
                *coefficient=gf.pow((row+1) as u8,col);
            }
        }
        let top=v[..FEC_DATA_SHARDS].iter().map(|r|r.to_vec()).collect::<Vec<_>>();
        let inverse=gf.invert(&top)?;
        let mut generator=[[0u8;FEC_DATA_SHARDS];TOTAL_ROWS];
        for (i,row) in generator.iter_mut().enumerate(){
            for (j,out) in row.iter_mut().enumerate(){
                for (p,inverse_row) in inverse.iter().enumerate(){
                    *out ^= gf.mul(v[i][p],inverse_row[j]);
                }
            }
        }
        Ok(Self {gf,generator})
    }

    pub fn generator_row(&self,index:usize)->Option<&[u8;FEC_DATA_SHARDS]> {
        self.generator.get(index)
    }

    fn profile(profile:u8)->Result<usize,FecMathError>{
        if !FEC_PARITY_PROFILES.contains(&profile){
            Err(FecMathError::UnsupportedProfile)
        }else{Ok(usize::from(profile))}
    }
    fn validate_sources<'a>(&self,sources:&[&'a [u8]])->Result<usize,FecMathError>{
        if sources.is_empty()||sources.len()>FEC_DATA_SHARDS ||
            sources.iter().any(|s|s.is_empty()||s.len()>MAX_SOURCE_SIZE) {
            return Err(FecMathError::InvalidSource);
        }
        Ok(sources.iter().map(|s|s.len()).max().unwrap_or(0))
    }

    /// Encode only requested absolute parity-row offsets [first,first+rows).
    /// This is genuine GF256 work, NOT slicing an already-computed 20-row
    /// buffer. An outer owner may return to its scheduler between <=4 rows.
    /// No source may be aliased by an output. Inactive 20-k columns are not read.
    pub fn encode_rows_active(&self,sources:&[&[u8]],profile:u8,
        first:usize,rows:usize)->Result<Vec<Vec<u8>>,FecMathError>{
        let profile=Self::profile(profile)?;
        let len=self.validate_sources(sources)?;
        let sent=sources.len().min(profile);
        if rows==0||first>=sent||rows>sent-first{
            return Err(FecMathError::InvalidIndex);
        }
        let mut parity=vec![vec![0u8;len];rows];
        for (p,dst) in parity.iter_mut().enumerate(){
            let row=&self.generator[FEC_DATA_SHARDS+first+p];
            for (i,src) in sources.iter().enumerate(){
                let coef=row[i];
                if coef==0 {continue;}
                for (j,b) in src.iter().enumerate(){
                    dst[j]^=self.gf.mul(coef,*b);
                }
            }
        }
        Ok(parity)
    }

    /// Real parity, length L=max active source length. Go sends
    /// min(k,configured_r) rows even for partial blocks.
    pub fn encode_active(&self,sources:&[&[u8]],profile:u8)
        ->Result<Vec<Vec<u8>>,FecMathError>{
        let r=Self::profile(profile)?;
        self.encode_rows_active(sources,profile,0,sources.len().min(r))
    }

    /// Reproduce pinned Go immediate systematic wire: provisional count=20,
    /// flags=1, only own original length authoritative, exactly len body.
    pub fn streaming_wire(
        &self,block_id:u32,index:usize,source:&[u8],profile:u8,wire_limit:usize
    )->Result<Vec<u8>,FecMathError>{
        Self::profile(profile)?;
        if index>=FEC_DATA_SHARDS||source.is_empty()||source.len()>MAX_SOURCE_SIZE{
            return Err(FecMathError::InvalidSource);
        }
        if FEC_HEADER+source.len()>wire_limit{return Err(FecMathError::InvalidLength);}
        let mut wire=vec![0u8;FEC_HEADER+source.len()];
        wire[..4].copy_from_slice(&[b'W',b'F',1,0]);
        wire[4..8].copy_from_slice(&block_id.to_be_bytes());
        wire[8]=index as u8;wire[9]=FEC_DATA_SHARDS as u8;
        wire[10]=profile;wire[11]=FEC_DATA_SHARDS as u8;
        wire[12..14].copy_from_slice(&(source.len() as u16).to_be_bytes());
        wire[14..16].copy_from_slice(&1u16.to_be_bytes());
        wire[16+index*2..18+index*2]
            .copy_from_slice(&(source.len() as u16).to_be_bytes());
        wire[FEC_HEADER..].copy_from_slice(source);
        Ok(wire)
    }

    /// Produces final parity wire for just the selected rows, using genuine
    /// scalar GF multiplication on the owned source slices. This is useful to
    /// build a codec-level cooperative first-send job without ever materializing
    /// all twenty rows in one call. All rows retain the CONFIGURED profile R.
    pub fn final_parity_wires_range(&self,block_id:u32,sources:&[&[u8]],
        profile:u8,wire_limit:usize,first:usize,rows:usize)
        ->Result<Vec<Vec<u8>>,FecMathError>{
        let parity=self.encode_rows_active(sources,profile,first,rows)?;
        let len=sources.iter().map(|s|s.len()).max().unwrap_or(0);
        if FEC_HEADER+len>wire_limit{return Err(FecMathError::InvalidLength);}
        let mut result=Vec::with_capacity(parity.len());
        for (p,body) in parity.into_iter().enumerate(){
            let mut frame=vec![0u8;FEC_HEADER+len];
            frame[..4].copy_from_slice(&[b'W',b'F',1,0]);
            frame[4..8].copy_from_slice(&block_id.to_be_bytes());
            frame[8]=(FEC_DATA_SHARDS+first+p) as u8;
            frame[9]=FEC_DATA_SHARDS as u8;frame[10]=profile;
            frame[11]=sources.len() as u8;
            frame[12..14].copy_from_slice(&(len as u16).to_be_bytes());
            for (i,source) in sources.iter().enumerate(){
                frame[16+i*2..18+i*2]
                    .copy_from_slice(&(source.len() as u16).to_be_bytes());
            }
            frame[FEC_HEADER..].copy_from_slice(&body);
            result.push(frame);
        }
        Ok(result)
    }

    /// All Go parity rows in a single batch for legacy callers. Explicit
    /// first-send jobs use the bounded per-row method above instead.
    pub fn final_parity_wires(&self,block_id:u32,sources:&[&[u8]],
        profile:u8,wire_limit:usize)->Result<Vec<Vec<u8>>,FecMathError>{
        self.final_parity_wires_range(block_id,sources,profile,wire_limit,0,
            sources.len().min(usize::from(profile)))
    }

    /// Return only missing active original packets using e x e inverse and
    /// direct fused output coefficients. All inputs MUST be authenticated
    /// separately by the owner and match one trusted final FEC block header.
    /// Parity indices are absolute wire indices 20..20+configured R; lowest
    /// distinct e are chosen deterministically, regardless of arrival order.
    pub fn recover_missing(
        &self, final_meta:&FecHeader, sources:&[Option<&[u8]>],
        parities:&[(u8,&[u8])]
    )->Result<Vec<(usize,Vec<u8>)>,FecMathError>{
        Self::profile(final_meta.parity_count)?;
        let k=usize::from(final_meta.data_count);
        let len=usize::from(final_meta.shard_size);
        if !(1..=FEC_DATA_SHARDS).contains(&k) ||
            len==0||sources.len()!=k ||
            final_meta.lengths[..k].iter().any(|&n|n==0||usize::from(n)>len) ||
            final_meta.lengths[k..].iter().any(|&n|n!=0){
            return Err(FecMathError::InvalidLength);
        }
        let mut missing=Vec::new();
        let mut known=Vec::new();
        for (i,source) in sources.iter().enumerate(){
            match source{
                Some(payload)=>{
                    if payload.len()!=usize::from(final_meta.lengths[i]){
                        return Err(FecMathError::InvalidLength);
                    }
                    known.push((i,*payload));
                },
                None=>missing.push(i),
            }
        }
        if missing.is_empty(){return Ok(Vec::new());}
        let e=missing.len();
        if e>usize::from(final_meta.parity_count) || e>parities.len(){
            return Err(FecMathError::TooManyMissing);
        }
        let mut sorted=parities.to_vec();
        sorted.sort_by_key(|(idx,_)|*idx);
        let mut previous=None;
        for &(index,body) in &sorted{
            if usize::from(index)<FEC_DATA_SHARDS ||
                usize::from(index)>=FEC_DATA_SHARDS+usize::from(final_meta.parity_count) {
                return Err(FecMathError::InvalidIndex);
            }
            if previous==Some(index){return Err(FecMathError::DuplicateParity);}
            if body.len()!=len{return Err(FecMathError::InvalidLength);}
            previous=Some(index);
        }
        let chosen=&sorted[..e];
        let matrix=chosen.iter().map(|&(index,_)|{
            missing.iter().map(|&d|self.generator[usize::from(index)][d])
                .collect::<Vec<_>>()
        }).collect::<Vec<_>>();
        let inverse=self.gf.invert(&matrix)?;
        let mut output=Vec::with_capacity(e);
        for (out_row,&missing_index) in missing.iter().enumerate(){
            let mut decoded=vec![0u8;len];
            // Direct D coefficients: selected parity plus known systematic.
            for (q,&(_,body)) in chosen.iter().enumerate(){
                let coeff=inverse[out_row][q];
                if coeff==0{continue;}
                for (j,&b) in body.iter().enumerate(){
                    decoded[j]^=self.gf.mul(coeff,b);
                }
            }
            for &(col,src) in &known{
                let mut coeff=0u8;
                for (q,&(index,_)) in chosen.iter().enumerate(){
                    coeff^=self.gf.mul(inverse[out_row][q],
                        self.generator[usize::from(index)][col]);
                }
                if coeff==0{continue;}
                for (j,&b) in src.iter().enumerate(){
                    decoded[j]^=self.gf.mul(coeff,b);
                }
            }
            decoded.truncate(usize::from(final_meta.lengths[missing_index]));
            output.push((missing_index,decoded));
        }
        Ok(output)
    }
}
