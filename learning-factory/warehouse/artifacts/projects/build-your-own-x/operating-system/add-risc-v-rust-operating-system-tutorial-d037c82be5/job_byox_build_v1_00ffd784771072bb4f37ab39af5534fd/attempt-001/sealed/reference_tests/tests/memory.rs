use rvkernel_model::memory::{
    Access, Frame, FrameAllocator, FrameError, MapError, PteFlags, Sv39, TranslateError,
    UnmapError, PAGE_SIZE,
};

fn read_only() -> PteFlags {
    PteFlags::VALID | PteFlags::READ
}

fn user_rw() -> PteFlags {
    PteFlags::VALID | PteFlags::READ | PteFlags::WRITE | PteFlags::USER
}

#[test]
fn allocator_rejects_overflow_exhaustion_and_double_free() {
    assert_eq!(
        FrameAllocator::new(u64::MAX, 2).unwrap_err(),
        FrameError::RangeOverflow
    );
    let mut frames = FrameAllocator::new(4, 1).unwrap();
    assert_eq!(frames.allocate(), Ok(Frame(4)));
    assert_eq!(frames.allocate(), Err(FrameError::OutOfFrames));
    assert_eq!(frames.deallocate(Frame(4)), Ok(()));
    assert_eq!(
        frames.deallocate(Frame(4)),
        Err(FrameError::NotAllocated(Frame(4)))
    );
    assert_eq!(
        frames.deallocate(Frame(5)),
        Err(FrameError::ForeignFrame(Frame(5)))
    );
    assert_eq!(frames.free_count(), 1);
    assert_eq!(frames.allocated_count(), 0);
}

#[test]
fn root_allocation_and_failed_walk_are_atomic() {
    let mut empty = FrameAllocator::new(0, 0).unwrap();
    assert_eq!(Sv39::new(&mut empty).unwrap_err(), FrameError::OutOfFrames);

    let mut frames = FrameAllocator::new(20, 2).unwrap();
    let mut table = Sv39::new(&mut frames).unwrap();
    let root = table.root_frame();
    assert_eq!(
        table.map(&mut frames, 0, PAGE_SIZE, read_only()),
        Err(MapError::OutOfFrames)
    );
    assert_eq!(table.root_frame(), root);
    assert_eq!(table.table_frame_count(), 1);
    assert_eq!((frames.free_count(), frames.allocated_count()), (1, 1));
    assert_eq!(table.translate(0, Access::Read, false), Err(TranslateError::NotMapped));
    assert_eq!(table.validate(), Ok(()));
}

#[test]
fn address_and_flag_validation_happens_before_allocation() {
    let mut frames = FrameAllocator::new(30, 6).unwrap();
    let mut table = Sv39::new(&mut frames).unwrap();
    let before = (frames.free_count(), table.table_frame_count());

    assert_eq!(
        table.map(&mut frames, 1 << 39, 0, read_only()),
        Err(MapError::NonCanonical)
    );
    assert_eq!(
        table.map(&mut frames, 1, 0, read_only()),
        Err(MapError::UnalignedVirtual)
    );
    assert_eq!(
        table.map(&mut frames, 0, 1, read_only()),
        Err(MapError::UnalignedPhysical)
    );
    assert_eq!(
        table.map(&mut frames, 0, 0, PteFlags::VALID | PteFlags::WRITE),
        Err(MapError::InvalidFlags)
    );
    assert_eq!(
        table.map(&mut frames, 0, 0, PteFlags::VALID),
        Err(MapError::InvalidFlags)
    );
    assert_eq!((frames.free_count(), table.table_frame_count()), before);
}

#[test]
fn canonical_high_mapping_and_permission_matrix() {
    let mut frames = FrameAllocator::new(100, 8).unwrap();
    let mut table = Sv39::new(&mut frames).unwrap();
    let high = 0xffff_ffc0_0000_0000;
    table.map(&mut frames, high, 0x80_0000, user_rw()).unwrap();

    assert_eq!(
        table.translate(high + 0xabc, Access::Read, true),
        Ok(0x80_0abc)
    );
    assert_eq!(
        table.translate(high + 0xabc, Access::Write, true),
        Ok(0x80_0abc)
    );
    assert_eq!(
        table.translate(high, Access::Execute, true),
        Err(TranslateError::PermissionDenied)
    );
    assert_eq!(
        table.translate(1 << 39, Access::Read, false),
        Err(TranslateError::NonCanonical)
    );
    assert_eq!(table.validate(), Ok(()));
}

#[test]
fn unmap_preserves_shared_tables_then_reclaims_them() {
    let mut frames = FrameAllocator::new(200, 8).unwrap();
    let mut table = Sv39::new(&mut frames).unwrap();
    table.map(&mut frames, 0x1000, 0x91_000, read_only()).unwrap();
    table.map(&mut frames, 0x2000, 0x92_000, read_only()).unwrap();
    assert_eq!(table.table_frame_count(), 3);

    let first = table.unmap(&mut frames, 0x1000).unwrap();
    assert_eq!(first.frame, Frame(0x91));
    assert_eq!(table.table_frame_count(), 3);
    assert_eq!(
        table.translate(0x2007, Access::Read, false),
        Ok(0x92_007)
    );

    let second = table.unmap(&mut frames, 0x2000).unwrap();
    assert_eq!(second.frame, Frame(0x92));
    assert_eq!(table.table_frame_count(), 1);
    assert_eq!(frames.allocated_count(), 1);
    assert_eq!(table.validate(), Ok(()));
}

#[test]
fn wrong_allocator_cannot_make_unmap_partially_mutate() {
    let mut owner = FrameAllocator::new(300, 8).unwrap();
    let mut table = Sv39::new(&mut owner).unwrap();
    table.map(&mut owner, 0, 0xa0_000, read_only()).unwrap();
    let owner_before = owner.allocated_count();

    let mut wrong = FrameAllocator::new(1, 8).unwrap();
    assert!(matches!(
        table.unmap(&mut wrong, 0),
        Err(UnmapError::Allocator(FrameError::ForeignFrame(_)))
    ));
    assert_eq!(owner.allocated_count(), owner_before);
    assert_eq!(table.table_frame_count(), 3);
    assert_eq!(table.translate(3, Access::Read, false), Ok(0xa0_003));
    assert_eq!(table.validate(), Ok(()));
}
