use std::collections::{BTreeMap, BTreeSet};

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
    Directory(BTreeMap<String, (Inode, NodeKind)>),
}

impl Node {
    fn kind(&self) -> NodeKind {
        match self {
            Self::File(_) => NodeKind::File,
            Self::Directory(_) => NodeKind::Directory,
        }
    }
}

#[derive(Clone, Debug)]
pub struct FileSystem {
    nodes: BTreeMap<Inode, Node>,
    next_inode: Option<u64>,
    max_file_size: usize,
}

impl FileSystem {
    pub fn new(max_file_size: usize) -> Self {
        let mut nodes = BTreeMap::new();
        nodes.insert(Inode(1), Node::Directory(BTreeMap::new()));
        Self {
            nodes,
            next_inode: Some(2),
            max_file_size,
        }
    }

    pub fn root(&self) -> Inode {
        Inode(1)
    }

    pub fn resolve(&self, path: &str) -> Result<Inode, FsError> {
        let components = parse_path(path)?;
        self.resolve_components(&components)
    }

    pub fn mkdir(&mut self, path: &str) -> Result<Inode, FsError> {
        self.create_node(path, NodeKind::Directory)
    }

    pub fn create_file(&mut self, path: &str) -> Result<Inode, FsError> {
        self.create_node(path, NodeKind::File)
    }

    pub fn write(&mut self, path: &str, offset: usize, data: &[u8]) -> Result<(), FsError> {
        let inode = self.resolve(path)?;
        let node = self.nodes.get(&inode).ok_or(FsError::NotFound)?;
        if !matches!(node, Node::File(_)) {
            return Err(FsError::NotFile);
        }
        let end = offset
            .checked_add(data.len())
            .ok_or(FsError::RangeOverflow)?;
        if end > self.max_file_size {
            return Err(FsError::FileTooLarge);
        }

        let file = match self.nodes.get_mut(&inode) {
            Some(Node::File(file)) => file,
            _ => unreachable!("file kind was checked before mutation"),
        };
        if file.len() < end {
            file.resize(end, 0);
        }
        file[offset..end].copy_from_slice(data);
        Ok(())
    }

    pub fn read(&self, path: &str, offset: usize, len: usize) -> Result<Vec<u8>, FsError> {
        let inode = self.resolve(path)?;
        let file = match self.nodes.get(&inode) {
            Some(Node::File(file)) => file,
            Some(Node::Directory(_)) => return Err(FsError::NotFile),
            None => return Err(FsError::NotFound),
        };
        let requested_end = offset.checked_add(len).ok_or(FsError::RangeOverflow)?;
        if offset >= file.len() {
            return Ok(Vec::new());
        }
        let end = requested_end.min(file.len());
        Ok(file[offset..end].to_vec())
    }

    pub fn list(&self, path: &str) -> Result<Vec<DirEntry>, FsError> {
        let inode = self.resolve(path)?;
        let entries = match self.nodes.get(&inode) {
            Some(Node::Directory(entries)) => entries,
            Some(Node::File(_)) => return Err(FsError::NotDirectory),
            None => return Err(FsError::NotFound),
        };
        entries
            .iter()
            .map(|(name, (child, cached_kind))| {
                let node = self.nodes.get(child).ok_or(FsError::NotFound)?;
                debug_assert_eq!(node.kind(), *cached_kind);
                Ok(DirEntry {
                    name: name.clone(),
                    inode: *child,
                    kind: node.kind(),
                })
            })
            .collect()
    }

    pub fn remove(&mut self, path: &str) -> Result<Inode, FsError> {
        let components = parse_path(path)?;
        if components.is_empty() {
            return Err(FsError::CannotRemoveRoot);
        }
        let name = components[components.len() - 1];
        let parent = self.resolve_components(&components[..components.len() - 1])?;
        let child = match self.nodes.get(&parent) {
            Some(Node::Directory(entries)) => entries
                .get(name)
                .map(|(inode, _)| *inode)
                .ok_or(FsError::NotFound)?,
            Some(Node::File(_)) => return Err(FsError::NotDirectory),
            None => return Err(FsError::NotFound),
        };
        match self.nodes.get(&child) {
            Some(Node::Directory(entries)) if !entries.is_empty() => {
                return Err(FsError::DirectoryNotEmpty)
            }
            Some(_) => {}
            None => return Err(FsError::NotFound),
        }

        match self.nodes.get_mut(&parent) {
            Some(Node::Directory(entries)) => {
                entries.remove(name);
            }
            _ => unreachable!("parent directory was checked before mutation"),
        }
        self.nodes.remove(&child);
        Ok(child)
    }

    pub fn kind(&self, path: &str) -> Result<NodeKind, FsError> {
        let inode = self.resolve(path)?;
        self.nodes
            .get(&inode)
            .map(Node::kind)
            .ok_or(FsError::NotFound)
    }

    pub fn file_len(&self, path: &str) -> Result<usize, FsError> {
        let inode = self.resolve(path)?;
        match self.nodes.get(&inode) {
            Some(Node::File(file)) => Ok(file.len()),
            Some(Node::Directory(_)) => Err(FsError::NotFile),
            None => Err(FsError::NotFound),
        }
    }

