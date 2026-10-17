//! Explicit M3-only optional ISA-L backend. The original Go-normalized
//! GF(256) generator and scalar entrypoints remain the default oracle.
//! No unsafe code, threads, CPU-performance or production dispatch claim.
#![forbid(unsafe_code)]
use super::*;

#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub enum FecBackendChoice { Scalar, PreferNative, RequireNative }
#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub enum FecBackendUsed { Scalar, NativeIsaL }

impl ReedSolomon20 {
    // A real NativeIsaL result is returned ONLY after Tables::encode calls
    // the native C ec_encode_data successfully. Feature compilation alone
    // never produces this status. Inputs may be unequal length: make inactive
    // tail bytes deterministically zero, never read poisoned arena capacity.
    fn selected_matrix_rows(&self, inputs:&[&[u8]], len:usize,
        coeff:&[u8], rows:usize, choice:FecBackendChoice)
        ->Result<(Vec<Vec<u8>>,FecBackendUsed),FecMathError> {
        if inputs.is_empty()||inputs.len()>20||rows==0||rows>20||
            len==0||len>MAX_SOURCE_SIZE||coeff.len()!=rows*inputs.len()||
            inputs.iter().any(|s|s.is_empty()||s.len()>len){
            return Err(FecMathError::InvalidLength);
        }
        if choice!=FecBackendChoice::Scalar && len>=64 {
            #[cfg(feature="native-isal")]
            {
                // Identical-length original buffers are borrowed, avoiding
                // an additional full-block copy on the fast path.
                let padded=inputs.iter().any(|b|b.len()!=len).then(||inputs.iter()
                    .map(|b|{let mut v=vec![0u8;len];v[..b.len()].copy_from_slice(b);v})
                    .collect::<Vec<_>>());
                let source:Vec<&[u8]>=if let Some(ref owned)=padded{
                    owned.iter().map(Vec::as_slice).collect()
                }else{inputs.to_vec()};
                let tables=wbd_isal_safe::Tables::new(inputs.len(),rows,coeff)
                    .map_err(|_|FecMathError::NativeFailure)?;
                let mut outputs=vec![vec![0u8;len];rows];
                let mut dest=outputs.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
                tables.encode(&source,&mut dest).map_err(|_|FecMathError::NativeFailure)?;
                return Ok((outputs,FecBackendUsed::NativeIsaL));
            }
        }
        if choice==FecBackendChoice::RequireNative{
            return Err(FecMathError::NativeUnavailable);
        }
        let mut outputs=vec![vec![0u8;len];rows];
        for (r,dst) in outputs.iter_mut().enumerate(){
            for (col,src) in inputs.iter().enumerate(){
                let a=coeff[r*inputs.len()+col];
                if a==0{continue;}
                for (j,&b) in src.iter().enumerate(){dst[j]^=self.gf.mul(a,b);}
            }
        }
        Ok((outputs,FecBackendUsed::Scalar))
    }

    /// Explicit backend select; no change to encode_rows_active or the
    /// default FecTxOwner constructor. Only active columns are supplied.
    pub fn encode_rows_active_selected(&self,sources:&[&[u8]],profile:u8,
        first:usize,rows:usize,choice:FecBackendChoice)
        ->Result<(Vec<Vec<u8>>,FecBackendUsed),FecMathError>{
        let configured=Self::profile(profile)?;
        let len=self.validate_sources(sources)?;
        let sent=sources.len().min(configured);
        if rows==0||first>=sent||rows>sent-first{
            return Err(FecMathError::InvalidIndex);
        }
        let mut coeff=Vec::with_capacity(rows*sources.len());
        for row in first..first+rows{
            coeff.extend_from_slice(&self.generator[20+row][..sources.len()]);
        }
        self.selected_matrix_rows(sources,len,&coeff,rows,choice)
    }

