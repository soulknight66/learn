"""Deterministic tests and unsafe-excerpt incident reproducers for ParcelQ.

Provenance: locally authored from the three staged learner-safe files only.
Validation label: SELF-TEST; independent or transfer validation is not claimed.
"""

import unittest

from lease_queue import (
    Coordinator,
    DurableQueue,
    EventRunner,
    JobState,
    Lease,
    Node,
    Request,
    Response,
    StructuredLog,
)


def matching_records(log, event=None, decision=None, command_id=None):
    records = log.records
    if event is not None:
        records = [record for record in records if record["event"] == event]
    if decision is not None:
        records = [
            record for record in records if record["decision"] == decision
        ]
    if command_id is not None:
        records = [
            record
            for record in records
            if record["command_id"] == command_id
        ]
    return records


class ParcelQPublicTraceTests(unittest.TestCase):
    def make_model(self, jobs=("job",)):
        log = StructuredLog()
        queue = DurableQueue(jobs, log)
        coordinator = Coordinator(queue)
        return log, queue, coordinator

    def test_paused_old_dispatcher_unseen_delayed_command_is_fenced(self):
        log, queue, coordinator = self.make_model()
        old = Node("old", queue)
        new = Node("new", queue)
        runner = EventRunner(coordinator)
        first_grant = runner.schedule_grant(0, old, 3)
        runner.schedule_pause(1, old)
        second_grant = runner.schedule_grant(3, new, 4)
        runner.schedule_resume(4, old)
        delayed = runner.schedule_submit(
            4, old, Request("delayed", "CLAIM", "job", "worker-old")
        )

        results = runner.run()

        self.assertEqual(1, results[first_grant].epoch)
        self.assertEqual(2, results[second_grant].epoch)
        self.assertEqual(Response("FENCED"), results[delayed])
        self.assertEqual(JobState("READY", None), queue.jobs["job"])
        self.assertEqual({}, queue.history)
        self.assertEqual(Lease("new", 2, 3, 7), queue.active_lease)
        rejected = matching_records(
            log, event="queue_decision", decision="FENCED", command_id="delayed"
        )
        self.assertEqual(1, len(rejected))
        self.assertEqual("old", rejected[0]["owner"])
        self.assertEqual(1, rejected[0]["epoch"])
        self.assertEqual("new", rejected[0]["active_owner"])
        self.assertEqual(2, rejected[0]["active_epoch"])
        self.assertFalse(rejected[0]["state_changed"])
        self.assertFalse(rejected[0]["history_changed"])

    def test_duplicate_accepted_request_transitions_once_and_replays_exact_response(self):
        log, queue, coordinator = self.make_model()
        node = Node("dispatcher", queue)
        request = Request("claim-1", "CLAIM", "job", "worker-a")
        runner = EventRunner(coordinator)
        runner.schedule_grant(0, node, 5)
        first = runner.schedule_submit(1, node, request)
        duplicate = runner.schedule_submit(2, node, request)

        results = runner.run()

        self.assertEqual(Response("OK_CLAIMED"), results[first])
        self.assertIs(results[first], results[duplicate])
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.jobs["job"])
        self.assertEqual(1, len(queue.history))
        self.assertEqual(request.payload, queue.history["claim-1"].payload)
        self.assertEqual(
            1,
            len(matching_records(log, event="business_decision", command_id="claim-1")),
        )
        self.assertEqual(
            1, len(matching_records(log, event="replay", command_id="claim-1"))
        )

    def test_command_id_conflict_preserves_original_history_and_jobs(self):
        log, queue, coordinator = self.make_model(("one", "two"))
        node = Node("dispatcher", queue)
        runner = EventRunner(coordinator)
        original = Request("same-id", "CLAIM", "one", "worker-a")
        conflict = Request("same-id", "CLAIM", "two", "worker-b")
        runner.schedule_grant(0, node, 5)
        accepted = runner.schedule_submit(1, node, original)
        conflicting = runner.schedule_submit(2, node, conflict)

        results = runner.run()

        self.assertEqual(Response("OK_CLAIMED"), results[accepted])
        self.assertEqual(Response("ID_CONFLICT"), results[conflicting])
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.jobs["one"])
        self.assertEqual(JobState("READY", None), queue.jobs["two"])
        self.assertEqual(1, len(queue.history))
        self.assertEqual(original.payload, queue.history["same-id"].payload)
        conflict_records = matching_records(
            log, event="conflict", command_id="same-id"
        )
        self.assertEqual(1, len(conflict_records))
        self.assertFalse(conflict_records[0]["state_changed"])
        self.assertFalse(conflict_records[0]["history_changed"])

    def test_historical_replay_after_new_fence_does_not_revert_newer_state(self):
        log, queue, coordinator = self.make_model()
        old = Node("old", queue)
        new = Node("new", queue)
        claim = Request("claim", "CLAIM", "job", "worker-a")
        complete = Request("complete", "COMPLETE", "job", "worker-a")
        runner = EventRunner(coordinator)
        runner.schedule_grant(0, old, 2)
        accepted = runner.schedule_submit(1, old, claim)
        runner.schedule_grant(2, new, 5)
        completed = runner.schedule_submit(3, new, complete)
        replayed = runner.schedule_submit(4, old, claim)

        results = runner.run()

        self.assertEqual(Response("OK_CLAIMED"), results[accepted])
        self.assertEqual(Response("OK_DONE"), results[completed])
        self.assertIs(results[accepted], results[replayed])
        self.assertEqual(JobState("DONE", "worker-a"), queue.jobs["job"])
        self.assertEqual(2, len(queue.history))
        replay = matching_records(log, event="replay", command_id="claim")
        self.assertEqual(1, len(replay))
        self.assertEqual("old", replay[0]["owner"])
        self.assertEqual(1, replay[0]["epoch"])
        self.assertEqual("new", replay[0]["active_owner"])
        self.assertEqual(2, replay[0]["active_epoch"])
        self.assertEqual(
            {"status": "DONE", "worker_id": "worker-a"},
            replay[0]["job_before"],
        )
        self.assertFalse(replay[0]["state_changed"])

    def test_denied_before_expiry_has_no_epoch_gap_and_exact_expiry_succeeds(self):
        log, queue, coordinator = self.make_model()
        first = Node("first", queue)
        second = Node("second", queue)
        runner = EventRunner(coordinator)
        initial = runner.schedule_grant(0, first, 5)
        denied = runner.schedule_grant(4, second, 4)
        boundary = runner.schedule_grant(5, second, 4)

        results = runner.run()

        self.assertEqual(1, results[initial].epoch)
        self.assertIsNone(results[denied])
        self.assertEqual(2, results[boundary].epoch)
        self.assertEqual(2, coordinator.epoch)
        self.assertEqual(Lease("second", 2, 5, 9), coordinator.current)
        self.assertEqual(coordinator.current, queue.active_lease)
        self.assertEqual(2, len(matching_records(log, event="fence_install")))
        denied_logs = matching_records(
            log, event="grant_decision", decision="DENIED_ACTIVE"
        )
        self.assertEqual(1, len(denied_logs))
        self.assertEqual(1, denied_logs[0]["active_epoch"])

    def test_same_tick_business_events_use_insertion_order(self):
        log, queue, coordinator = self.make_model()
        node = Node("dispatcher", queue)
        runner = EventRunner(coordinator)
        runner.schedule_grant(0, node, 5)
        first = runner.schedule_submit(
            1, node, Request("first", "CLAIM", "job", "worker-a")
        )
        second = runner.schedule_submit(
            1, node, Request("second", "CLAIM", "job", "worker-b")
        )

        results = runner.run()

        self.assertEqual(Response("OK_CLAIMED"), results[first])
        self.assertEqual(Response("CLAIMED_BY_OTHER"), results[second])
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.jobs["job"])
        self.assertEqual(2, len(queue.history))
        decisions = matching_records(log, event="business_decision")
        self.assertEqual([first, second], [r["insertion_index"] for r in decisions])
        self.assertEqual(["first", "second"], [r["command_id"] for r in decisions])
        self.assertEqual(
            ["OK_CLAIMED", "CLAIMED_BY_OTHER"],
            [r["decision"] for r in decisions],
        )


