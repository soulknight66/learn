from __future__ import annotations

import json
import unittest


class ByoxRelocationCutoverTests(unittest.TestCase):
    """Legacy retirement uses stored observations without trusting material."""

    def _fixture(self):
        # Import inside the helper so unittest discovery does not re-export and
        # duplicate the comprehensive cutover contract class.
        from tests.test_byox_s2_cutover import ByoxS2CutoverTests

        fixture = ByoxS2CutoverTests(
            "test_exact_six_validator_blocked_graph_is_fully_retired"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    @staticmethod
    def _relocate(fixture) -> None:
        from tests.test_byox_s2_cutover import SOURCE_ID

        with fixture.database.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE sources SET name=?,path=?,upstream_url=?
                WHERE source_id=?
                """,
                (
                    "Relocated Build Your Own X",
                    "/another/authorized/checkout",
                    "https://mirror.example.invalid/byox.git",
                    SOURCE_ID,
                ),
            )

    def test_relocated_ready_legacy_graph_is_atomically_retired(self) -> None:
        fixture = self._fixture()
        spec = fixture._legacy_spec()
        payload = fixture._legacy_payload(6)
        builder_id = fixture._create_legacy_builder(
            payload, state="READY", attempted=False
        )
        reviewer_id = fixture._create_legacy_reviewer(spec, payload)
        self._relocate(fixture)

        result = fixture._seed()

        self.assertEqual(2, result["created_jobs"])
        self.assertEqual("CANCELLED", fixture.jobs.get(builder_id)["state"])
        self.assertEqual("CANCELLED", fixture.jobs.get(reviewer_id)["state"])

    def test_relocated_terminal_builder_still_authenticates_queued_reviewer(
        self,
    ) -> None:
        fixture = self._fixture()
        spec = fixture._legacy_spec()
        payload = fixture._legacy_payload(6)
        builder_id = fixture._create_legacy_builder(
            payload, state="DISCOVERED", attempted=False
        )
        reviewer_id = fixture._create_legacy_reviewer(spec, payload)
        fixture.jobs.cancel(builder_id)
        self._relocate(fixture)

        result = fixture._seed()

        self.assertEqual(2, result["created_jobs"])
        self.assertEqual("CANCELLED", fixture.jobs.get(builder_id)["state"])
        self.assertEqual("CANCELLED", fixture.jobs.get(reviewer_id)["state"])

    def test_forged_historical_observations_material_and_prompts_write_nothing(
        self,
    ) -> None:
        attacks = (
            "material",
            "project-material",
            "builder-prompt",
            "reviewer-prompt",
            "builder-model",
            "reviewer-model",
            "builder-dependency",
            "reviewer-dependency",
            "nul-locator",
            "oversized-locator",
        )
        for attack in attacks:
            with self.subTest(attack=attack):
                fixture = self._fixture()
                spec = fixture._legacy_spec()
                payload = fixture._legacy_payload(6)
                builder_id = fixture._create_legacy_builder(
                    payload, state="READY", attempted=False
                )
                reviewer_id = fixture._create_legacy_reviewer(spec, payload)
                self._relocate(fixture)
                if attack in {"builder-dependency", "reviewer-dependency"}:
                    fixture.jobs.create(
                        "forged-dependency",
                        "test",
                        {},
                        job_id=f"job_forged_{attack.replace('-', '_')}",
                    )
                with fixture.database.transaction(immediate=True) as connection:
                    if attack in {"builder-model", "reviewer-model"}:
                        target = (
                            builder_id if attack == "builder-model" else reviewer_id
                        )
                        connection.execute(
                            "UPDATE jobs SET model='gpt-5.6-terra' WHERE job_id=?",
                            (target,),
                        )
                        attacked = None
                    elif attack in {"builder-dependency", "reviewer-dependency"}:
                        target = (
                            builder_id
                            if attack == "builder-dependency"
                            else reviewer_id
                        )
                        forged = f"job_forged_{attack.replace('-', '_')}"
                        connection.execute(
                            """
                            UPDATE job_dependencies SET depends_on_job_id=?
                            WHERE job_id=? AND depends_on_job_id=(
                                SELECT MIN(depends_on_job_id)
                                FROM job_dependencies WHERE job_id=?
                            )
                            """,
                            (forged, target, target),
                        )
                        attacked = None
                    else:
                        target = builder_id
                        row = connection.execute(
                            "SELECT payload_json FROM jobs WHERE job_id=?", (target,)
                        ).fetchone()
                        attacked = json.loads(row["payload_json"])
                    if attack == "material":
                        attacked["provenance"]["source"]["commit_hash"] = "forged"
                    elif attack == "project-material":
                        attacked["provenance"]["project"]["title"] = "Forged"
                    elif attack == "builder-prompt":
                        attacked["prompt"] += "\nforged"
                    elif attack == "reviewer-prompt":
                        target = reviewer_id
                        row = connection.execute(
                            "SELECT payload_json FROM jobs WHERE job_id=?", (target,)
                        ).fetchone()
                        attacked = json.loads(row["payload_json"])
                        attacked["prompt"] += "\nforged"
                    elif attack == "nul-locator":
                        attacked["provenance"]["source"]["path"] = "/tmp/forged\0path"
                    else:
                        if attack == "oversized-locator":
                            attacked["provenance"]["source"]["path"] = (
                                "/" + "x" * 8_001
                            )
                    if attacked is not None:
                        connection.execute(
                            "UPDATE jobs SET payload_json=? WHERE job_id=?",
                            (
                                json.dumps(
                                    attacked,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ),
                                target,
                            ),
                        )
                before = fixture._database_dump()

                with self.assertRaisesRegex(
                    RuntimeError, "exact released definition"
                ):
                    fixture._seed()

                self.assertEqual(before, fixture._database_dump())


if __name__ == "__main__":
    unittest.main()
