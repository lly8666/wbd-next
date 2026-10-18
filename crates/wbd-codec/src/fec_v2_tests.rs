//! Independent F2-MATH/WIRE negative and erasure oracles. V1 Go vectors
//! stay in fec_math_tests; these never compare V2 to old Go bytes.
use crate::fec_v2::*;

fn gf_ref_mul(mut a:u8,mut b:u8)->u8 {
    let mut out=0;
    while b!=0 {
        if b&1!=0 {out^=a;}
        let top=a&0x80!=0;
        a<<=1;if top{a^=0x1d;}
        b>>=1;
    }
    out
}
fn gf_ref_div(a:u8,b:u8)->u8 {
    assert_ne!(b,0);
    (0u16..=255).find(|&x|gf_ref_mul(x as u8,b)==a).unwrap() as u8
}
fn independent_coefficient(row:usize,col:usize,k:usize)->u8 {
    if row==0 || k==1 {1}
    else {let y=(32+col) as u8;gf_ref_div(y,(row as u8)^y)}
}
fn oracle_row(src:&[&[u8]],row:usize)->Vec<u8> {
    let len=src.iter().map(|x|x.len()).max().unwrap()+2;
    let mut out=vec![0;len];
    for (j,frame) in src.iter().enumerate() {
        let coef=independent_coefficient(row,j,src.len());
        let prefix=(frame.len() as u16).to_be_bytes();
        for at in 0..len {
            let x=if at<2 {prefix[at]} else {frame.get(at-2).copied().unwrap_or(0)};
            out[at]^=gf_ref_mul(coef,x);
        }
    }
    out
}
fn frames(k:usize)->Vec<Vec<u8>> {
    (0..k).map(|i| {
        let n=match i%7 {0=>0,1=>1,2=>15,3=>31,4=>63,5=>64,_=>65};
        (0..n).map(|j|((i*37+j*13+7)%251) as u8).collect()
    }).collect()
}
fn all_rows(rs:&Rs16,block:u64,frames:&[Vec<u8>],p:Profile,limit:usize)
            ->Vec<Vec<u8>> {
    let borrowed=frames.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let r=p.parity_count(frames.len()).unwrap();
    let mut out=Vec::new();
    for start in (0..r).step_by(MAX_BATCH_ROWS) {
        let n=(r-start).min(MAX_BATCH_ROWS);
        let (mut rows,used)=rs.encode_owned(block,&borrowed,p,start,n,limit,BackendChoice::Scalar).unwrap();
        assert_eq!(used,BackendUsed::Scalar);
        for (i,wire) in rows.iter_mut().enumerate() {
            let parsed=parse_repair(wire,limit).unwrap();
            assert_eq!(parsed.body,oracle_row(&borrowed,start+i));
            assert_eq!(parsed.parity_row as usize,start+i);
            assert_eq!(parsed.actual_k as usize,frames.len());
        }
        out.extend(rows);
    }
    out
}
#[test]
fn r1_f2_independent_cauchy_all_rows_and_profiles() {
    let rs=Rs16::new();
    for k in 1..=16 {
        for p in Profile::ALL {
            let (num,den)=p.ratio();
            let count=p.parity_count(k).unwrap();
            assert_eq!(count,(k*num+den-1)/den);
            assert!((1..=20).contains(&count));
            for row in 0..20 {
                for col in 0..k {
                    assert_eq!(rs.coefficient(row,col,k).unwrap(),
                               independent_coefficient(row,col,k),
                               "k={k} row={row} col={col}");
                }
            }
        }
    }
    assert_eq!(Profile::Strong.parity_count(16),Ok(16));
    assert_eq!(Profile::Maximum.parity_count(16),Ok(20));
    assert_eq!(Profile::Maximum.parity_count(1),Ok(2));
    assert_eq!(Profile::Light.parity_count(1),Ok(1));
    assert_eq!("strong".parse::<Profile>(),Ok(Profile::Strong));
    assert_eq!("20:20".parse::<Profile>(),Err(Error::UnsupportedProfile));
    assert_eq!(rs.coefficient(20,0,2),Err(Error::InvalidRow));
    assert_eq!(rs.coefficient(0,16,16),Err(Error::InvalidIndex));
    assert_eq!(Profile::Strong.parity_count(0),Err(Error::InvalidK));
}
#[test]
fn r1_f2_wire_golden_endianness_short_zero_and_strict_header() {
    let src=source_owned(0x0102030405060708,15,b"ab",100).unwrap();
    assert_eq!(src,vec![1,2,3,4,5,6,7,8,15,0,b'a',b'b']);
    let s=parse_source(&src,100).unwrap();
    assert_eq!((s.block_id,s.source_index,s.frame),(0x0102030405060708,15,b"ab".as_slice()));
    let empty=source_owned(1,0,&[],14).unwrap();
    assert_eq!(empty.len(),SOURCE_HEADER);
    assert_eq!(parse_source(&empty,14).unwrap().frame,b"");
    let r=Rs16::new();
    let mut dest=vec![0xee;14];
    let choice=r.encode_into(1,&[&[][..]],Profile::Maximum,0,
        &mut [&mut dest],14,BackendChoice::Scalar).unwrap();
    assert_eq!(choice,BackendUsed::Scalar);
    assert_eq!(dest,vec![0,0,0,0,0,0,0,1,0,1,0,2,0,0]);
    assert_eq!(parse_repair(&dest,14).unwrap().body,&[0,0]);
    let mut bad=src.clone();bad[9]=1;
    assert_eq!(parse_source(&bad,100),Err(Error::NonzeroFlags));
    bad=src.clone();bad[8]=16;
    assert_eq!(parse_source(&bad,100),Err(Error::InvalidIndex));
    assert!(parse_source(&src[..9],100).is_err());
    assert!(parse_source(&src,11).is_err());
    assert_eq!(source_owned(0,0,b"",100),Err(Error::InvalidIndex));
    assert_eq!(source_owned(1,0,b"a",14),Err(Error::BudgetExceeded));
    let mut bad=dest.clone();bad[8]=20;
    assert_eq!(parse_repair(&bad,14),Err(Error::InvalidRow));
    bad=dest.clone();bad[9]=0;
    assert_eq!(parse_repair(&bad,14),Err(Error::InvalidK));
    bad=dest.clone();bad[11]=3;
    assert_eq!(parse_repair(&bad,14),Err(Error::InvalidLength));
    bad=dest.clone();bad.push(1);
    assert!(parse_repair(&bad,15).is_err());
}
#[test]
fn r1_f2_full_profiles_all_k_and_every_erasure_count() {
    for k in 1..=MAX_K {
        let f=frames(k);
        for p in Profile::ALL {
            let mut rs=Rs16::new();
            let rows=all_rows(&rs,0x100000000+k as u64,&f,p,100);
            let r=rows.len();
            // e0..min(k,r), select e distinct parity rows only.
            for e in 0..=k.min(r) {
                let mut originals=f.iter().map(|x|Some(x.as_slice())).collect::<Vec<_>>();
                // Deterministic non-prefix source loss; includes index k-1.
                let erased=(0..e).map(|i|(i*7+k-1)%k).collect::<Vec<_>>();
                // 7 may not be coprime to k, ensure unique by cycling all k.
                let mut used=[false;MAX_K];let mut removed=0;
                for &i in &erased {if !used[i] {used[i]=true;originals[i]=None;removed+=1;}}
                for idx in (0..k).rev() {
                    if removed==e {break;}
                    if !used[idx] {used[idx]=true;originals[idx]=None;removed+=1;}
                }
                let repair=rows.iter().take(e).map(|row|parse_repair(row,100).unwrap())
                    .collect::<Vec<_>>();
                let (got,backend)=rs.recover_missing(0x100000000+k as u64,
                    &originals,&repair,100,BackendChoice::Scalar).unwrap();
                assert_eq!(backend,BackendUsed::Scalar);
                assert_eq!(got.len(),e);
                for (idx,payload) in got {assert_eq!(payload,f[idx as usize]);}
                assert!(rs.cache_entries()<=DECODE_CACHE_LIMIT);
            }
        }
    }
}
#[test]
fn r1_f2_odd_size_mtu_dirty_outputs_and_direct_borrowed() {
    let rs=Rs16::new();
    let input=vec![vec![3u8;65],vec![8;1],vec![],vec![0x7f;63]];
    let src=input.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let length=REPAIR_HEADER+67;
    let mut a=vec![0x96;length];
    let mut b=vec![0xdd;length];
    let used=rs.encode_into(17,&src,Profile::Maximum,0,
        &mut [&mut a,&mut b],79,BackendChoice::Scalar).unwrap();
    assert_eq!(used,BackendUsed::Scalar);
    assert_eq!(a[12..],oracle_row(&src,0));
    assert_eq!(b[12..],oracle_row(&src,1));
    let saved=a.clone();
    a.fill(0xa5); // dirty recycled slab
    rs.encode_into(17,&src,Profile::Maximum,0,&mut [&mut a],
        79,BackendChoice::Scalar).unwrap();
    assert_eq!(a,saved);
    assert_eq!(rs.encode_into(17,&src,Profile::Maximum,0,
        &mut [&mut vec![0u8;length-1]],79,BackendChoice::Scalar),
        Err(Error::BudgetExceeded));
    assert_eq!(rs.encode_into(17,&src,Profile::Maximum,0,
        &mut [&mut vec![0u8;length]],78,BackendChoice::Scalar),
        Err(Error::BudgetExceeded));
    assert_eq!(max_original_for_record_budget(79),Ok(65));
    assert_eq!(source_owned(17,0,&input[0],79).unwrap().len(),75);
    assert_eq!(source_owned(17,0,&vec![0;66],79),Err(Error::BudgetExceeded));
}
#[test]
fn r1_f2_malformed_parity_scope_conflict_protected_length_and_no_capability_shortcut() {
    let mut rs=Rs16::new();
    let f=vec![b"a".to_vec(),b"b".to_vec()];
    let wires=all_rows(&rs,99,&f,Profile::Strong,80);
    let original=[None,Some(b"b".as_slice())];
    let row=parse_repair(&wires[0],80).unwrap();
    let (got,_) =rs.recover_missing(99,&original,&[row],80,BackendChoice::Scalar).unwrap();
    assert_eq!(got[0].1,b"a");
    assert_eq!(rs.recover_missing(99,&original,&[],80,BackendChoice::Scalar),
        Err(Error::TooManyMissing));
    assert_eq!(rs.recover_missing(100,&original,&[row],80,BackendChoice::Scalar),
        Err(Error::ConflictingMeta));
    assert_eq!(rs.recover_missing(99,&original,&[row,row],80,BackendChoice::Scalar),
        Err(Error::DuplicateParity));
    let mut corrupted=wires[0].clone();
    // row0 XOR: altering parity prefix to encode absurd protected length.
    corrupted[12]=0xff;corrupted[13]=0xff;
    let bad=parse_repair(&corrupted,80).unwrap();
    assert_eq!(rs.recover_missing(99,&original,&[bad],80,BackendChoice::Scalar),
        Err(Error::CorruptProtectedLength));
    // Neither native feature availability nor a caller's guess may authorize
    // 2/3 on a legacy session. These are bare inner payload helpers only.
    assert_eq!(AUTHENTICATED_FEC2_SOURCE_KIND,2);
    assert_eq!(AUTHENTICATED_FEC2_REPAIR_KIND,3);
    assert_eq!(rs.encode_owned(99,&[b"ab"],Profile::Light,0,1,80,
        BackendChoice::RequireNative),Err(Error::NativeUnavailable));
}
#[test]
fn r1_f2_decode_cache_bounded_and_partial_with_repair_first() {
    let mut rs=Rs16::new();
    let f=(0..16).map(|i|vec![i as u8;65]).collect::<Vec<_>>();
    let rows=all_rows(&rs,44,&f,Profile::Maximum,100);
    let mut original=f.iter().map(|x|Some(x.as_slice())).collect::<Vec<_>>();
    for i in 0..8 {original[i]=None;}
    let parsed=rows[..8].iter().map(|v|parse_repair(v,100).unwrap()).collect::<Vec<_>>();
    let (first,_) =rs.recover_missing(44,&original,&parsed,100,BackendChoice::Scalar).unwrap();
    let (second,_) =rs.recover_missing(44,&original,&parsed,100,BackendChoice::Scalar).unwrap();
    assert_eq!(first,second);
    assert_eq!(rs.cache_entries(),1);
    // No admission/lifecycle state is modified by mathematical recovery:
    // the authenticated owner must enforce first arrival, epoch and Stop.
}
#[cfg(feature="native-isal")]
#[test]
fn r1_f2_real_isal_exact_rows_and_missing_only_native_equivalence() {
    let mut scalar=Rs16::new();
    let mut native=Rs16::new();
    for k in [2usize,3,8,16] {
        let f=(0..k).map(|i|vec![(i*7) as u8;128+i]).collect::<Vec<_>>();
        let src=f.iter().map(Vec::as_slice).collect::<Vec<_>>();
        let (scalar_rows,_) =scalar.encode_owned(400+k as u64,&src,
            Profile::Maximum,0,4,180,BackendChoice::Scalar).unwrap();
        let (native_rows,used) =native.encode_owned(400+k as u64,&src,
            Profile::Maximum,0,4,180,BackendChoice::RequireNative).unwrap();
        assert_eq!(used,BackendUsed::NativeIsaL);
        assert_eq!(scalar_rows,native_rows);
        let mut originals=f.iter().map(|x|Some(x.as_slice())).collect::<Vec<_>>();
        originals[0]=None;originals[k-1]=None;
        let rp=native_rows.iter().take(2).map(|w|parse_repair(w,180).unwrap()).collect::<Vec<_>>();
        let (a,_) =scalar.recover_missing(400+k as u64,&originals,&rp,180,
            BackendChoice::Scalar).unwrap();
        let (b,how) =native.recover_missing(400+k as u64,&originals,&rp,180,
            BackendChoice::RequireNative).unwrap();
        assert_eq!(how,BackendUsed::NativeIsaL);
        assert_eq!(a,b);
        for (index,payload) in a {assert_eq!(payload,f[index as usize]);}
    }
}