class ParcelQContractTests(unittest.TestCase):
    def make_model(self, jobs=("job",)):
        log = StructuredLog()
        queue = DurableQueue(jobs, log)
        coordinator = Coordinator(queue)
        return log, queue, coordinator

    def test_all_forged_or_out_of_interval_unseen_requests_are_fenced(self):
        log, queue, coordinator = self.make_model()
        installed = coordinator.grant("real", 0, 3)
        variants = [
            (Lease("real", 0, 0, 3), 1),       # lower epoch
            (Lease("real", 2, 0, 3), 1),       # invented higher epoch
            (Lease("wrong", 1, 0, 3), 1),      # wrong owner
            (Lease("real", 1, 0, 4), 1),       # altered interval
            (Lease("real", 1, 2, 5), 1),       # not-yet-valid forgery
            (installed, 3),                     # exact expiry boundary
        ]
        for number, (lease, tick) in enumerate(variants):
            request = Request(
                "forged-{0}".format(number), "CLAIM", "job", "worker"
            )
            self.assertEqual(Response("FENCED"), queue.apply(request, lease, tick))

        self.assertEqual(JobState("READY", None), queue.jobs["job"])
        self.assertEqual({}, queue.history)
        self.assertEqual(installed, queue.active_lease)
        self.assertEqual(6, len(matching_records(log, decision="FENCED")))

    def test_invalid_ttl_and_failed_install_are_atomic(self):
        log, queue, coordinator = self.make_model()
        with self.assertRaises(ValueError):
            coordinator.grant("dispatcher", 0, 0)
        self.assertEqual(0, coordinator.epoch)
        self.assertIsNone(coordinator.current)
        self.assertIsNone(queue.active_lease)
        self.assertEqual([], matching_records(log, event="fence_install"))

        class RejectingQueue(DurableQueue):
            def _install_fence(
                self, lease, tick, installing_coordinator, insertion_index
            ):
                self._validate_fence_install(lease, installing_coordinator)
                raise RuntimeError("injected installation failure")

        failing_log = StructuredLog()
        failing_queue = RejectingQueue(("job",), failing_log)
        failing_coordinator = Coordinator(failing_queue)
        with self.assertRaisesRegex(RuntimeError, "injected"):
            failing_coordinator.grant("dispatcher", 0, 3)
        self.assertEqual(0, failing_coordinator.epoch)
        self.assertIsNone(failing_coordinator.current)
        self.assertIsNone(failing_queue.active_lease)
        self.assertEqual(
            [], matching_records(failing_log, event="fence_install")
        )
        self.assertEqual(
            1,
            len(
                matching_records(
                    failing_log,
                    event="grant_decision",
                    decision="INSTALL_FAILED",
                )
            ),
        )

    def test_unbound_caller_cannot_install_fence(self):
        log, queue, coordinator = self.make_model()
        with self.assertRaises(PermissionError):
            queue._install_fence(Lease("forged", 1, 0, 2), 0, object(), None)
        self.assertIsNone(queue.active_lease)
        self.assertIsNone(coordinator.current)
        self.assertEqual([], matching_records(log, event="fence_install"))

    def test_no_lease_is_early_node_rejection_without_history(self):
        log, queue, coordinator = self.make_model()
        node = Node("dispatcher", queue)
        request = Request("no-lease", "CLAIM", "job", "worker")
        self.assertEqual(Response("NO_LEASE"), node.submit(request, 0))
        self.assertEqual(JobState("READY", None), queue.jobs["job"])
        self.assertEqual({}, queue.history)
        rejection = matching_records(log, event="node_rejection")
        self.assertEqual(1, len(rejection))
        self.assertEqual("NO_LEASE", rejection[0]["decision"])

    def test_nonmutating_business_results_are_recorded_and_replay_stably(self):
        log, queue, coordinator = self.make_model()
        lease = coordinator.grant("dispatcher", 0, 5)
        not_claimed = Request("ready-complete", "COMPLETE", "job", "worker")
        invalid = Request("invalid", "CANCEL", "job", "worker")
        missing = Request("missing", "CLAIM", "absent", "worker")
        self.assertEqual(Response("NOT_CLAIMED"), queue.apply(not_claimed, lease, 1))
        self.assertEqual(Response("INVALID"), queue.apply(invalid, lease, 1))
        self.assertEqual(Response("NOT_FOUND"), queue.apply(missing, lease, 1))
        self.assertEqual(JobState("READY", None), queue.jobs["job"])
        self.assertEqual(3, len(queue.history))
        historical = queue.history["ready-complete"].response

        claim = Request("claim", "CLAIM", "job", "worker")
        self.assertEqual(Response("OK_CLAIMED"), queue.apply(claim, lease, 2))
        replay = queue.apply(not_claimed, lease, 2)
        self.assertIs(historical, replay)
        self.assertEqual(JobState("CLAIMED", "worker"), queue.jobs["job"])
        decision = matching_records(
            log, event="business_decision", command_id="ready-complete"
        )[0]
        self.assertFalse(decision["state_changed"])
        self.assertTrue(decision["history_changed"])

    def test_every_log_record_has_required_queryable_fields(self):
        log, queue, coordinator = self.make_model()
        node = Node("dispatcher", queue)
        runner = EventRunner(coordinator)
        runner.schedule_grant(0, node, 2)
        runner.schedule_submit(
            1, node, Request("claim", "CLAIM", "job", "worker")
        )
        runner.run()
        self.assertGreater(len(log.records), 0)
        for record in log.records:
            for field in StructuredLog.REQUIRED_FIELDS:
                self.assertIn(field, record)

    def test_identical_event_lists_produce_identical_state_responses_and_log(self):
        def execute():
            log, queue, coordinator = self.make_model()
            node = Node("dispatcher", queue)
            runner = EventRunner(coordinator)
            runner.schedule_grant(0, node, 4)
            runner.schedule_submit(
                1, node, Request("claim", "CLAIM", "job", "worker")
            )
            runner.schedule_submit(
                2, node, Request("complete", "COMPLETE", "job", "worker")
            )
            results = runner.run()
            result_codes = [
                None if value is None else getattr(value, "code", None)
                for _, value in sorted(results.items())
            ]
            return queue.jobs.copy(), queue.history.copy(), result_codes, log.records

        self.assertEqual(execute(), execute())


