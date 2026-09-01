use rvkernel_model::process::{Pid, ProcessError, ProcessState, ProcessTable};

#[test]
fn process_round_robin_and_lifecycle() {
    let mut table = ProcessTable::new();
    let p1 = table.spawn().unwrap();
    let p2 = table.spawn().unwrap();
    let p3 = table.spawn().unwrap();

    assert_eq!((p1, p2, p3), (Pid(1), Pid(2), Pid(3)));
    assert_eq!(table.ready_order(), vec![p1, p2, p3]);
    assert_eq!(table.schedule(), Some(p1));
    assert_eq!(table.state(p1), Some(ProcessState::Running));

    assert_eq!(table.schedule(), Some(p2));
    assert_eq!(table.ready_order(), vec![p3, p1]);
    assert_eq!(table.block_current(), Ok(p2));
    assert_eq!(table.state(p2), Some(ProcessState::Blocked));

    assert_eq!(table.schedule(), Some(p3));
    assert_eq!(table.wake(p2), Ok(()));
    assert_eq!(table.ready_order(), vec![p1, p2]);
    assert_eq!(table.exit_current(-7), Ok(p3));
    assert_eq!(table.state(p3), Some(ProcessState::Exited(-7)));

    assert_eq!(table.schedule(), Some(p1));
    assert_eq!(table.validate(), Ok(()));
}

#[test]
fn process_invalid_transitions_are_rejected() {
    let mut table = ProcessTable::new();
    assert_eq!(table.block_current(), Err(ProcessError::NoCurrent));
    assert_eq!(table.exit_current(0), Err(ProcessError::NoCurrent));
    assert_eq!(table.wake(Pid(99)), Err(ProcessError::NoSuchProcess(Pid(99))));

    let pid = table.spawn().unwrap();
    assert_eq!(table.wake(pid), Err(ProcessError::NotBlocked(pid)));
    assert_eq!(table.ready_order(), vec![pid]);
    assert_eq!(table.validate(), Ok(()));
}
