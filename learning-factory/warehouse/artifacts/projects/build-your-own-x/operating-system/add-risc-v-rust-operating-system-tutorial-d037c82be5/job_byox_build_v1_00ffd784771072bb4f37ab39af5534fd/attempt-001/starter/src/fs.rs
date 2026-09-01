use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct Inode(pub u64);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NodeKind {
    File,
    Directory,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirEntry {
    pub name: String,
    pub inode: Inode,
    pub kind: NodeKind,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PathError {
    Empty,
    Relative,
    RepeatedSeparator,
    TrailingSeparator,
    DotComponent,
    ParentComponent,
    Nul,
    ComponentTooLong,
    RootHasNoName,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum FsError {
    InvalidPath(PathError),
    NotFound,
    NotDirectory,
    NotFile,
    AlreadyExists,
    DirectoryNotEmpty,
    CannotRemoveRoot,
    InodeExhausted,
    FileTooLarge,
    RangeOverflow,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum FsInvariant {
    MissingRoot,
    RootNotDirectory,
    DanglingEntry { parent: Inode, child: Inode },
    KindMismatch { parent: Inode, child: Inode },
    DuplicateReachability(Inode),
    Cycle(Inode),
    Orphan(Inode),
    OversizedFile(Inode),
}

#[derive(Clone, Debug)]
enum Node {
    File(Vec<u8>),
    Directory(BTreeMap<String, Inode>),
}

#[derive(Clone, Debug)]
pub struct FileSystem {
    nodes: BTreeMap<Inode, Node>,
    next_inode: Option<u64>,
    max_file_size: usize,
}

impl FileSystem {
    pub fn new(max_file_size: usize) -> Self {
        todo!("create inode 1 as the empty root directory")
    }

    pub fn root(&self) -> Inode {
        Inode(1)
    }

    pub fn resolve(&self, path: &str) -> Result<Inode, FsError> {
        todo!("validate and resolve an absolute path from root")
    }

    pub fn mkdir(&mut self, path: &str) -> Result<Inode, FsError> {
        todo!("atomically add an empty directory")
    }

    pub fn create_file(&mut self, path: &str) -> Result<Inode, FsError> {
        todo!("atomically add an empty file")
    }

    pub fn write(&mut self, path: &str, offset: usize, data: &[u8]) -> Result<(), FsError> {
        todo!("extend with zeroes as needed, then copy data")
    }

    pub fn read(&self, path: &str, offset: usize, len: usize) -> Result<Vec<u8>, FsError> {
        todo!("return the requested file range without crossing EOF")
    }

    pub fn list(&self, path: &str) -> Result<Vec<DirEntry>, FsError> {
        todo!("return immediate children in bytewise lexical order")
    }

    pub fn remove(&mut self, path: &str) -> Result<Inode, FsError> {
        todo!("atomically remove a file or empty non-root directory")
    }

    pub fn kind(&self, path: &str) -> Result<NodeKind, FsError> {
        todo!("resolve a path and report its node kind")
    }

    pub fn file_len(&self, path: &str) -> Result<usize, FsError> {
        todo!("resolve a file and report its byte length")
    }

    pub fn inode_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn validate(&self) -> Result<(), FsInvariant> {
        todo!("walk the inode tree and reject dangling, duplicate, or orphan nodes")
    }
}