    /// Go-compatible final wire layout, not a new protocol.
    pub fn final_parity_wires_range_selected(&self,block_id:u32,
        sources:&[&[u8]],profile:u8,wire_limit:usize,
        first:usize,rows:usize,choice:FecBackendChoice)
        ->Result<(Vec<Vec<u8>>,FecBackendUsed),FecMathError>{
        let len=self.validate_sources(sources)?;
        if FEC_HEADER+len>wire_limit{return Err(FecMathError::InvalidLength);}
        let (parity,used)=self.encode_rows_active_selected(sources,profile,first,rows,choice)?;
        let mut wires=Vec::with_capacity(parity.len());
        for (i,body) in parity.into_iter().enumerate(){
            let mut frame=vec![0u8;FEC_HEADER+len];
            frame[..4].copy_from_slice(b"WF\x01\x00");
            frame[4..8].copy_from_slice(&block_id.to_be_bytes());
            frame[8]=(20+first+i) as u8;
            frame[9]=20;frame[10]=profile;frame[11]=sources.len() as u8;
            frame[12..14].copy_from_slice(&(len as u16).to_be_bytes());
            for (j,src) in sources.iter().enumerate(){
                frame[16+j*2..18+j*2].copy_from_slice(&(src.len() as u16).to_be_bytes());
            }
            frame[FEC_HEADER..].copy_from_slice(&body);
            wires.push(frame);
        }
        Ok((wires,used))
    }

    /// Same missing-only e-by-e inverse as the scalar Go oracle; only the
    /// fused GF row multiplication is dispatched to the selected backend.
    /// Parity is sorted by authenticated index before selecting e rows.
    pub fn recover_missing_selected(&self,meta:&FecHeader,
        sources:&[Option<&[u8]>],parities:&[(u8,&[u8])],choice:FecBackendChoice)
        ->Result<(Vec<(usize,Vec<u8>)>,FecBackendUsed),FecMathError>{
        if choice==FecBackendChoice::Scalar{
            return Ok((self.recover_missing(meta,sources,parities)?,FecBackendUsed::Scalar));
        }
        Self::profile(meta.parity_count)?;
        let k=usize::from(meta.data_count);
        let len=usize::from(meta.shard_size);
        if !(1..=20).contains(&k)||len==0||sources.len()!=k||
           meta.lengths[..k].iter().any(|&n|n==0||usize::from(n)>len)||
           meta.lengths[k..].iter().any(|&n|n!=0){
            return Err(FecMathError::InvalidLength);
        }
        let mut missing=Vec::new();
        let mut known=Vec::new();
        for (i,src) in sources.iter().enumerate(){
            match src{
                Some(s)=>{
                    if s.len()!=usize::from(meta.lengths[i]){return Err(FecMathError::InvalidLength);}
                    known.push((i,*s));
                },
                None=>missing.push(i),
            }
        }
        if missing.is_empty(){return Ok((Vec::new(),FecBackendUsed::Scalar));}
        let e=missing.len();
        if e>usize::from(meta.parity_count)||e>parities.len(){
            return Err(FecMathError::TooManyMissing);
        }
        let mut sorted=parities.to_vec();
        sorted.sort_by_key(|p|p.0);
        let mut previous=None;
        for &(idx,data) in &sorted{
            if usize::from(idx)<20||usize::from(idx)>=20+usize::from(meta.parity_count){
                return Err(FecMathError::InvalidIndex);
            }
            if previous==Some(idx){return Err(FecMathError::DuplicateParity);}
            if data.len()!=len{return Err(FecMathError::InvalidLength);}
            previous=Some(idx);
        }
        if len<64 && choice==FecBackendChoice::PreferNative{
            return Ok((self.recover_missing(meta,sources,parities)?,FecBackendUsed::Scalar));
        }
        let chosen=&sorted[..e];
        let matrix=chosen.iter().map(|(idx,_)|missing.iter()
            .map(|&col|self.generator[usize::from(*idx)][col]).collect::<Vec<_>>())
            .collect::<Vec<_>>();
        let inverse=self.gf.invert(&matrix)?;
        let mut coeff=Vec::with_capacity(e*k);
        for out in 0..e{
            // First e columns are selected parity, then k-e known sources.
            coeff.extend_from_slice(&inverse[out]);
            for &(col,_) in &known{
                let mut a=0u8;
                for (q,(idx,_)) in chosen.iter().enumerate(){
                    a^=self.gf.mul(inverse[out][q],
                        self.generator[usize::from(*idx)][col]);
                }
                coeff.push(a);
            }
        }
        let inputs=chosen.iter().map(|(_,b)|*b).chain(known.iter().map(|(_,b)|*b))
            .collect::<Vec<_>>();
        let (mut bytes,used)=self.selected_matrix_rows(&inputs,len,&coeff,e,choice)?;
        let mut recovered=Vec::with_capacity(e);
        for (index,mut output) in missing.into_iter().zip(bytes.drain(..)){
            output.truncate(usize::from(meta.lengths[index]));
            recovered.push((index,output));
        }
        Ok((recovered,used))
    }
}
