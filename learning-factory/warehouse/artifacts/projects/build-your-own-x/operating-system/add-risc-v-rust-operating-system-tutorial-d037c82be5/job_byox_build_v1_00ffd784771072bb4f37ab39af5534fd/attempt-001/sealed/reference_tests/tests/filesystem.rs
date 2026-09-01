use rvkernel_model::fs::{FileSystem, FsError, NodeKind, PathError};

#[test]
fn root_and_path_grammar_are_explicit() {
    let mut fs = FileSystem::new(32);
    assert_eq!(fs.root().0, 1);
    assert_eq!(fs.resolve("/"), Ok(fs.root()));
    assert_eq!(fs.kind("/"), Ok(NodeKind::Directory));
    assert_eq!(
        fs.create_file("/"),
        Err(FsError::InvalidPath(PathError::RootHasNoName))
    );
    assert_eq!(fs.remove("/"), Err(FsError::CannotRemoveRoot));

    let cases = [
        ("", PathError::Empty),
        ("relative", PathError::Relative),
        ("/trailing/", PathError::TrailingSeparator),
        ("/two//parts", PathError::RepeatedSeparator),
        ("/./x", PathError::DotComponent),
        ("/../x", PathError::ParentComponent),
        ("/nul\0x", PathError::Nul),
    ];
    for (path, error) in cases {
        assert_eq!(fs.resolve(path), Err(FsError::InvalidPath(error)));
    }
    let long = format!("/{}", "x".repeat(256));
    assert_eq!(
        fs.resolve(&long),
        Err(FsError::InvalidPath(PathError::ComponentTooLong))
    );
    assert_eq!(fs.inode_count(), 1);
    assert_eq!(fs.validate(), Ok(()));
}

#[test]
fn file_holes_limits_and_range_overflow_are_deterministic() {
    let mut fs = FileSystem::new(8);
    fs.create_file("/f").unwrap();
    fs.write("/f", 3, b"xy").unwrap();
    assert_eq!(fs.read("/f", 0, 20).unwrap(), vec![0, 0, 0, b'x', b'y']);
    assert_eq!(fs.read("/f", 5, 0).unwrap(), Vec::<u8>::new());
    assert_eq!(fs.read("/f", 99, 1).unwrap(), Vec::<u8>::new());
    assert_eq!(
        fs.read("/f", usize::MAX, 1),
        Err(FsError::RangeOverflow)
    );

    let before = fs.read("/f", 0, 8).unwrap();
    assert_eq!(fs.write("/f", 8, b"x"), Err(FsError::FileTooLarge));
    assert_eq!(
        fs.write("/f", usize::MAX, b"x"),
        Err(FsError::RangeOverflow)
    );
    assert_eq!(fs.read("/f", 0, 8).unwrap(), before);
    assert_eq!(fs.validate(), Ok(()));
}

#[test]
fn directory_operations_are_typed_atomic_and_lexical() {
    let mut fs = FileSystem::new(128);
    let dir = fs.mkdir("/d").unwrap();
    let z = fs.create_file("/d/z").unwrap();
    let a = fs.mkdir("/d/a").unwrap();
    assert_eq!(fs.create_file("/d/z"), Err(FsError::AlreadyExists));
    assert_eq!(fs.create_file("/d/z/x"), Err(FsError::NotDirectory));
    assert_eq!(fs.remove("/d"), Err(FsError::DirectoryNotEmpty));

    let entries = fs.list("/d").unwrap();
    assert_eq!(entries.iter().map(|e| e.name.as_str()).collect::<Vec<_>>(), vec!["a", "z"]);
    assert_eq!(entries[0].inode, a);
    assert_eq!(entries[0].kind, NodeKind::Directory);
    assert_eq!(entries[1].inode, z);
    assert_eq!(entries[1].kind, NodeKind::File);

    assert_eq!(fs.remove("/d/a"), Ok(a));
    assert_eq!(fs.remove("/d/z"), Ok(z));
    assert_eq!(fs.remove("/d"), Ok(dir));
    assert_eq!(fs.inode_count(), 1);
    assert_eq!(fs.validate(), Ok(()));
}

#[test]
fn inode_numbers_are_monotonic_after_removal() {
    let mut fs = FileSystem::new(4);
    let first = fs.create_file("/first").unwrap();
    fs.remove("/first").unwrap();
    let second = fs.create_file("/second").unwrap();
    assert!(second.0 > first.0);
    assert_eq!(fs.validate(), Ok(()));
}
