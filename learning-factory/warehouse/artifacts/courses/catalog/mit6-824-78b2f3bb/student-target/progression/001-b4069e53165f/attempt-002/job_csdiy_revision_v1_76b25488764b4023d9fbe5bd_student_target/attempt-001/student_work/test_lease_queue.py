"""Deterministic public, contract, and unsafe-excerpt incident traces."""

from __future__ import print_function

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


def make_system(job_ids=("job-1", "job-2"), owners=("alpha", "beta")):
    audit = StructuredLog()
    queue = DurableQueue(job_ids, audit)
    coordinator = Coordinator(queue)
    nodes = {owner: Node(owner, queue) for owner in owners}
    runner = EventRunner(coordinator, nodes)
    return audit, queue, coordinator, nodes, runner


class ParcelQPublicTraceTests(unittest.TestCase):
    def test_paused_old_dispatcher_unseen_delayed_command_is_fenced(self):
        audit, queue, coordinator, nodes, runner = make_system()
        runner.schedule_grant(0, "alpha", 3)
        runner.schedule_pause(1, "alpha")
        runner.schedule_grant(3, "beta", 4)
        runner.schedule_resume(4, "alpha")
        delayed = Request("late-1", "CLAIM", "job-1", "worker-a")
        delayed_index = runner.schedule_submit(4, "alpha", delayed)

        runner.run()

        self.assertEqual(Response("FENCED"), runner.result_for(delayed_index))
        self.assertEqual(JobState("READY", None), queue.job_state("job-1"))
        self.assertEqual({}, queue.history)
        self.assertEqual("beta", queue.active_lease.owner)
        self.assertEqual(2, queue.active_lease.epoch)
        rejection = [
            record
            for record in audit.records
            if record["event"] == "fence_rejection"
        ][0]
        self.assertEqual("late-1", rejection["command_id"])
        self.assertEqual(("alpha", 1), (rejection["owner"], rejection["epoch"]))
        self.assertEqual(
            ("beta", 2),
            (rejection["active_owner"], rejection["active_epoch"]),
        )
        self.assertFalse(rejection["state_changed"])
        self.assertFalse(rejection["history_changed"])
        self.assertEqual(rejection["job_before"], rejection["job_after"])

    def test_duplicate_accepted_request_replays_one_transition(self):
        audit, queue, coordinator, nodes, runner = make_system()
        runner.schedule_grant(0, "alpha", 10)
        request = Request("claim-1", "CLAIM", "job-1", "worker-a")
        first_index = runner.schedule_submit(1, "alpha", request)
        second_index = runner.schedule_submit(2, "alpha", request)

        runner.run()

        first = runner.result_for(first_index)
        second = runner.result_for(second_index)
        self.assertEqual(Response("OK_CLAIMED"), first)
        self.assertIs(first, second)
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.job_state("job-1"))
        self.assertEqual(1, len(queue.history))
        self.assertIs(first, queue.history["claim-1"].response)
        self.assertEqual(
            ["business_decision", "replay"],
            [
                record["event"]
                for record in audit.records
                if record["command_id"] == "claim-1"
                and record["event"] != "queue_attempt"
            ],
        )
        self.assertEqual(
            1,
            len(
                [
                    record
                    for record in audit.records
                    if record["command_id"] == "claim-1"
                    and record["state_changed"]
                ]
            ),
        )

    def test_command_id_conflict_preserves_original_history_and_jobs(self):
        audit, queue, coordinator, nodes, runner = make_system()
        runner.schedule_grant(0, "alpha", 10)
        original = Request("shared-id", "CLAIM", "job-1", "worker-a")
        conflict = Request("shared-id", "CLAIM", "job-2", "worker-b")
        accepted_index = runner.schedule_submit(1, "alpha", original)
        conflict_index = runner.schedule_submit(2, "alpha", conflict)

        runner.run()

        accepted = runner.result_for(accepted_index)
        self.assertEqual(Response("OK_CLAIMED"), accepted)
        self.assertEqual(Response("ID_CONFLICT"), runner.result_for(conflict_index))
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.job_state("job-1"))
        self.assertEqual(JobState("READY", None), queue.job_state("job-2"))
        self.assertEqual(1, len(queue.history))
        self.assertEqual(original.payload, queue.history["shared-id"].payload)
        self.assertIs(accepted, queue.history["shared-id"].response)
        conflict_record = [
            record for record in audit.records if record["event"] == "conflict"
        ][0]
        self.assertFalse(conflict_record["state_changed"])
        self.assertFalse(conflict_record["history_changed"])

    def test_historical_request_replays_after_new_fence_without_reversion(self):
        audit, queue, coordinator, nodes, runner = make_system()
        runner.schedule_grant(0, "alpha", 3)
        claim = Request("claim-old", "CLAIM", "job-1", "worker-a")
        first_index = runner.schedule_submit(1, "alpha", claim)
        runner.schedule_grant(3, "beta", 5)
        complete = Request("complete-new", "COMPLETE", "job-1", "worker-a")
        complete_index = runner.schedule_submit(4, "beta", complete)
        replay_index = runner.schedule_submit(5, "alpha", claim)

        runner.run()

        self.assertEqual(Response("OK_CLAIMED"), runner.result_for(first_index))
        self.assertEqual(Response("OK_DONE"), runner.result_for(complete_index))
        self.assertIs(
            runner.result_for(first_index), runner.result_for(replay_index)
        )
        self.assertEqual(JobState("DONE", "worker-a"), queue.job_state("job-1"))
        self.assertEqual(2, len(queue.history))
        replay = [
            record
            for record in audit.records
            if record["event"] == "replay"
            and record["command_id"] == "claim-old"
        ][0]
        self.assertEqual((1, 2), (replay["epoch"], replay["active_epoch"]))
        self.assertEqual("DONE", replay["job_before"]["state"])
        self.assertEqual(replay["job_before"], replay["job_after"])
        self.assertFalse(replay["state_changed"])

    def test_denied_before_expiry_has_no_gap_and_exact_expiry_succeeds(self):
        audit, queue, coordinator, nodes, runner = make_system()
        first_grant = runner.schedule_grant(0, "alpha", 5)
        denied_grant = runner.schedule_grant(4, "beta", 5)
        expiry_grant = runner.schedule_grant(5, "beta", 5)

        runner.run()

        self.assertEqual(1, runner.result_for(first_grant).epoch)
        self.assertIsNone(runner.result_for(denied_grant))
        self.assertEqual(2, runner.result_for(expiry_grant).epoch)
        self.assertEqual(2, coordinator.epoch)
        self.assertEqual(Lease("beta", 2, 5, 10), coordinator.current)
        self.assertEqual(coordinator.current, queue.active_lease)
        installs = [
            record for record in audit.records if record["event"] == "fence_install"
        ]
        self.assertEqual([1, 2], [record["epoch"] for record in installs])
        denied = [
            record
            for record in audit.records
            if record["event"] == "grant_decision"
            and record["decision"] == "DENIED_ACTIVE"
        ][0]
        self.assertEqual(4, denied["tick"])
        self.assertEqual(1, denied["active_epoch"])

    def test_same_tick_business_events_follow_insertion_order(self):
        audit, queue, coordinator, nodes, runner = make_system()
        runner.schedule_grant(0, "alpha", 5)
        first = Request("same-tick-first", "CLAIM", "job-1", "worker-a")
        second = Request("same-tick-second", "CLAIM", "job-1", "worker-b")
        first_index = runner.schedule_submit(1, "alpha", first)
        second_index = runner.schedule_submit(1, "alpha", second)

        runner.run()

        self.assertLess(first_index, second_index)
        self.assertEqual(Response("OK_CLAIMED"), runner.result_for(first_index))
        self.assertEqual(
            Response("CLAIMED_BY_OTHER"), runner.result_for(second_index)
        )
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.job_state("job-1"))
        self.assertEqual(2, len(queue.history))
        decisions = [
            record
            for record in audit.records
            if record["event"] == "business_decision" and record["tick"] == 1
        ]
        self.assertEqual(
            [first_index, second_index],
            [record["insertion_index"] for record in decisions],
        )
        self.assertEqual(
            ["same-tick-first", "same-tick-second"],
            [record["command_id"] for record in decisions],
        )
        self.assertEqual([True, False], [r["state_changed"] for r in decisions])


