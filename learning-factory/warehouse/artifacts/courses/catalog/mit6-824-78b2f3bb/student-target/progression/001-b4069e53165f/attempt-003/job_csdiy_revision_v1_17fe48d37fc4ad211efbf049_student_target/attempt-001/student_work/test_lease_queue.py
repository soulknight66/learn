from __future__ import absolute_import

import unittest

from lease_queue import (
    CLAIMED,
    DONE,
    READY,
    Coordinator,
    DurableQueue,
    EventRunner,
    JobState,
    Lease,
    Node,
    RECORD_FIELDS,
    Request,
)


def records(queue, event):
    return [row for row in queue.audit.records if row["event"] == event]


class ParcelQPublicTraceTests(unittest.TestCase):
    def test_paused_old_dispatcher_delayed_unseen_command_is_fenced(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        runner = EventRunner(coordinator, queue)

        runner.schedule_grant(0, "old-dispatcher", 3)
        runner.schedule_grant(3, "new-dispatcher", 4)
        delayed = Request("cmd-delayed", "CLAIM", "parcel-1", "worker-a")
        delayed_index = runner.schedule_delivery(4, "old-dispatcher", delayed)
        outcomes = runner.run()

        self.assertEqual("FENCED", outcomes[-1].value.code)
        self.assertEqual(JobState(READY, None), queue.job_state("parcel-1"))
        self.assertEqual({}, queue.history)
        self.assertEqual("new-dispatcher", queue.active_lease.owner)
        self.assertEqual(2, queue.active_lease.epoch)

        rejection = records(queue, "fence_rejection")[-1]
        self.assertEqual(delayed_index, rejection["insertion_index"])
        self.assertEqual("old-dispatcher", rejection["owner"])
        self.assertEqual(1, rejection["epoch"])
        self.assertEqual("new-dispatcher", rejection["active_owner"])
        self.assertEqual(2, rejection["active_epoch"])
        self.assertFalse(rejection["state_changed"])
        self.assertFalse(rejection["history_changed"])
        self.assertEqual(rejection["job_before"], rejection["job_after"])

    def test_duplicate_accepted_request_transitions_once_and_replays_exactly(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        node = Node("dispatcher", queue)
        node.install_lease(coordinator.grant("dispatcher", 0, 5))
        request = Request("cmd-1", "CLAIM", "parcel-1", "worker-a")

        first = node.submit(request, 1)
        second = node.submit(request, 2)

        self.assertIs(first, second)
        self.assertEqual("OK_CLAIMED", second.code)
        self.assertEqual(JobState(CLAIMED, "worker-a"), queue.job_state("parcel-1"))
        self.assertEqual(1, len(queue.history))
        self.assertIs(first, queue.history["cmd-1"].response)
        self.assertEqual(1, len(records(queue, "business_decision")))
        self.assertEqual(1, len(records(queue, "replay")))
        self.assertFalse(records(queue, "replay")[0]["state_changed"])

    def test_same_id_different_payload_conflicts_without_replacement(self):
        queue = DurableQueue(["parcel-1", "parcel-2"])
        coordinator = Coordinator(queue)
        node = Node("dispatcher", queue)
        node.install_lease(coordinator.grant("dispatcher", 0, 5))
        original = Request("same-id", "CLAIM", "parcel-1", "worker-a")
        conflicting = Request("same-id", "CLAIM", "parcel-2", "worker-b")

        accepted = node.submit(original, 1)
        saved_entry = queue.history["same-id"]
        response = node.submit(conflicting, 2)

        self.assertEqual("ID_CONFLICT", response.code)
        self.assertIs(saved_entry, queue.history["same-id"])
        self.assertIs(accepted, saved_entry.response)
        self.assertEqual(1, len(queue.history))
        self.assertEqual(JobState(CLAIMED, "worker-a"), queue.job_state("parcel-1"))
        self.assertEqual(JobState(READY, None), queue.job_state("parcel-2"))
        conflict = records(queue, "conflict")[-1]
        self.assertFalse(conflict["state_changed"])
        self.assertFalse(conflict["history_changed"])

    def test_historical_request_replays_after_new_fence_without_reverting_state(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        old_node = Node("old", queue)
        old_node.install_lease(coordinator.grant("old", 0, 3))
        claim = Request("claim-1", "CLAIM", "parcel-1", "worker-a")
        original_response = old_node.submit(claim, 1)

        new_node = Node("new", queue)
        new_node.install_lease(coordinator.grant("new", 3, 4))
        done = new_node.submit(
            Request("complete-1", "COMPLETE", "parcel-1", "worker-a"), 3
        )
        replayed = old_node.submit(claim, 4)

        self.assertEqual("OK_DONE", done.code)
        self.assertIs(original_response, replayed)
        self.assertEqual(JobState(DONE, "worker-a"), queue.job_state("parcel-1"))
        self.assertEqual(2, len(queue.history))
        replay = records(queue, "replay")[-1]
        self.assertEqual(1, replay["epoch"])
        self.assertEqual(2, replay["active_epoch"])
        self.assertEqual("OK_CLAIMED", replay["response_code"])
        self.assertFalse(replay["state_changed"])
        self.assertEqual(
            {"status": DONE, "worker_id": "worker-a"}, replay["job_after"]
        )

    def test_denied_before_expiry_has_no_gap_and_exact_expiry_succeeds(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        first = coordinator.grant("one", 0, 5)

        denied = coordinator.grant("too-early", 4, 5)
        self.assertIsNone(denied)
        self.assertEqual(1, coordinator.epoch)
        self.assertIs(first, coordinator.current)
        self.assertIs(first, queue.active_lease)

        second = coordinator.grant("two", 5, 5)
        self.assertEqual(2, second.epoch)
        self.assertEqual(2, coordinator.epoch)
        self.assertIs(second, coordinator.current)
        self.assertIs(second, queue.active_lease)

        attempts = records(queue, "grant_attempt")
        self.assertEqual(
            ["GRANTED", "DENIED_CURRENT_LEASE", "GRANTED"],
            [row["decision"] for row in attempts],
        )
        self.assertEqual([1, 2], [row["epoch"] for row in records(queue, "fence_install")])

    def test_same_tick_business_events_follow_insertion_order(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        runner = EventRunner(coordinator, queue)
        runner.schedule_grant(0, "dispatcher", 5)
        first_request = Request("first", "CLAIM", "parcel-1", "worker-a")
        second_request = Request("second", "CLAIM", "parcel-1", "worker-b")
        first_index = runner.schedule_delivery(1, "dispatcher", first_request)
        second_index = runner.schedule_delivery(1, "dispatcher", second_request)

        outcomes = runner.run()
        by_index = dict((item.insertion_index, item.value) for item in outcomes)

        self.assertLess(first_index, second_index)
        self.assertEqual("OK_CLAIMED", by_index[first_index].code)
        self.assertEqual("CLAIMED_BY_OTHER", by_index[second_index].code)
        self.assertEqual(JobState(CLAIMED, "worker-a"), queue.job_state("parcel-1"))
        self.assertEqual(2, len(queue.history))
        decisions = records(queue, "business_decision")
        self.assertEqual([first_index, second_index], [r["insertion_index"] for r in decisions])
        self.assertEqual(
            ["OK_CLAIMED", "CLAIMED_BY_OTHER"],
            [r["decision"] for r in decisions],
        )


class ParcelQContractTests(unittest.TestCase):
    def test_lower_higher_wrong_owner_altered_interval_and_bad_ticks_are_fenced(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        active = coordinator.grant("dispatcher", 10, 5)
        attempts = [
            (Lease("dispatcher", 0, 10, 15), 11),
            (Lease("dispatcher", 2, 10, 15), 11),
            (Lease("intruder", 1, 10, 15), 11),
            (Lease("dispatcher", 1, 9, 15), 11),
            (Lease("dispatcher", 1, 10, 16), 11),
            (active, 9),
            (active, 15),
        ]

        for number, (lease, tick) in enumerate(attempts):
            request = Request("forged-%d" % number, "CLAIM", "parcel-1", "worker")
            self.assertEqual("FENCED", queue.apply(request, lease, tick).code)

        self.assertEqual({}, queue.history)
        self.assertEqual(JobState(READY, None), queue.job_state("parcel-1"))
        self.assertIs(active, queue.active_lease)
        self.assertEqual(7, len(records(queue, "fence_rejection")))

    def test_fenced_first_attempt_can_retry_with_same_identity_under_valid_fence(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        active = coordinator.grant("dispatcher", 0, 5)
        request = Request("retry-me", "CLAIM", "parcel-1", "worker-a")

        first = queue.apply(request, Lease("wrong", 1, 0, 5), 1)
        self.assertEqual("FENCED", first.code)
        self.assertNotIn("retry-me", queue.history)
        second = queue.apply(request, active, 1)

        self.assertEqual("OK_CLAIMED", second.code)
        self.assertIn("retry-me", queue.history)
        self.assertEqual(JobState(CLAIMED, "worker-a"), queue.job_state("parcel-1"))

    def test_node_without_lease_rejects_without_reaching_queue(self):
        queue = DurableQueue(["parcel-1"])
        Coordinator(queue)
        node = Node("dispatcher", queue)
        response = node.submit(Request("cmd", "CLAIM", "parcel-1", "worker"), 0)

        self.assertEqual("NO_LEASE", response.code)
        self.assertEqual({}, queue.history)
        self.assertEqual(JobState(READY, None), queue.job_state("parcel-1"))
        self.assertEqual(1, len(records(queue, "node_rejection")))
        self.assertEqual(0, len(records(queue, "queue_attempt")))

    def test_nonmutating_business_response_is_historical_and_stable(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        active = coordinator.grant("dispatcher", 0, 8)
        premature = Request("premature", "COMPLETE", "parcel-1", "worker-a")

        first = queue.apply(premature, active, 1)
        self.assertEqual("NOT_CLAIMED", first.code)
        self.assertIn("premature", queue.history)
        queue.apply(Request("claim", "CLAIM", "parcel-1", "worker-a"), active, 2)
        replay = queue.apply(premature, active, 3)

        self.assertIs(first, replay)
        self.assertEqual(JobState(CLAIMED, "worker-a"), queue.job_state("parcel-1"))
        first_decision = [
            row
            for row in records(queue, "business_decision")
            if row["command_id"] == "premature"
        ][0]
        self.assertFalse(first_decision["state_changed"])
        self.assertTrue(first_decision["history_changed"])

    def test_conflict_precedes_fence_check_even_after_failover(self):
        queue = DurableQueue(["parcel-1", "parcel-2"])
        coordinator = Coordinator(queue)
        old = coordinator.grant("old", 0, 2)
        accepted = Request("identity", "CLAIM", "parcel-1", "worker-a")
        queue.apply(accepted, old, 1)
        coordinator.grant("new", 2, 5)

        conflicting = Request("identity", "CLAIM", "parcel-2", "worker-b")
        response = queue.apply(conflicting, old, 3)

        self.assertEqual("ID_CONFLICT", response.code)
        self.assertEqual(JobState(READY, None), queue.job_state("parcel-2"))
        self.assertEqual(1, len(queue.history))
        self.assertEqual("conflict", queue.audit.records[-1]["event"])
        self.assertEqual(1, queue.audit.records[-1]["epoch"])
        self.assertEqual(2, queue.audit.records[-1]["active_epoch"])

    def test_invalid_ttl_and_post_install_failure_expose_no_partial_grant(self):
        class FailAfterInstallQueue(DurableQueue):
            def __init__(self, jobs):
                DurableQueue.__init__(self, jobs)
                self.fail = True

            def _install_fence(self, lease, tick, caller, insertion_index=None):
                record = DurableQueue._install_fence(
                    self, lease, tick, caller, insertion_index=insertion_index
                )
                if self.fail:
                    # Deliberately add misleading partial evidence too; the
                    # coordinator transaction must remove it on rollback.
                    self.audit.append(record)
                    raise RuntimeError("injected installation failure")
                return record

        queue = FailAfterInstallQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        for bad_ttl in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                coordinator.grant("dispatcher", 0, bad_ttl)
        self.assertEqual(0, coordinator.epoch)
        self.assertIsNone(coordinator.current)
        self.assertIsNone(queue.active_lease)

        with self.assertRaises(RuntimeError):
            coordinator.grant("dispatcher", 0, 3)
        self.assertEqual(0, coordinator.epoch)
        self.assertIsNone(coordinator.current)
        self.assertIsNone(queue.active_lease)
        self.assertEqual(0, len(records(queue, "fence_install")))
        self.assertEqual("INSTALL_FAILED", records(queue, "grant_attempt")[-1]["decision"])

        queue.fail = False
        lease = coordinator.grant("dispatcher", 0, 3)
        self.assertEqual(1, lease.epoch)
        self.assertIs(lease, coordinator.current)
        self.assertIs(lease, queue.active_lease)

    def test_only_bound_coordinator_identity_can_install_fence(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        with self.assertRaises(PermissionError):
            queue._install_fence(Lease("intruder", 1, 0, 2), 0, object())
        self.assertEqual(0, coordinator.epoch)
        self.assertIsNone(queue.active_lease)
        self.assertEqual([], queue.audit.records)

    def test_business_response_codes_and_history_rules(self):
        queue = DurableQueue(["a", "b", "c"])
        coordinator = Coordinator(queue)
        lease = coordinator.grant("dispatcher", 0, 20)

        cases = [
            (Request("invalid", "REMOVE", "a", "w"), "INVALID"),
            (Request("missing", "CLAIM", "missing", "w"), "NOT_FOUND"),
            (Request("claim-a", "CLAIM", "a", "w1"), "OK_CLAIMED"),
            (Request("same-a", "CLAIM", "a", "w1"), "ALREADY_CLAIMED"),
            (Request("other-a", "CLAIM", "a", "w2"), "CLAIMED_BY_OTHER"),
            (Request("wrong-complete", "COMPLETE", "a", "w2"), "NOT_OWNER"),
            (Request("done-a", "COMPLETE", "a", "w1"), "OK_DONE"),
            (Request("done-again", "COMPLETE", "a", "w1"), "ALREADY_DONE"),
            (Request("ready-complete", "COMPLETE", "b", "w1"), "NOT_CLAIMED"),
        ]
        for tick, (request, expected) in enumerate(cases, 1):
            self.assertEqual(expected, queue.apply(request, lease, tick).code)

        self.assertEqual(len(cases), len(queue.history))
        self.assertEqual(JobState(DONE, "w1"), queue.job_state("a"))
        self.assertEqual(JobState(READY, None), queue.job_state("b"))

    def test_identical_event_lists_produce_identical_state_responses_and_logs(self):
        def run_trace():
            queue = DurableQueue(["parcel-1"])
            coordinator = Coordinator(queue)
            runner = EventRunner(coordinator, queue)
            runner.schedule_grant(0, "dispatcher", 4)
            runner.schedule_delivery(
                1,
                "dispatcher",
                Request("claim", "CLAIM", "parcel-1", "worker-a"),
            )
            runner.schedule_delivery(
                1,
                "dispatcher",
                Request("other", "CLAIM", "parcel-1", "worker-b"),
            )
            outcomes = runner.run()
            return queue.jobs.copy(), queue.history.copy(), outcomes, list(queue.audit.records)

        self.assertEqual(run_trace(), run_trace())

    def test_every_log_record_has_the_common_queryable_schema(self):
        queue = DurableQueue(["parcel-1"])
        coordinator = Coordinator(queue)
        node = Node("dispatcher", queue)
        node.submit(Request("none", "CLAIM", "parcel-1", "worker"), 0)
        node.install_lease(coordinator.grant("dispatcher", 0, 2))
        request = Request("claim", "CLAIM", "parcel-1", "worker")
        node.submit(request, 1)
        node.submit(request, 2)
        queue.apply(
            Request("stale", "CLAIM", "parcel-1", "other"), node.lease, 2
        )

        required = {
            "tick",
            "event",
            "command_id",
            "owner",
            "epoch",
            "active_owner",
            "active_epoch",
            "decision",
            "state_changed",
            "job_before",
            "job_after",
        }
        self.assertTrue(queue.audit.records)
        for record in queue.audit.records:
            self.assertTrue(required.issubset(record))
            self.assertTrue(set(RECORD_FIELDS).issubset(record))


class _UnsafeExcerptQueue(object):
    """Small executable transcription of the excerpt's unsafe ordering."""

    def __init__(self, jobs, active_epoch):
        self.jobs = dict((job, READY) for job in jobs)
        self.active_epoch = active_epoch
        self.history = {}
        self.transition_calls = 0

    def transition(self, request):
        self.transition_calls += 1
        if request.action == "CLAIM" and self.jobs[request.job_id] == READY:
            self.jobs[request.job_id] = CLAIMED
            return "OK_CLAIMED"
        return "NO_CHANGE"

    def apply(self, request, epoch):
        response = self.transition(request)
        if request.command_id in self.history:
            return self.history[request.command_id]
        if epoch < self.active_epoch:
            return "FENCED"
        self.active_epoch = epoch
        self.history[request.command_id] = response
        return response


class UnsafeExcerptIncidentTests(unittest.TestCase):
    def test_stale_command_mutates_before_fence_rejection(self):
        unsafe = _UnsafeExcerptQueue(["job"], active_epoch=2)
        response = unsafe.apply(Request("stale", "CLAIM", "job", "w"), epoch=1)
        self.assertEqual("FENCED", response)
        self.assertEqual(CLAIMED, unsafe.jobs["job"])
        self.assertEqual({}, unsafe.history)

    def test_duplicate_reexecutes_transition_before_history_replay(self):
        unsafe = _UnsafeExcerptQueue(["job"], active_epoch=1)
        request = Request("dup", "CLAIM", "job", "w")
        first = unsafe.apply(request, epoch=1)
        second = unsafe.apply(request, epoch=1)
        self.assertEqual(first, second)
        self.assertEqual(2, unsafe.transition_calls)
        self.assertEqual(1, len(unsafe.history))

    def test_conflicting_payload_mutates_before_id_only_history_replay(self):
        unsafe = _UnsafeExcerptQueue(["a", "b"], active_epoch=1)
        first = unsafe.apply(Request("same", "CLAIM", "a", "w1"), epoch=1)
        conflict = unsafe.apply(Request("same", "CLAIM", "b", "w2"), epoch=1)
        self.assertEqual(first, conflict)
        self.assertEqual(CLAIMED, unsafe.jobs["a"])
        self.assertEqual(CLAIMED, unsafe.jobs["b"])
        self.assertEqual(1, len(unsafe.history))

    def test_invented_higher_epoch_self_authorizes_and_advances_fence(self):
        unsafe = _UnsafeExcerptQueue(["job"], active_epoch=1)
        response = unsafe.apply(Request("forged", "CLAIM", "job", "w"), epoch=99)
        self.assertEqual("OK_CLAIMED", response)
        self.assertEqual(99, unsafe.active_epoch)
        self.assertEqual(CLAIMED, unsafe.jobs["job"])


if __name__ == "__main__":
    unittest.main()
