use std::collections::{BTreeMap, BTreeSet, VecDeque};

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
        Self {
            next_pid: Some(1),
            processes: BTreeMap::new(),
            ready: VecDeque::new(),
            current: None,
        }
    }

    pub fn spawn(&mut self) -> Result<Pid, ProcessError> {
        let raw = self.next_pid.ok_or(ProcessError::PidExhausted)?;
        let pid = Pid(raw);
        self.next_pid = raw.checked_add(1);
        self.processes.insert(pid, ProcessState::Ready);
        self.ready.push_back(pid);
        Ok(pid)
    }

    pub fn schedule(&mut self) -> Option<Pid> {
        if let Some(previous) = self.current.take() {
            let state = self
                .processes
                .get_mut(&previous)
                .expect("current PID is an internal process-table invariant");
            debug_assert_eq!(*state, ProcessState::Running);
            *state = ProcessState::Ready;
            self.ready.push_back(previous);
        }

        let next = self.ready.pop_front()?;
        let state = self
            .processes
            .get_mut(&next)
            .expect("queued PID is an internal process-table invariant");
        debug_assert_eq!(*state, ProcessState::Ready);
        *state = ProcessState::Running;
        self.current = Some(next);
        Some(next)
    }

    pub fn block_current(&mut self) -> Result<Pid, ProcessError> {
        let pid = self.current.ok_or(ProcessError::NoCurrent)?;
        let state = self
            .processes
            .get_mut(&pid)
            .expect("current PID is an internal process-table invariant");
        debug_assert_eq!(*state, ProcessState::Running);
        *state = ProcessState::Blocked;
        self.current = None;
        Ok(pid)
    }

    pub fn wake(&mut self, pid: Pid) -> Result<(), ProcessError> {
        let state = self
            .processes
            .get_mut(&pid)
            .ok_or(ProcessError::NoSuchProcess(pid))?;
        if *state != ProcessState::Blocked {
            return Err(ProcessError::NotBlocked(pid));
        }
        *state = ProcessState::Ready;
        self.ready.push_back(pid);
        Ok(())
    }

    pub fn exit_current(&mut self, code: i32) -> Result<Pid, ProcessError> {
        let pid = self.current.ok_or(ProcessError::NoCurrent)?;
        let state = self
            .processes
            .get_mut(&pid)
            .expect("current PID is an internal process-table invariant");
        debug_assert_eq!(*state, ProcessState::Running);
        *state = ProcessState::Exited(code);
        self.current = None;
        Ok(pid)
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
        if let Some(current) = self.current {
            let state = self
                .processes
                .get(&current)
                .ok_or(ProcessInvariant::CurrentMissing(current))?;
            if *state != ProcessState::Running {
                return Err(ProcessInvariant::CurrentNotRunning(current));
            }
        }

        let running: Vec<Pid> = self
            .processes
            .iter()
            .filter_map(|(pid, state)| (*state == ProcessState::Running).then_some(*pid))
            .collect();
        if running.len() > 1 {
            return Err(ProcessInvariant::MultipleRunning);
        }
        if let Some(runner) = running.first().copied() {
            if self.current != Some(runner) {
                return Err(ProcessInvariant::RunningWithoutCurrent(runner));
            }
        }

        let mut queued = BTreeSet::new();
        for pid in &self.ready {
            if !queued.insert(*pid) {
                return Err(ProcessInvariant::DuplicateQueueEntry(*pid));
            }
            let state = self
                .processes
                .get(pid)
                .ok_or(ProcessInvariant::QueueMissingProcess(*pid))?;
            if *state != ProcessState::Ready {
                return Err(ProcessInvariant::QueueContainsNonReady(*pid));
            }
        }
        for (pid, state) in &self.processes {
            if *state == ProcessState::Ready && !queued.contains(pid) {
                return Err(ProcessInvariant::ReadyMissingFromQueue(*pid));
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod internal_tests {
    use super::*;

    #[test]
    fn maximum_pid_is_issued_once_then_exhausted_atomically() {
        let mut table = ProcessTable {
            next_pid: Some(u32::MAX),
            processes: BTreeMap::new(),
            ready: VecDeque::new(),
            current: None,
        };
        assert_eq!(table.spawn(), Ok(Pid(u32::MAX)));
        let before = table.ready_order();
        assert_eq!(table.spawn(), Err(ProcessError::PidExhausted));
        assert_eq!(table.ready_order(), before);
        assert_eq!(table.len(), 1);
        assert_eq!(table.validate(), Ok(()));
    }

    #[test]
    fn validator_detects_a_duplicate_queue_entry() {
        let mut table = ProcessTable::new();
        let pid = table.spawn().unwrap();
        table.ready.push_back(pid);
        assert_eq!(
            table.validate(),
            Err(ProcessInvariant::DuplicateQueueEntry(pid))
        );
    }
}
