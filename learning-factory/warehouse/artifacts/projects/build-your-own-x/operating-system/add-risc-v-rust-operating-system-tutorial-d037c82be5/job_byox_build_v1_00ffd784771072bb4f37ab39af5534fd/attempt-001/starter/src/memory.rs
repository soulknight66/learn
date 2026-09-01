use std::collections::{BTreeMap, BTreeSet};
use std::ops::{BitAnd, BitAndAssign, BitOr, BitOrAssign};

pub const PAGE_SIZE: u64 = 4096;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct Frame(pub u64);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrameError {
    RangeOverflow,
    OutOfFrames,
    ForeignFrame(Frame),
    NotAllocated(Frame),
}

#[derive(Clone, Debug)]
pub struct FrameAllocator {
    first: u64,
    end: u64,
    free: BTreeSet<Frame>,
    allocated: BTreeSet<Frame>,
}

impl FrameAllocator {
    pub fn new(first: u64, count: u64) -> Result<Self, FrameError> {
        todo!("construct the owned frame interval with checked arithmetic")
    }

    pub fn allocate(&mut self) -> Result<Frame, FrameError> {
        todo!("return the lowest free frame")
    }

    pub fn deallocate(&mut self, frame: Frame) -> Result<(), FrameError> {
        todo!("reject foreign and unallocated frames")
    }

    pub fn owns(&self, frame: Frame) -> bool {
        frame.0 >= self.first && frame.0 < self.end
    }

    pub fn free_count(&self) -> usize {
        self.free.len()
    }

    pub fn allocated_count(&self) -> usize {
        self.allocated.len()
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct PteFlags(u16);

impl PteFlags {
    pub const VALID: Self = Self(1 << 0);
    pub const READ: Self = Self(1 << 1);
    pub const WRITE: Self = Self(1 << 2);
    pub const EXECUTE: Self = Self(1 << 3);
    pub const USER: Self = Self(1 << 4);
    pub const GLOBAL: Self = Self(1 << 5);
    pub const ACCESSED: Self = Self(1 << 6);
    pub const DIRTY: Self = Self(1 << 7);

    pub const fn empty() -> Self {
        Self(0)
    }

    pub const fn bits(self) -> u16 {
        self.0
    }

    pub const fn from_bits(bits: u16) -> Option<Self> {
        if bits & !0xff == 0 {
            Some(Self(bits))
        } else {
            None
        }
    }

    pub const fn contains(self, other: Self) -> bool {
        self.0 & other.0 == other.0
    }

    pub const fn intersects(self, other: Self) -> bool {
        self.0 & other.0 != 0
    }
}

impl BitOr for PteFlags {
    type Output = Self;

    fn bitor(self, rhs: Self) -> Self::Output {
        Self(self.0 | rhs.0)
    }
}

impl BitOrAssign for PteFlags {
    fn bitor_assign(&mut self, rhs: Self) {
        self.0 |= rhs.0;
    }
}

impl BitAnd for PteFlags {
    type Output = Self;

    fn bitand(self, rhs: Self) -> Self::Output {
        Self(self.0 & rhs.0)
    }
}

impl BitAndAssign for PteFlags {
    fn bitand_assign(&mut self, rhs: Self) {
        self.0 &= rhs.0;
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Access {
    Read,
    Write,
    Execute,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Mapping {
    pub frame: Frame,
    pub flags: PteFlags,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MapError {
    NonCanonical,
    UnalignedVirtual,
    UnalignedPhysical,
    PhysicalAddressTooWide,
    InvalidFlags,
    AlreadyMapped,
    OutOfFrames,
    CorruptPageTable,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TranslateError {
    NonCanonical,
    NotMapped,
    PermissionDenied,
    CorruptPageTable,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum UnmapError {
    NonCanonical,
    UnalignedVirtual,
    NotMapped,
    CorruptPageTable,
    Allocator(FrameError),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MemoryInvariant {
    MissingRoot,
    UnknownTable(Frame),
    InvalidIntermediate,
    InvalidLeaf,
    UnreachableTable(Frame),
}

#[derive(Clone, Debug)]
pub struct Sv39 {
    root: Frame,
    tables: BTreeMap<Frame, Box<[u64; 512]>>,
}

impl Sv39 {
    pub fn new(allocator: &mut FrameAllocator) -> Result<Self, FrameError> {
        todo!("allocate and install one empty root table")
    }

    pub fn root_frame(&self) -> Frame {
        self.root
    }

    pub fn table_frame_count(&self) -> usize {
        self.tables.len()
    }

    pub fn map(
        &mut self,
        allocator: &mut FrameAllocator,
        virtual_address: u64,
        physical_address: u64,
        flags: PteFlags,
    ) -> Result<(), MapError> {
        todo!("walk three Sv39 levels and roll back partial allocations")
    }

    pub fn translate(
        &self,
        virtual_address: u64,
        access: Access,
        user: bool,
    ) -> Result<u64, TranslateError> {
        todo!("walk to a leaf, check permissions, and preserve the offset")
    }

    pub fn unmap(
        &mut self,
        allocator: &mut FrameAllocator,
        virtual_address: u64,
    ) -> Result<Mapping, UnmapError> {
        todo!("remove a leaf and reclaim empty table frames bottom-up")
    }

    pub fn validate(&self) -> Result<(), MemoryInvariant> {
        todo!("prove all table frames are reachable and entries are well formed")
    }
}
