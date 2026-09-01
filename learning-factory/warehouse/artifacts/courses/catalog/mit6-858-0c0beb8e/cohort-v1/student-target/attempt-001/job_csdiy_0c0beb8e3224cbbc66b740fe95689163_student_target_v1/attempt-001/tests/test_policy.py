"""Exhaustive examples and invariants for the finite authorization policy."""

import itertools
import unittest
from typing import Tuple

from authz import Action, AuthorizationRequest, Principal, Resource, Role, authorize


def make_request(
    role: Role,
    action: Action,
    same_owner: bool,
    same_tenant: bool,
) -> AuthorizationRequest:
    return AuthorizationRequest(
        principal=Principal("subject-a", "tenant-a", role),
        action=action,
        resource=Resource(
            "resource-a",
            "tenant-a" if same_tenant else "tenant-b",
            "subject-a" if same_owner else "subject-b",
        ),
    )


def expected_decision(
    role: Role,
    action: Action,
    same_owner: bool,
    same_tenant: bool,
) -> Tuple[bool, str]:
    if not same_tenant:
        return False, "deny_cross_tenant"
    if role is Role.ADMIN:
        return True, "allow_admin"
    if role is Role.AUDITOR and action is Action.READ:
        return True, "allow_auditor_read"
    if role is Role.MEMBER and same_owner and action in (Action.READ, Action.WRITE):
        return True, "allow_owner"
    return False, "deny_insufficient_privilege"


class ExhaustivePolicyTests(unittest.TestCase):
    def test_all_36_policy_combinations(self) -> None:
        observed_cases = 0
        dimensions = itertools.product(Role, Action, (False, True), (False, True))
        for role, action, same_owner, same_tenant in dimensions:
            with self.subTest(
                role=role.value,
                action=action.value,
                same_owner=same_owner,
                same_tenant=same_tenant,
            ):
                decision = authorize(make_request(role, action, same_owner, same_tenant))
                expected_allowed, expected_reason = expected_decision(
                    role, action, same_owner, same_tenant
                )
                self.assertIs(type(decision.allowed), bool)
                self.assertEqual(expected_allowed, decision.allowed)
                self.assertEqual(expected_reason, decision.reason)
                self.assertEqual({"allowed", "reason"}, set(decision.as_dict()))
            observed_cases += 1
        self.assertEqual(36, observed_cases)

    def test_cross_tenant_reason_precedes_role_and_ownership_rules(self) -> None:
        apparently_privileged_cases = (
            (Role.ADMIN, Action.DELETE, False),
            (Role.AUDITOR, Action.READ, False),
            (Role.MEMBER, Action.READ, True),
        )
        for role, action, same_owner in apparently_privileged_cases:
            with self.subTest(role=role.value, action=action.value):
                decision = authorize(make_request(role, action, same_owner, False))
                self.assertFalse(decision.allowed)
                self.assertEqual("deny_cross_tenant", decision.reason)

    def test_same_tenant_allowed_reason_codes_are_stable(self) -> None:
        cases = (
            (Role.ADMIN, Action.DELETE, False, "allow_admin"),
            (Role.AUDITOR, Action.READ, False, "allow_auditor_read"),
            (Role.MEMBER, Action.WRITE, True, "allow_owner"),
        )
        for role, action, same_owner, reason in cases:
            with self.subTest(reason=reason):
                decision = authorize(make_request(role, action, same_owner, True))
                self.assertTrue(decision.allowed)
                self.assertEqual(reason, decision.reason)


class PolicyInvariantTests(unittest.TestCase):
    def test_tenant_isolation_invariant(self) -> None:
        for role, action, same_owner in itertools.product(Role, Action, (False, True)):
            with self.subTest(role=role.value, action=action.value, owner=same_owner):
                decision = authorize(make_request(role, action, same_owner, False))
                self.assertEqual((False, "deny_cross_tenant"), (decision.allowed, decision.reason))

    def test_auditor_non_mutation_invariant(self) -> None:
        for action, same_owner in itertools.product((Action.WRITE, Action.DELETE), (False, True)):
            with self.subTest(action=action.value, owner=same_owner):
                decision = authorize(make_request(Role.AUDITOR, action, same_owner, True))
                self.assertEqual(
                    (False, "deny_insufficient_privilege"),
                    (decision.allowed, decision.reason),
                )

    def test_member_ownership_and_delete_invariants(self) -> None:
        for action, same_owner in itertools.product(Action, (False, True)):
            with self.subTest(action=action.value, owner=same_owner):
                decision = authorize(make_request(Role.MEMBER, action, same_owner, True))
                should_allow = same_owner and action in (Action.READ, Action.WRITE)
                self.assertEqual(should_allow, decision.allowed)
                if not should_allow:
                    self.assertEqual("deny_insufficient_privilege", decision.reason)

    def test_admin_same_tenant_invariant(self) -> None:
        for action, same_owner in itertools.product(Action, (False, True)):
            with self.subTest(action=action.value, owner=same_owner):
                decision = authorize(make_request(Role.ADMIN, action, same_owner, True))
                self.assertEqual((True, "allow_admin"), (decision.allowed, decision.reason))


if __name__ == "__main__":
    unittest.main()
