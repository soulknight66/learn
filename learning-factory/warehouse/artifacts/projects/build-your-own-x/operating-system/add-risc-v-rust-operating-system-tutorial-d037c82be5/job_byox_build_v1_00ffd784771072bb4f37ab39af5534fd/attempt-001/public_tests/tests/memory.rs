use rvkernel_model::memory::{
    Access, Frame, FrameAllocator, FrameError, MapError, PteFlags, Sv39, TranslateError,
};

fn user_rw() -> PteFlags {
    PteFlags::VALID | PteFlags::READ | PteFlags::WRITE | PteFlags::USER
}

#[test]
fn memory_allocator_is_lowest_first_and_defensive() {
    let mut frames = FrameAllocator::new(8, 3).unwrap();
    assert_eq!(frames.allocate(), Ok(Frame(8)));
    assert_eq!(frames.allocate(), Ok(Frame(9)));
    assert_eq!(frames.deallocate(Frame(8)), Ok(()));
    assert_eq!(frames.allocate(), Ok(Frame(8)));
    assert_eq!(frames.deallocate(Frame(12)), Err(FrameError::ForeignFrame(Frame(12))));
    assert_eq!(frames.free_count(), 1);
    assert_eq!(frames.allocated_count(), 2);
}

#[test]
fn memory_map_translate_and_reclaim_tables() {
    let mut frames = FrameAllocator::new(10, 8).unwrap();
    let mut table = Sv39::new(&mut frames).unwrap();
    let flags = user_rw();

    table.map(&mut frames, 0x4000, 0x20_0000, flags).unwrap();
    assert_eq!(table.table_frame_count(), 3);
    assert_eq!(table.translate(0x4123, Access::Read, true), Ok(0x20_0123));
    assert_eq!(table.translate(0x4123, Access::Write, true), Ok(0x20_0123));
    assert_eq!(
        table.translate(0x4123, Access::Execute, true),
        Err(TranslateError::PermissionDenied)
    );

    let before = frames.allocated_count();
    assert_eq!(
        table.map(&mut frames, 0x4000, 0x30_0000, flags),
        Err(MapError::AlreadyMapped)
    );
    assert_eq!(frames.allocated_count(), before);

    let old = table.unmap(&mut frames, 0x4000).unwrap();
    assert_eq!(old.frame, Frame(0x20_0000 / 4096));
    assert_eq!(old.flags, flags);
    assert_eq!(table.table_frame_count(), 1);
    assert_eq!(frames.allocated_count(), 1);
    assert_eq!(table.validate(), Ok(()));
}

#[test]
fn memory_out_of_frames_rolls_back_the_walk() {
    let mut frames = FrameAllocator::new(1, 2).unwrap();
    let mut table = Sv39::new(&mut frames).unwrap();

    assert_eq!(
        table.map(&mut frames, 0, 0x1000, PteFlags::VALID | PteFlags::READ),
        Err(MapError::OutOfFrames)
    );
    assert_eq!(table.table_frame_count(), 1);
    assert_eq!(frames.free_count(), 1);
    assert_eq!(frames.allocated_count(), 1);
    assert_eq!(table.validate(), Ok(()));
}
