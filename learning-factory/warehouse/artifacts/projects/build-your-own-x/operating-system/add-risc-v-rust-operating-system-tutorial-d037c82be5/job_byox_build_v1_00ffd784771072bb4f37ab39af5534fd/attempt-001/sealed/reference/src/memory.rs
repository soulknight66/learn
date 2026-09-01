use std::collections::{BTreeMap, BTreeSet};
use std::ops::{BitAnd, BitAndAssign, BitOr, BitOrAssign};

pub const PAGE_SIZE: u64 = 4096;
const ENTRY_COUNT: usize = 512;
const PTE_PPN_SHIFT: u32 = 10;
const PTE_FLAG_MASK: u64 = 0xff;
const PTE_RESERVED_MASK: u64 = 0xffc0_0000_0000_0000;
const PTE_RSW_MASK: u64 = 0x300;
const MAX_PPN: u64 = (1u64 << 44) - 1;

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
        let end = first.checked_add(count).ok_or(FrameError::RangeOverflow)?;
        let free = (first..end).map(Frame).collect();
        Ok(Self {
            first,
            end,
            free,
            allocated: BTreeSet::new(),
        })
    }

    pub fn allocate(&mut self) -> Result<Frame, FrameError> {
        let frame = self
            .free
            .iter()
            .next()
            .copied()
            .ok_or(FrameError::OutOfFrames)?;
        self.free.remove(&frame);
        self.allocated.insert(frame);
        Ok(frame)
    }

    pub fn deallocate(&mut self, frame: Frame) -> Result<(), FrameError> {
        if !self.owns(frame) {
            return Err(FrameError::ForeignFrame(frame));
        }
        if !self.allocated.remove(&frame) {
            return Err(FrameError::NotAllocated(frame));
        }
        self.free.insert(frame);
        Ok(())
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

    fn preflight_deallocate(&self, frame: Frame) -> Result<(), FrameError> {
        if !self.owns(frame) {
            return Err(FrameError::ForeignFrame(frame));
        }
        if !self.allocated.contains(&frame) {
            return Err(FrameError::NotAllocated(frame));
        }
        Ok(())
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
    tables: BTreeMap<Frame, Box<[u64; ENTRY_COUNT]>>,
}

impl Sv39 {
    pub fn new(allocator: &mut FrameAllocator) -> Result<Self, FrameError> {
        let root = allocator.allocate()?;
        let mut tables = BTreeMap::new();
        tables.insert(root, Box::new([0; ENTRY_COUNT]));
        Ok(Self { root, tables })
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
        if !is_canonical(virtual_address) {
            return Err(MapError::NonCanonical);
        }
        if virtual_address % PAGE_SIZE != 0 {
            return Err(MapError::UnalignedVirtual);
        }
        if physical_address % PAGE_SIZE != 0 {
            return Err(MapError::UnalignedPhysical);
        }
        let data_frame = Frame(physical_address / PAGE_SIZE);
        if data_frame.0 > MAX_PPN {
            return Err(MapError::PhysicalAddressTooWide);
        }
        if !valid_leaf_flags(flags) {
            return Err(MapError::InvalidFlags);
        }
        if self
            .tables
            .keys()
            .any(|frame| allocator.preflight_deallocate(*frame).is_err())
        {
            return Err(MapError::CorruptPageTable);
        }

        let indices = vpn_indices(virtual_address);
        let mut current = self.root;
        let mut seen = BTreeSet::from([self.root]);
        let mut created: Vec<(Frame, usize, Frame)> = Vec::new();

        for index in indices.into_iter().take(2) {
            let entry = match self.tables.get(&current) {
                Some(table) => table[index],
                None => {
                    self.rollback_created(allocator, &created);
                    return Err(MapError::CorruptPageTable);
                }
            };

            if entry == 0 {
                let child = match allocator.allocate() {
                    Ok(frame) => frame,
                    Err(FrameError::OutOfFrames) => {
                        self.rollback_created(allocator, &created);
                        return Err(MapError::OutOfFrames);
                    }
                    Err(_) => {
                        self.rollback_created(allocator, &created);
                        return Err(MapError::CorruptPageTable);
                    }
                };
                if child.0 > MAX_PPN || self.tables.contains_key(&child) {
                    let _ = allocator.deallocate(child);
                    self.rollback_created(allocator, &created);
                    return Err(MapError::CorruptPageTable);
                }
                self.tables.insert(child, Box::new([0; ENTRY_COUNT]));
                if let Some(parent) = self.tables.get_mut(&current) {
                    parent[index] = encode_entry(child, PteFlags::VALID);
                } else {
                    self.tables.remove(&child);
                    let _ = allocator.deallocate(child);
                    self.rollback_created(allocator, &created);
                    return Err(MapError::CorruptPageTable);
                }
                created.push((current, index, child));
                seen.insert(child);
                current = child;
            } else {
                let child = match decode_intermediate(entry) {
                    Some(frame) if self.tables.contains_key(&frame) && seen.insert(frame) => frame,
                    _ => {
                        self.rollback_created(allocator, &created);
                        return Err(MapError::CorruptPageTable);
                    }
                };
                current = child;
            }
        }

        let leaf_index = indices[2];
        let old_entry = match self.tables.get(&current) {
            Some(table) => table[leaf_index],
            None => {
                self.rollback_created(allocator, &created);
                return Err(MapError::CorruptPageTable);
            }
        };
        if old_entry != 0 {
            let result = if decode_leaf(old_entry).is_some() {
                MapError::AlreadyMapped
            } else {
                MapError::CorruptPageTable
            };
            self.rollback_created(allocator, &created);
            return Err(result);
        }

        if let Some(table) = self.tables.get_mut(&current) {
            table[leaf_index] = encode_entry(data_frame, flags);
            Ok(())
        } else {
            self.rollback_created(allocator, &created);
            Err(MapError::CorruptPageTable)
        }
    }

    pub fn translate(
        &self,
        virtual_address: u64,
        access: Access,
        user: bool,
    ) -> Result<u64, TranslateError> {
        if !is_canonical(virtual_address) {
            return Err(TranslateError::NonCanonical);
        }
        let indices = vpn_indices(virtual_address);
        let mut current = self.root;
        let mut seen = BTreeSet::from([self.root]);
        for index in indices.into_iter().take(2) {
            let table = self
                .tables
                .get(&current)
                .ok_or(TranslateError::CorruptPageTable)?;
            let entry = table[index];
            if entry == 0 {
                return Err(TranslateError::NotMapped);
            }
            let child = decode_intermediate(entry).ok_or(TranslateError::CorruptPageTable)?;
            if !seen.insert(child) || !self.tables.contains_key(&child) {
                return Err(TranslateError::CorruptPageTable);
            }
            current = child;
        }

        let table = self
            .tables
            .get(&current)
            .ok_or(TranslateError::CorruptPageTable)?;
        let entry = table[indices[2]];
        if entry == 0 {
            return Err(TranslateError::NotMapped);
        }
        let mapping = decode_leaf(entry).ok_or(TranslateError::CorruptPageTable)?;
        let required = match access {
            Access::Read => PteFlags::READ,
            Access::Write => PteFlags::WRITE,
            Access::Execute => PteFlags::EXECUTE,
        };
        if !mapping.flags.contains(required)
            || (user && !mapping.flags.contains(PteFlags::USER))
        {
            return Err(TranslateError::PermissionDenied);
        }
        Ok((mapping.frame.0 << 12) | (virtual_address & (PAGE_SIZE - 1)))
    }

    pub fn unmap(
        &mut self,
        allocator: &mut FrameAllocator,
        virtual_address: u64,
    ) -> Result<Mapping, UnmapError> {
        if !is_canonical(virtual_address) {
            return Err(UnmapError::NonCanonical);
        }
        if virtual_address % PAGE_SIZE != 0 {
            return Err(UnmapError::UnalignedVirtual);
        }
        for frame in self.tables.keys() {
            allocator
                .preflight_deallocate(*frame)
                .map_err(UnmapError::Allocator)?;
        }

        let indices = vpn_indices(virtual_address);
        let mut current = self.root;
        let mut seen = BTreeSet::from([self.root]);
        let mut edges: Vec<(Frame, usize, Frame)> = Vec::new();
        for index in indices.into_iter().take(2) {
            let table = self
                .tables
                .get(&current)
                .ok_or(UnmapError::CorruptPageTable)?;
            let entry = table[index];
            if entry == 0 {
                return Err(UnmapError::NotMapped);
            }
            let child = decode_intermediate(entry).ok_or(UnmapError::CorruptPageTable)?;
            if !seen.insert(child) || !self.tables.contains_key(&child) {
                return Err(UnmapError::CorruptPageTable);
            }
            edges.push((current, index, child));
            current = child;
        }

        let leaf_index = indices[2];
        let leaf_table = self
            .tables
            .get(&current)
            .ok_or(UnmapError::CorruptPageTable)?;
        let leaf_entry = leaf_table[leaf_index];
        if leaf_entry == 0 {
            return Err(UnmapError::NotMapped);
        }
        let mapping = decode_leaf(leaf_entry).ok_or(UnmapError::CorruptPageTable)?;

        let mut reclaim = BTreeSet::new();
        if table_empty_except(leaf_table, leaf_index) {
            reclaim.insert(current);
            let (parent, parent_index, _) = edges[1];
            let parent_table = self
                .tables
                .get(&parent)
                .ok_or(UnmapError::CorruptPageTable)?;
            if table_empty_except(parent_table, parent_index) {
                reclaim.insert(parent);
            }
        }
        for frame in &reclaim {
            allocator
                .preflight_deallocate(*frame)
                .map_err(UnmapError::Allocator)?;
        }

        self.tables
            .get_mut(&current)
            .expect("walked leaf table remains present")
            [leaf_index] = 0;
        for (parent, index, child) in edges.into_iter().rev() {
            if reclaim.contains(&child) {
                self.tables.remove(&child);
                self.tables
                    .get_mut(&parent)
                    .expect("walked parent table remains present")[index] = 0;
                allocator
                    .deallocate(child)
                    .expect("deallocation was preflighted");
            }
        }
        Ok(mapping)
    }

    pub fn validate(&self) -> Result<(), MemoryInvariant> {
        if !self.tables.contains_key(&self.root) {
            return Err(MemoryInvariant::MissingRoot);
        }
        let mut visited = BTreeSet::from([self.root]);
        let mut pending = vec![(self.root, 2u8)];
        while let Some((frame, level)) = pending.pop() {
            let table = self
                .tables
                .get(&frame)
                .ok_or(MemoryInvariant::UnknownTable(frame))?;
            for entry in table.iter().copied().filter(|entry| *entry != 0) {
                if level == 0 {
                    if decode_leaf(entry).is_none() {
                        return Err(MemoryInvariant::InvalidLeaf);
                    }
                    continue;
                }
                let child = decode_intermediate(entry)
                    .ok_or(MemoryInvariant::InvalidIntermediate)?;
                if !self.tables.contains_key(&child) {
                    return Err(MemoryInvariant::UnknownTable(child));
                }
                if !visited.insert(child) {
                    return Err(MemoryInvariant::InvalidIntermediate);
                }
                pending.push((child, level - 1));
            }
        }
        if let Some(frame) = self.tables.keys().find(|frame| !visited.contains(frame)) {
            return Err(MemoryInvariant::UnreachableTable(*frame));
        }
        Ok(())
    }

    fn rollback_created(
        &mut self,
        allocator: &mut FrameAllocator,
        created: &[(Frame, usize, Frame)],
    ) {
        for (parent, index, child) in created.iter().rev().copied() {
            if let Some(table) = self.tables.get_mut(&parent) {
                table[index] = 0;
            }
            self.tables.remove(&child);
            let result = allocator.deallocate(child);
            debug_assert!(result.is_ok());
        }
    }
}

fn is_canonical(address: u64) -> bool {
    let sign = (address >> 38) & 1;
    let upper = address >> 39;
    if sign == 0 {
        upper == 0
    } else {
        upper == (1u64 << 25) - 1
    }
}

fn vpn_indices(address: u64) -> [usize; 3] {
    [
        ((address >> 30) & 0x1ff) as usize,
        ((address >> 21) & 0x1ff) as usize,
        ((address >> 12) & 0x1ff) as usize,
    ]
}

fn encode_entry(frame: Frame, flags: PteFlags) -> u64 {
    (frame.0 << PTE_PPN_SHIFT) | u64::from(flags.bits())
}

fn entry_flags(entry: u64) -> PteFlags {
    PteFlags::from_bits((entry & PTE_FLAG_MASK) as u16)
        .expect("the PTE mask permits only defined flag bits")
}

fn entry_frame(entry: u64) -> Option<Frame> {
    if entry & (PTE_RESERVED_MASK | PTE_RSW_MASK) != 0 {
        None
    } else {
        Some(Frame((entry >> PTE_PPN_SHIFT) & MAX_PPN))
    }
}

fn valid_leaf_flags(flags: PteFlags) -> bool {
    flags.contains(PteFlags::VALID)
        && flags.intersects(PteFlags::READ | PteFlags::WRITE | PteFlags::EXECUTE)
        && (!flags.contains(PteFlags::WRITE) || flags.contains(PteFlags::READ))
}

fn decode_intermediate(entry: u64) -> Option<Frame> {
    if entry_flags(entry) != PteFlags::VALID {
        return None;
    }
    entry_frame(entry)
}

fn decode_leaf(entry: u64) -> Option<Mapping> {
    let flags = entry_flags(entry);
    if !valid_leaf_flags(flags) {
        return None;
    }
    Some(Mapping {
        frame: entry_frame(entry)?,
        flags,
    })
}

fn table_empty_except(table: &[u64; ENTRY_COUNT], ignored_index: usize) -> bool {
    table
        .iter()
        .enumerate()
        .all(|(index, entry)| index == ignored_index || *entry == 0)
}

#[cfg(test)]
mod internal_tests {
    use super::*;

    #[test]
    fn validator_rejects_a_leaf_at_an_intermediate_level() {
        let mut allocator = FrameAllocator::new(1, 1).unwrap();
        let mut table = Sv39::new(&mut allocator).unwrap();
        table.tables.get_mut(&table.root).unwrap()[0] =
            encode_entry(Frame(8), PteFlags::VALID | PteFlags::READ);
        assert_eq!(
            table.validate(),
            Err(MemoryInvariant::InvalidIntermediate)
        );
    }

    #[test]
    fn validator_rejects_an_unreachable_table() {
        let mut allocator = FrameAllocator::new(10, 1).unwrap();
        let mut table = Sv39::new(&mut allocator).unwrap();
        table.tables.insert(Frame(99), Box::new([0; ENTRY_COUNT]));
        assert_eq!(
            table.validate(),
            Err(MemoryInvariant::UnreachableTable(Frame(99)))
        );
    }
}