#[test]
fn r1_f2_prepared_block_batch_dirty_reuse_and_exact_oracle() {
    let rs=Rs16::new();
    for k in [1usize,2,8,16] {
        let f=frames(k);
        let src=f.iter().map(Vec::as_slice).collect::<Vec<_>>();
        let mut block=PreparedBlock::from_frames(&src,100).unwrap();
        assert_eq!(block.k(),k);
        let r=Profile::Maximum.parity_count(k).unwrap();
        for start in (0..r).step_by(MAX_BATCH_ROWS) {
            let count=(r-start).min(MAX_BATCH_ROWS);
            let size=REPAIR_HEADER+block.symbol_len();
            let mut owned=vec![vec![0x7b;size];count];
            let got={
                let mut slices=owned.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
                rs.encode_prepared_into(91,&mut block,Profile::Maximum,start,
                    &mut slices,100,BackendChoice::Scalar).unwrap()
            };
            assert_eq!(got,BackendUsed::Scalar);
            for (i,row) in owned.iter().enumerate() {
                assert_eq!(parse_repair(row,100).unwrap().body,oracle_row(&src,start+i));
            }
        }
        assert_eq!(block.cached_native_tables(),0);
    }
}
#[cfg(feature="native-isal")]
#[test]
fn r1_f2_prepared_native_cached_tables_real_ec_encode_data() {
    let rs=Rs16::new();
    let f=(0..16).map(|i|vec![(i*17) as u8;128+i]).collect::<Vec<_>>();
    let src=f.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let mut block=PreparedBlock::from_frames(&src,180).unwrap();
    for _ in 0..3 {
        let size=REPAIR_HEADER+block.symbol_len();
        let mut out=vec![vec![0xee;size];4];
        let mut borrowed=out.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
        let backend=rs.encode_prepared_into(812,&mut block,Profile::Maximum,0,
            &mut borrowed,180,BackendChoice::RequireNative).unwrap();
        assert_eq!(backend,BackendUsed::NativeIsaL);
        for (i,w) in out.iter().enumerate() {
            assert_eq!(parse_repair(w,180).unwrap().body,oracle_row(&src,i));
        }
    }
    assert_eq!(block.cached_native_tables(),1);
}

