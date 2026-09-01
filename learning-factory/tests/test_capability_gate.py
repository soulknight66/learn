from __future__ import annotations

import hashlib
import unittest

from learnfactory.capability_gate import build_codex_backend_gate_job_spec
from learnfactory.util import canonical_json


class CapabilityGateSpecificationTests(unittest.TestCase):
    def test_released_payload_and_full_spec_fingerprints_are_frozen(self) -> None:
        spec = build_codex_backend_gate_job_spec()
        current, legacy = spec.released_payloads

        self.assertEqual(
            "950bb0e77bd8dd5ba9c869855f5a1390e769b640be45b856e87455d0000d60b2",
            self._digest(current),
        )
        self.assertEqual(
            "4b79ce5f5b2824bb624084b5d536079935d8c5e485da54603c1be3ad77a2cebc",
            self._digest(legacy),
        )
        self.assertEqual(
            "71ca5cf7484921a2d73642e86c7e7abe43d4d0ad99632bc90b7c44a173676dd8",
            self._digest(spec.normalized_identity(payload=current)),
        )
        self.assertEqual(
            "7bf054e289c5755eaacf5b5ae7d14080913498374282e186c59989e7a0ede0f6",
            self._digest(spec.normalized_identity(payload=legacy)),
        )

    def test_specs_are_fresh_and_cannot_mutate_the_registry(self) -> None:
        first = build_codex_backend_gate_job_spec()
        first.payload["prompt"] = "mutated"
        first.released_payloads[0]["validators"].clear()

        second = build_codex_backend_gate_job_spec()
        self.assertNotEqual("mutated", second.payload["prompt"])
        self.assertEqual(2, len(second.released_payloads[0]["validators"]))

    @staticmethod
    def _digest(value: object) -> str:
        return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
