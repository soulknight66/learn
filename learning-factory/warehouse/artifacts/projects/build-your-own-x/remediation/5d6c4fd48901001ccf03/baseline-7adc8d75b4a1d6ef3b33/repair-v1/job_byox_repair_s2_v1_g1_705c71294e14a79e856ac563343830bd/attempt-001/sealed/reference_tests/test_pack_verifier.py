import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from environment import verify_pack


class ProvenanceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "environment").mkdir()
        self.provenance = self.root / "PROVENANCE.json"
        self.provenance.write_bytes((verify_pack.ROOT / "PROVENANCE.json").read_bytes())
        (self.root / "environment/PROVENANCE.sha256").write_text(
            f"{verify_pack.EXPECTED_PROVENANCE_DOCUMENT_SHA256}  PROVENANCE.json\n",
            encoding="ascii",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_accepts_the_exact_canonical_document(self):
        self.assertEqual(verify_pack._provenance_document_errors(self.root), [])

    def test_rejects_semantic_edit_even_with_recomputed_declaration(self):
        value = json.loads(self.provenance.read_bytes())
        value["classification"] = "edited while snapshot id is unchanged"
        changed = (json.dumps(value, indent=2) + "\n").encode("utf-8")
        self.provenance.write_bytes(changed)
        changed_digest = hashlib.sha256(changed).hexdigest()
        (self.root / "environment/PROVENANCE.sha256").write_text(
            f"{changed_digest}  PROVENANCE.json\n", encoding="ascii"
        )

        errors = verify_pack._provenance_document_errors(self.root)

        self.assertIn("PROVENANCE.json byte digest differs from canonical document", errors)
        self.assertIn(
            "provenance document digest declaration differs from canonical digest", errors
        )


if __name__ == "__main__":
    unittest.main()