class _UnsafeQueue(object):
    """Tiny executable rendering of the unsafe excerpt for incident evidence."""

    def __init__(self, jobs, active_epoch=0):
        self.jobs = dict((job, "READY") for job in jobs)
        self.active_epoch = active_epoch
        self.history = {}

    def transition(self, request):
        if request.action == "CLAIM" and self.jobs[request.job_id] == "READY":
            self.jobs[request.job_id] = "CLAIMED:{0}".format(request.worker_id)
            return Response("OK_CLAIMED")
        return Response("NO_CHANGE")

    def apply(self, request, lease, tick):
        response = self.transition(request)
        if request.command_id in self.history:
            return self.history[request.command_id]
        if lease.epoch < self.active_epoch:
            return Response("FENCED")
        self.active_epoch = lease.epoch
        self.history[request.command_id] = response
        return response


class UnsafeExcerptIncidentTests(unittest.TestCase):
    """Passing tests whose assertions expose the intentionally unsafe behavior."""

    def test_unsafe_stale_request_mutates_before_fence_rejection(self):
        queue = _UnsafeQueue(("job",), active_epoch=2)
        stale = Lease("old", 1, 0, 2)
        response = queue.apply(
            Request("stale", "CLAIM", "job", "worker-old"), stale, 3
        )
        self.assertEqual(Response("FENCED"), response)
        self.assertEqual("CLAIMED:worker-old", queue.jobs["job"])
        self.assertEqual({}, queue.history)

    def test_unsafe_conflicting_id_mutates_second_job_and_returns_old_response(self):
        queue = _UnsafeQueue(("one", "two"), active_epoch=1)
        lease = Lease("dispatcher", 1, 0, 5)
        first = queue.apply(
            Request("same", "CLAIM", "one", "worker-a"), lease, 1
        )
        conflicting = queue.apply(
            Request("same", "CLAIM", "two", "worker-b"), lease, 2
        )
        self.assertIs(first, conflicting)
        self.assertEqual("CLAIMED:worker-a", queue.jobs["one"])
        self.assertEqual("CLAIMED:worker-b", queue.jobs["two"])
        self.assertEqual(1, len(queue.history))

    def test_unsafe_forged_higher_epoch_is_accepted_and_advances_fence(self):
        queue = _UnsafeQueue(("job",), active_epoch=1)
        forged = Lease("attacker", 99, 100, 101)
        response = queue.apply(
            Request("forged", "CLAIM", "job", "worker-x"), forged, 1
        )
        self.assertEqual(Response("OK_CLAIMED"), response)
        self.assertEqual(99, queue.active_epoch)
        self.assertEqual("CLAIMED:worker-x", queue.jobs["job"])

    def test_unsafe_node_accepts_exact_expiry_and_queue_does_not_check_time(self):
        queue = _UnsafeQueue(("job",), active_epoch=1)
        lease = Lease("dispatcher", 1, 0, 2)
        tick = 2
        locally_rejected = tick > lease.expires_tick
        self.assertFalse(locally_rejected)
        response = queue.apply(
            Request("boundary", "CLAIM", "job", "worker"), lease, tick
        )
        self.assertEqual(Response("OK_CLAIMED"), response)
        self.assertEqual("CLAIMED:worker", queue.jobs["job"])


if __name__ == "__main__":
    unittest.main()
