//! M0 shared Rust-only cross-role buffer handoff CONTRACT, not an arena,
//! codec, driver or C ABI. M1 implements allocations; M3 owns seal mutation;
//! M2 retains frozen handles; M4 only reads borrowed ciphertext.
//! These traits do not prove zero-copy or bounded shutdown by themselves.
use core::ops::Range;
use crate::{BufferKey, LaneKey, RecordPn, SeqOffset};

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct BufferOrigin { pub owner_arena: u32, pub key: BufferKey }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FrozenMetadata {
    pub lane: LaneKey, pub seq: SeqOffset, pub pn: RecordPn,
    pub carrier_snapshot: u64,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BufferContractError {
    NoCapacity, InvalidWindow, StaleGeneration, OwnerStopping,
}

/// M1-allocated unique writable byte region. The only path to publish
/// it consumes the unique owner, preventing mutable aliases after freeze.
/// M1 must implement bounded return backlog and owner/generation validation.
pub trait UniqueSealable {
    type Frozen: FrozenRecordHandle;
    fn origin(&self) -> BufferOrigin;
    fn writable(&mut self) -> &mut [u8];
    fn freeze(self, written_wire: Range<usize>, metadata: FrozenMetadata)
        -> Result<Self::Frozen, BufferContractError>;
}

/// Immutable owning handle. M2 retains/clones it for same ciphertext repair;
/// M4 can borrow bytes read-only. M1 must separately prove that cloning
/// shares one allocation, does not copy payload and has bounded lifetime.
pub trait FrozenRecordHandle: Clone + Send + Sync + 'static {
    fn origin(&self) -> BufferOrigin;
    fn metadata(&self) -> FrozenMetadata;
    fn bytes(&self) -> &[u8];
}
pub struct DriverRead<'a> { pub metadata: FrozenMetadata, pub wire: &'a [u8] }
pub fn driver_read<'a,F:FrozenRecordHandle>(frozen:&'a F)->DriverRead<'a>{
    DriverRead{metadata:frozen.metadata(),wire:frozen.bytes()}
}
/// Bounds only; initialization and authentication remain M3 obligations.
pub fn checked_wire_range(capacity:usize,range:Range<usize>)
    ->Result<Range<usize>,BufferContractError>{
    if range.start>=range.end || range.end>capacity {
        Err(BufferContractError::InvalidWindow)
    }else{Ok(range)}
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::TunnelKey;
    use std::sync::Arc;
    #[derive(Clone)]
    struct FakeFrozen {bytes:Arc<[u8]>,origin:BufferOrigin,meta:FrozenMetadata}
    impl FrozenRecordHandle for FakeFrozen {
        fn origin(&self)->BufferOrigin{self.origin}
        fn metadata(&self)->FrozenMetadata{self.meta}
        fn bytes(&self)->&[u8]{&self.bytes}
    }
    struct FakeUnique{bytes:Vec<u8>,origin:BufferOrigin}
    impl UniqueSealable for FakeUnique{
        type Frozen=FakeFrozen;
        fn origin(&self)->BufferOrigin{self.origin}
        fn writable(&mut self)->&mut[u8]{&mut self.bytes}
        fn freeze(self,range:Range<usize>,meta:FrozenMetadata)
            ->Result<Self::Frozen,BufferContractError>{
            let r=checked_wire_range(self.bytes.len(),range)?;
            // Fixture allocates; unlike M1 future real arena, NOT zero-copy.
            Ok(FakeFrozen{bytes:self.bytes[r].to_vec().into(),origin:self.origin,meta})
        }
    }
    fn meta()->FrozenMetadata{
        FrozenMetadata{lane:LaneKey{tunnel:TunnelKey{slot:7,generation:3},slot:2,generation:5},
                       seq:SeqOffset(10),pn:RecordPn(99),carrier_snapshot:42}
    }
    #[test]
    fn r0_buffer_unique_mutation_frozen_handle_and_read_only_driver(){
        let origin=BufferOrigin{owner_arena:3,key:BufferKey{slot:5,generation:12}};
        let mut buf=FakeUnique{bytes:vec![0;64],origin};
        buf.writable()[8..12].copy_from_slice(&[1,2,3,4]);
        let frozen=buf.freeze(8..12,meta()).unwrap();
        let repair=frozen.clone();
        assert_eq!(repair.origin(),origin);
        assert_eq!(frozen.bytes(),repair.bytes());
        let driver=driver_read(&repair);
        assert_eq!(driver.wire,&[1,2,3,4]);
        assert_eq!(driver.metadata.pn,RecordPn(99));
    }
    #[test]
    fn r0_buffer_invalid_bounds_never_publish(){
        assert_eq!(checked_wire_range(64,7..12),Ok(7..12));
        for r in [1..1,12..11,0..65,100..101]{
            assert_eq!(checked_wire_range(64,r),Err(BufferContractError::InvalidWindow));
        }
        let b=FakeUnique{bytes:vec![0;8],origin:BufferOrigin{
            owner_arena:1,key:BufferKey{slot:1,generation:2}}};
        assert!(matches!(b.freeze(4..9,meta()),Err(BufferContractError::InvalidWindow)));
    }
    #[test]
    fn r0_buffer_arena_id_distinguishes_equal_slots(){
        let key=BufferKey{slot:1,generation:2};
        assert_ne!(BufferOrigin{owner_arena:1,key},BufferOrigin{owner_arena:2,key});
    }
}
