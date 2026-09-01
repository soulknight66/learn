use std::collections::{BTreeMap, VecDeque};

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct Pid(pub u32);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProcessState {
    Ready,
    Running,
    Blocked,
    Exited(i32),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProcessError {
    PidExhausted,
    NoCurrent,
    NoSuchProcess(Pid),
    NotBlocked(Pid),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProcessInvariant {
    CurrentMissing(Pid),
    CurrentNotRunning(Pid),
    MultipleRunning,
    RunningWithoutCurrent(Pid),
    QueueMissingProcess(Pid),
    QueueContainsNonReady(Pid),
    DuplicateQueueEntry(Pid),
    ReadyMissingFromQueue(Pid),
}

#[derive(Clone, Debug)]
pub struct ProcessTable {
    next_pid: Option<u32>,
    processes: BTreeMap<Pid, ProcessState>,
    ready: VecDeque<Pid>,
    current: Option<Pid>,
}

impl Default for ProcessTable {
    fn default() -> Self {
        Self::new()
    }
}

impl ProcessTable {
    pub fn new() -> Self {
        todo!("initialize an empty process table whose first PID is 1")
    }

    pub fn spawn(&mut self) -> Result<Pid, ProcessError> {
        todo!("allocate a monotonic PID and enqueue one Ready process")
    }

    pub fn schedule(&mut self) -> Option<Pid> {
        todo!("rotate the current process, then run the oldest Ready process")
    }

    pub fn block_current(&mut self) -> Result<Pid, ProcessError> {
        todo!("transition the current process from Running to Blocked")
    }

    pub fn wake(&mut self, pid: Pid) -> Result<(), ProcessError> {
        todo!("transition exactly one Blocked process to Ready")
    }

    pub fn exit_current(&mut self, code: i32) -> Result<Pid, ProcessError> {
        todo!("transition the current process to Exited(code)")
    }

    pub fn state(&self, pid: Pid) -> Option<ProcessState> {
        self.processes.get(&pid).copied()
    }

    pub fn current(&self) -> Option<Pid> {
        self.current
    }

    pub fn ready_order(&self) -> Vec<Pid> {
        self.ready.iter().copied().collect()
    }

    pub fn len(&self) -> usize {
        self.processes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.processes.is_empty()
    }

    pub fn validate(&self) -> Result<(), ProcessInvariant> {
        todo!("cross-check the current slot, states, and ready queue")
    }
}
