use rvkernel_model::fs::{FileSystem, FsError, NodeKind, PathError};

#[test]
fn fs_create_write_read_list_and_remove() {
    let mut fs = FileSystem::new(64);
    let etc = fs.mkdir("/etc").unwrap();
    let cfg = fs.create_file("/etc/config").unwrap();
    assert_ne!(etc, cfg);

    fs.write("/etc/config", 3, b"rv").unwrap();
    assert_eq!(
        fs.read("/etc/config", 0, 10).unwrap(),
        vec![0, 0, 0, b'r', b'v']
    );
    assert_eq!(fs.file_len("/etc/config"), Ok(5));
    assert_eq!(fs.kind("/etc"), Ok(NodeKind::Directory));

    let entries = fs.list("/etc").unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].name, "config");
    assert_eq!(entries[0].inode, cfg);
    assert_eq!(entries[0].kind, NodeKind::File);

    assert_eq!(fs.remove("/etc/config"), Ok(cfg));
    assert_eq!(fs.remove("/etc"), Ok(etc));
    assert_eq!(fs.inode_count(), 1);
    assert_eq!(fs.validate(), Ok(()));
}

#[test]
fn fs_listing_is_lexical_and_failures_do_not_mutate() {
    let mut fs = FileSystem::new(8);
    fs.create_file("/z").unwrap();
    fs.mkdir("/a").unwrap();

    let names: Vec<_> = fs.list("/").unwrap().into_iter().map(|e| e.name).collect();
    assert_eq!(names, vec!["a", "z"]);

    let before = fs.inode_count();
    assert_eq!(fs.create_file("/a/missing/x"), Err(FsError::NotFound));
    assert_eq!(fs.inode_count(), before);
    assert_eq!(
        fs.create_file("/bad//name"),
        Err(FsError::InvalidPath(PathError::RepeatedSeparator))
    );
    assert_eq!(fs.inode_count(), before);
    assert_eq!(fs.validate(), Ok(()));
}