class ParcelQContractTests(unittest.TestCase):
    def test_all_forged_or_out_of_interval_unseen_requests_are_fenced(self):
        audit, queue, coordinator, nodes, runner = make_system()
        installed = coordinator.grant("alpha", 10, 5)
        nodes["alpha"].receive_lease(installed, 10)
        attempts = [
            (Lease("alpha", 0, 10, 15), 11),
            (Lease("alpha", 2, 10, 15), 11),
            (Lease("mallory", 1, 10, 15), 11),
            (Lease("alpha", 1, 9, 15), 11),
            (Lease("alpha", 1, 10, 16), 11),
            (installed, 9),
            (installed, 15),
        ]
        for number, (presented, tick) in enumerate(attempts):
            request = Request(
                "forged-{0}".format(number), "CLAIM", "job-1", "worker-a"
            )
            self.assertEqual(Response("FENCED"), queue.apply(request, presented, tick))

        self.assertEqual(JobState("READY", None), queue.job_state("job-1"))
        self.assertEqual({}, queue.history)
        self.assertEqual(installed, queue.active_lease)
        rejections = [r for r in audit.records if r["event"] == "fence_rejection"]
        self.assertEqual(7, len(rejections))
        self.assertTrue(all(not r["state_changed"] for r in rejections))
        self.assertTrue(all(not r["history_changed"] for r in rejections))

        # The expiry rejection created no history, so the same logical command
        # can be retried through the newly fenced dispatcher.
        replacement = coordinator.grant("beta", 15, 5)
        nodes["beta"].receive_lease(replacement, 15)
        retry = Request("forged-6", "CLAIM", "job-1", "worker-a")
        self.assertEqual(Response("OK_CLAIMED"), nodes["beta"].submit(retry, 16))
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.job_state("job-1"))
        self.assertEqual(1, len(queue.history))

    def test_node_without_lease_rejects_before_queue_and_history(self):
        audit, queue, coordinator, nodes, runner = make_system()
        request = Request("no-token", "CLAIM", "job-1", "worker-a")

        response = nodes["alpha"].submit(request, 0)

        self.assertEqual(Response("NO_LEASE"), response)
        self.assertEqual(JobState("READY", None), queue.job_state("job-1"))
        self.assertEqual({}, queue.history)
        self.assertEqual(
            ["node_rejection"],
            [record["event"] for record in audit.records],
        )
        self.assertEqual("NO_LEASE", audit.records[0]["decision"])

    def test_authorized_nonmutating_response_is_historical_and_stable(self):
        audit, queue, coordinator, nodes, runner = make_system()
        lease = coordinator.grant("alpha", 0, 10)
        nodes["alpha"].receive_lease(lease, 0)
        too_early = Request("early-complete", "COMPLETE", "job-1", "worker-a")
        claim = Request("later-claim", "CLAIM", "job-1", "worker-a")

        original = nodes["alpha"].submit(too_early, 1)
        self.assertEqual(Response("NOT_CLAIMED"), original)
        self.assertEqual(Response("OK_CLAIMED"), nodes["alpha"].submit(claim, 2))
        replayed = nodes["alpha"].submit(too_early, 3)

        self.assertIs(original, replayed)
        self.assertEqual(JobState("CLAIMED", "worker-a"), queue.job_state("job-1"))
        self.assertEqual(2, len(queue.history))
        original_decision = [
            r
            for r in audit.records
            if r["event"] == "business_decision"
            and r["command_id"] == "early-complete"
        ][0]
        self.assertFalse(original_decision["state_changed"])
        self.assertTrue(original_decision["history_changed"])

    def test_invalid_ttl_and_failed_install_are_atomic(self):
        audit = StructuredLog()
        queue = DurableQueue(("job-1",), audit)
        coordinator = Coordinator(queue)

        with self.assertRaises(ValueError):
            coordinator.grant("alpha", 0, 0)
        self.assertEqual(0, coordinator.epoch)
        self.assertIsNone(coordinator.current)
        self.assertIsNone(queue.active_lease)
        self.assertEqual([], [r for r in audit.records if r["event"] == "fence_install"])

        class FailAfterInstallQueue(DurableQueue):
            def _install_fence(
                self, lease, tick, authority, insertion_index=None
            ):
                DurableQueue._install_fence(
                    self, lease, tick, authority, insertion_index
                )
                raise RuntimeError("injected installation failure")

        failed_audit = StructuredLog()
        failed_queue = FailAfterInstallQueue(("job-1",), failed_audit)
        failed_coordinator = Coordinator(failed_queue)
        with self.assertRaises(RuntimeError):
            failed_coordinator.grant("alpha", 0, 5)
        self.assertEqual(0, failed_coordinator.epoch)
        self.assertIsNone(failed_coordinator.current)
        self.assertIsNone(failed_queue.active_lease)
        self.assertEqual(
            [], [r for r in failed_audit.records if r["event"] == "fence_install"]
        )
        self.assertEqual(
            "INSTALL_FAILED",
            [r for r in failed_audit.records if r["event"] == "grant_decision"][-1][
                "decision"
            ],
        )

    def test_unbound_caller_cannot_install_a_fence(self):
        audit, queue, coordinator, nodes, runner = make_system()

        with self.assertRaises(PermissionError):
            queue._install_fence(Lease("mallory", 1, 0, 5), 0, object())

        self.assertIsNone(queue.active_lease)
        self.assertIsNone(coordinator.current)
        self.assertEqual(0, coordinator.epoch)
        self.assertEqual([], audit.records)

    def test_business_response_codes_and_history_policy(self):
        audit, queue, coordinator, nodes, runner = make_system()
        lease = coordinator.grant("alpha", 0, 20)
        nodes["alpha"].receive_lease(lease, 0)
        cases = [
            (Request("c1", "CLAIM", "missing", "w1"), "NOT_FOUND"),
            (Request("c2", "BOGUS", "job-1", "w1"), "INVALID"),
            (Request("c3", "COMPLETE", "job-1", "w1"), "NOT_CLAIMED"),
            (Request("c4", "CLAIM", "job-1", "w1"), "OK_CLAIMED"),
            (Request("c5", "CLAIM", "job-1", "w1"), "ALREADY_CLAIMED"),
            (Request("c6", "CLAIM", "job-1", "w2"), "CLAIMED_BY_OTHER"),
            (Request("c7", "COMPLETE", "job-1", "w2"), "NOT_OWNER"),
            (Request("c8", "COMPLETE", "job-1", "w1"), "OK_DONE"),
            (Request("c9", "COMPLETE", "job-1", "w1"), "ALREADY_DONE"),
            (Request("c10", "CLAIM", "job-1", "w1"), "ALREADY_DONE"),
        ]

        actual = [nodes["alpha"].submit(request, 1).code for request, code in cases]

        self.assertEqual([code for request, code in cases], actual)
        self.assertEqual(JobState("DONE", "w1"), queue.job_state("job-1"))
        self.assertEqual(len(cases), len(queue.history))
        decisions = [r for r in audit.records if r["event"] == "business_decision"]
        self.assertEqual(len(cases), len(decisions))
        self.assertTrue(all(r["history_changed"] for r in decisions))
        self.assertEqual(2, len([r for r in decisions if r["state_changed"]]))

    def test_repeat_runs_have_identical_results_logs_and_common_schema(self):
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

        def execute():
            audit, queue, coordinator, nodes, runner = make_system()
            runner.schedule_grant(0, "alpha", 4)
            runner.schedule_submit(
                1, "alpha", Request("one", "CLAIM", "job-1", "w1")
            )
            runner.schedule_submit(
                1, "alpha", Request("two", "CLAIM", "job-1", "w2")
            )
            results = runner.run()
            values = [
                result.value.code
                if isinstance(result.value, Response)
                else result.value
                for result in results
            ]
            return values, audit.records, queue.jobs, queue.history

        first = execute()
        second = execute()

        self.assertEqual(first, second)
        for record in first[1]:
            self.assertTrue(required.issubset(set(record)))