#[test]
fn r1_f2_source_membership_and_index_reject_conflict() {
    let rs=Rs16::new();
    let f=frames(2);
    let wires=all_rows(&rs,47,&f,Profile::Strong,100);
    let repair=parse_repair(&wires[0],100).unwrap();
    let src=source_owned(47,1,&f[1],100).unwrap();
    assert_eq!(validate_source_against_repair(&parse_source(&src,100).unwrap(),&repair),Ok(()));
    let wrong_block=source_owned(48,1,&f[1],100).unwrap();
    assert_eq!(validate_source_against_repair(&parse_source(&wrong_block,100).unwrap(),&repair),
        Err(Error::ConflictingMeta));
    let wrong_index=source_owned(47,2,&f[1],100).unwrap();
    assert_eq!(validate_source_against_repair(&parse_source(&wrong_index,100).unwrap(),&repair),
        Err(Error::InvalidIndex));
    let oversize=source_owned(47,0,&vec![0xab;65],100).unwrap();
    assert_eq!(validate_source_against_repair(&parse_source(&oversize,100).unwrap(),&repair),
        Err(Error::ConflictingMeta));
}
#[test]
fn r1_f2_mds_nonprefix_repair_pairs_and_variable_missing() {
    let mut rs=Rs16::new();
    for k in 2usize..=4 {
        let f=frames(k);
        let full=all_rows(&rs,500+k as u64,&f,Profile::Maximum,100);
        // Exhaust all 190 parity-row pairs including row 19, and every
        // distinct pair of erased systematic sources. Independent oracle
        // ensures matrix actually encodes 0x11d Cauchy, not just roundtrip.
        for a in 0..20 {
            for b in a+1..20 {
                let repairs=[parse_repair(&full[a],100).unwrap(),
                             parse_repair(&full[b],100).unwrap()];
                for x in 0..k {
                    for y in x+1..k {
                        let mut original=f.iter().map(|s|Some(s.as_slice())).collect::<Vec<_>>();
                        original[x]=None;original[y]=None;
                        let (decoded,how)=rs.recover_missing(500+k as u64,&original,
                            &repairs,100,BackendChoice::Scalar).unwrap();
                        assert_eq!(how,BackendUsed::Scalar);
                        assert_eq!(decoded,vec![(x as u8,f[x].clone()),(y as u8,f[y].clone())]);
                    }
                }
            }
        }
        assert!(rs.cache_entries()<=DECODE_CACHE_LIMIT);
    }
}