    pub fn inode_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn validate(&self) -> Result<(), FsInvariant> {
        let root = self.nodes.get(&Inode(1)).ok_or(FsInvariant::MissingRoot)?;
        if !matches!(root, Node::Directory(_)) {
            return Err(FsInvariant::RootNotDirectory);
        }
        let mut visited = BTreeSet::new();
        let mut active = BTreeSet::new();
        validate_node(
            Inode(1),
            &self.nodes,
            self.max_file_size,
            &mut visited,
            &mut active,
        )?;
        if let Some(inode) = self.nodes.keys().find(|inode| !visited.contains(inode)) {
            return Err(FsInvariant::Orphan(*inode));
        }
        Ok(())
    }

    fn resolve_components(&self, components: &[&str]) -> Result<Inode, FsError> {
        let mut current = Inode(1);
        for component in components {
            let entries = match self.nodes.get(&current) {
                Some(Node::Directory(entries)) => entries,
                Some(Node::File(_)) => return Err(FsError::NotDirectory),
                None => return Err(FsError::NotFound),
            };
            current = entries
                .get(*component)
                .map(|(inode, _)| *inode)
                .ok_or(FsError::NotFound)?;
        }
        Ok(current)
    }

    fn create_node(&mut self, path: &str, kind: NodeKind) -> Result<Inode, FsError> {
        let components = parse_path(path)?;
        if components.is_empty() {
            return Err(FsError::InvalidPath(PathError::RootHasNoName));
        }
        let name = components[components.len() - 1];
        let parent = self.resolve_components(&components[..components.len() - 1])?;
        match self.nodes.get(&parent) {
            Some(Node::Directory(entries)) if entries.contains_key(name) => {
                return Err(FsError::AlreadyExists)
            }
            Some(Node::Directory(_)) => {}
            Some(Node::File(_)) => return Err(FsError::NotDirectory),
            None => return Err(FsError::NotFound),
        }

        let raw = self.next_inode.ok_or(FsError::InodeExhausted)?;
        let inode = Inode(raw);
        let next = raw.checked_add(1);
        let node = match kind {
            NodeKind::File => Node::File(Vec::new()),
            NodeKind::Directory => Node::Directory(BTreeMap::new()),
        };

        self.nodes.insert(inode, node);
        match self.nodes.get_mut(&parent) {
            Some(Node::Directory(entries)) => {
                entries.insert(name.to_owned(), (inode, kind));
            }
            _ => unreachable!("parent directory was checked before publication"),
        }
        self.next_inode = next;
        Ok(inode)
    }
}

fn parse_path(path: &str) -> Result<Vec<&str>, FsError> {
    if path.is_empty() {
        return Err(FsError::InvalidPath(PathError::Empty));
    }
    if !path.starts_with('/') {
        return Err(FsError::InvalidPath(PathError::Relative));
    }
    if path == "/" {
        return Ok(Vec::new());
    }
    if path.ends_with('/') {
        return Err(FsError::InvalidPath(PathError::TrailingSeparator));
    }

    let mut components = Vec::new();
    for component in path[1..].split('/') {
        if component.is_empty() {
            return Err(FsError::InvalidPath(PathError::RepeatedSeparator));
        }
        if component == "." {
            return Err(FsError::InvalidPath(PathError::DotComponent));
        }
        if component == ".." {
            return Err(FsError::InvalidPath(PathError::ParentComponent));
        }
        if component.as_bytes().contains(&0) {
            return Err(FsError::InvalidPath(PathError::Nul));
        }
        if component.len() > 255 {
            return Err(FsError::InvalidPath(PathError::ComponentTooLong));
        }
        components.push(component);
    }
    Ok(components)
}

fn validate_node(
    inode: Inode,
    nodes: &BTreeMap<Inode, Node>,
    max_file_size: usize,
    visited: &mut BTreeSet<Inode>,
    active: &mut BTreeSet<Inode>,
) -> Result<(), FsInvariant> {
    if active.contains(&inode) {
        return Err(FsInvariant::Cycle(inode));
    }
    if !visited.insert(inode) {
        return Err(FsInvariant::DuplicateReachability(inode));
    }
    active.insert(inode);

    let node = nodes.get(&inode).ok_or(FsInvariant::DanglingEntry {
        parent: inode,
        child: inode,
    })?;
    match node {
        Node::File(data) => {
            if data.len() > max_file_size {
                return Err(FsInvariant::OversizedFile(inode));
            }
        }
        Node::Directory(entries) => {
            for (child, cached_kind) in entries.values() {
                let child_node = nodes.get(child).ok_or(FsInvariant::DanglingEntry {
                    parent: inode,
                    child: *child,
                })?;
                if child_node.kind() != *cached_kind {
                    return Err(FsInvariant::KindMismatch {
                        parent: inode,
                        child: *child,
                    });
                }
                validate_node(*child, nodes, max_file_size, visited, active)?;
            }
        }
    }
    active.remove(&inode);
    Ok(())
}

#[cfg(test)]
mod internal_tests {
    use super::*;

    #[test]
    fn validator_detects_cached_kind_mismatch() {
        let mut fs = FileSystem::new(16);
        let file = fs.create_file("/f").unwrap();
        let root = match fs.nodes.get_mut(&Inode(1)).unwrap() {
            Node::Directory(entries) => entries,
            Node::File(_) => unreachable!(),
        };
        root.insert("f".to_owned(), (file, NodeKind::Directory));
        assert_eq!(
            fs.validate(),
            Err(FsInvariant::KindMismatch {
                parent: Inode(1),
                child: file,
            })
        );
    }

    #[test]
    fn validator_detects_an_orphan() {
        let mut fs = FileSystem::new(16);
        fs.nodes.insert(Inode(9), Node::File(Vec::new()));
        assert_eq!(fs.validate(), Err(FsInvariant::Orphan(Inode(9))));
    }
}