class UnsafeQueue(object):
    """Only enough of the manager-provided unsafe ordering for reproducers."""

    def __init__(self, job_ids, active_epoch):
        self.jobs = {job_id: "READY" for job_id in job_ids}
        self.history = {}
        self.active_epoch = active_epoch

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
    def test_hypothesis_transition_before_fence_mutates_stale_command(self):
        queue = UnsafeQueue(("job-1",), active_epoch=2)
        stale = Lease("old", 1, 0, 3)
        request = Request("late", "CLAIM", "job-1", "worker-a")

        response = queue.apply(request, stale, 4)

        self.assertEqual(Response("FENCED"), response)
        self.assertEqual("CLAIMED:worker-a", queue.jobs["job-1"])
        self.assertEqual({}, queue.history)

    def test_hypothesis_history_after_transition_mutates_id_conflict(self):
        queue = UnsafeQueue(("job-1", "job-2"), active_epoch=1)
        lease = Lease("alpha", 1, 0, 5)
        first = Request("same", "CLAIM", "job-1", "worker-a")
        conflicting = Request("same", "CLAIM", "job-2", "worker-b")

        original = queue.apply(first, lease, 1)
        misleading_replay = queue.apply(conflicting, lease, 2)

        self.assertIs(original, misleading_replay)
        self.assertEqual("CLAIMED:worker-b", queue.jobs["job-2"])
        self.assertEqual(1, len(queue.history))

    def test_hypothesis_higher_epoch_self_authorizes(self):
        queue = UnsafeQueue(("job-1",), active_epoch=2)
        forged = Lease("mallory", 99, 0, 100)
        request = Request("forged", "CLAIM", "job-1", "worker-x")

        response = queue.apply(request, forged, 10)

        self.assertEqual(Response("OK_CLAIMED"), response)
        self.assertEqual(99, queue.active_epoch)
        self.assertEqual("CLAIMED:worker-x", queue.jobs["job-1"])

    def test_hypothesis_expiry_operators_disagree_at_boundary(self):
        lease = Lease("alpha", 1, 0, 5)
        unsafe_grant_denies = 5 <= lease.expires_tick
        unsafe_node_accepts = not (5 > lease.expires_tick)

        self.assertTrue(unsafe_grant_denies)
        self.assertTrue(unsafe_node_accepts)
        self.assertFalse(lease.start_tick <= 5 < lease.expires_tick)


if __name__ == "__main__":
    unittest.main()
