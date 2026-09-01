use rvkernel_model::process::{Pid, ProcessError, ProcessState, ProcessTable};

#[test]
fn idle_and_single_process_scheduling_are_consistent() {
    let mut table = ProcessTable::new();
    assert_eq!(table.schedule(), None);
    assert!(table.is_empty());

    let only = table.spawn().unwrap();
    for _ in 0..8 {
        assert_eq!(table.schedule(), Some(only));
        assert_eq!(table.current(), Some(only));
        assert_eq!(table.ready_order(), Vec::<Pid>::new());
        assert_eq!(table.validate(), Ok(()));
    }
}

#[test]
fn blocked_and_exited_processes_never_run() {
    let mut table = ProcessTable::new();
    let first = table.spawn().unwrap();
    let second = table.spawn().unwrap();
    let third = table.spawn().unwrap();

    assert_eq!(table.schedule(), Some(first));
    assert_eq!(table.block_current(), Ok(first));
    assert_eq!(table.schedule(), Some(second));
    assert_eq!(table.exit_current(42), Ok(second));
    assert_eq!(table.schedule(), Some(third));
    assert_eq!(table.schedule(), Some(third));
    assert_eq!(table.state(first), Some(ProcessState::Blocked));
    assert_eq!(table.state(second), Some(ProcessState::Exited(42)));

    assert_eq!(table.wake(first), Ok(()));
    assert_eq!(table.schedule(), Some(first));
    assert_eq!(table.wake(first), Err(ProcessError::NotBlocked(first)));
    assert_eq!(table.ready_order(), vec![third]);
    assert_eq!(table.validate(), Ok(()));
}

#[test]
fn invalid_operations_preserve_the_ready_queue() {
    let mut table = ProcessTable::new();
    let pid = table.spawn().unwrap();
    let before = table.ready_order();
    assert_eq!(table.wake(Pid(0)), Err(ProcessError::NoSuchProcess(Pid(0))));
    assert_eq!(table.wake(pid), Err(ProcessError::NotBlocked(pid)));
    assert_eq!(table.ready_order(), before);
    assert_eq!(table.validate(), Ok(()));
}
