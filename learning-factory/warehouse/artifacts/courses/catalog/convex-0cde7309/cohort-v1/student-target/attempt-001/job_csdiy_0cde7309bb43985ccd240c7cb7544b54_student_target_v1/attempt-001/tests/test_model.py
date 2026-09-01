import math
import unittest

from allocation_solver.model import (
    InvalidInput,
    NumericalFailure,
    gradient,
    objective,
    parse_input_bytes,
    validate_input,
)


def valid_document():
    return {
        "budget": 1.0,
        "items": [
            {"id": "api", "weight": 1.0, "target": 0.8},
            {"id": "batch", "weight": 2.0, "target": 0.4},
        ],
        "solver": {"tolerance": 1e-9, "max_iterations": 10000},
    }


class InputValidationTests(unittest.TestCase):
    def assert_code(self, document, code):
        with self.assertRaises(InvalidInput) as caught:
            validate_input(document)
        self.assertEqual(caught.exception.code, code)

    def test_malformed_json_and_utf8_are_invalid_json(self):
        for raw in (b"{", b"{} trailing", b"\xff"):
            with self.subTest(raw=raw):
                with self.assertRaises(InvalidInput) as caught:
                    parse_input_bytes(raw)
                self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_structure_defects(self):
        cases = [
            [],
            {},
            {"budget": 1, "items": [], "solver": {}},
            {"budget": 1, "items": [{}], "solver": {}},
            {
                "budget": 1,
                "items": [{"id": "x", "weight": 1, "target": 0}],
                "solver": [],
            },
        ]
        for document in cases:
            with self.subTest(document=document):
                self.assert_code(document, "INVALID_STRUCTURE")

    def test_wrong_or_nonfinite_numeric_values(self):
        cases = []
        for field, value in (("budget", True), ("budget", "1"), ("budget", math.inf)):
            document = valid_document()
            document[field] = value
            cases.append(document)

        document = valid_document()
        document["items"][0]["weight"] = None
        cases.append(document)
        document = valid_document()
        document["items"][0]["target"] = math.nan
        cases.append(document)
        document = valid_document()
        document["solver"]["tolerance"] = -math.inf
        cases.append(document)
        document = valid_document()
        document["solver"]["max_iterations"] = True
        cases.append(document)
        document = valid_document()
        document["solver"]["max_iterations"] = 2.5
        cases.append(document)

        for document in cases:
            with self.subTest(document=document):
                self.assert_code(document, "INVALID_NUMERIC")

    def test_range_defects(self):
        mutations = [
            lambda d: d.__setitem__("budget", -1),
            lambda d: d["items"][0].__setitem__("weight", 0),
            lambda d: d["items"][0].__setitem__("weight", -2),
            lambda d: d["solver"].__setitem__("tolerance", 0),
            lambda d: d["solver"].__setitem__("tolerance", 0.00101),
            lambda d: d["solver"].__setitem__("max_iterations", 0),
            lambda d: d["solver"].__setitem__("max_iterations", 1_000_001),
        ]
        for mutation in mutations:
            document = valid_document()
            mutation(document)
            with self.subTest(document=document):
                self.assert_code(document, "INVALID_RANGE")

    def test_item_id_defects(self):
        cases = []
        for bad_id in ("", 7, None):
            document = valid_document()
            document["items"][0]["id"] = bad_id
            cases.append(document)
        document = valid_document()
        document["items"][1]["id"] = document["items"][0]["id"]
        cases.append(document)
        for document in cases:
            with self.subTest(document=document):
                self.assert_code(document, "INVALID_ITEM_ID")

    def test_precedence_checks_numeric_before_range_before_id(self):
        document = valid_document()
        document["budget"] = True
        document["items"][0]["weight"] = 0
        document["items"][0]["id"] = ""
        self.assert_code(document, "INVALID_NUMERIC")

        document["budget"] = 1
        self.assert_code(document, "INVALID_RANGE")

    def test_huge_finite_integer_is_valid_syntax_but_unrepresentable(self):
        document = valid_document()
        document["budget"] = 10**400
        with self.assertRaises(NumericalFailure):
            validate_input(document)


class MathematicalPrimitiveTests(unittest.TestCase):
    def test_gradient_and_objective(self):
        problem = validate_input(valid_document())
        allocation = (0.25, 0.75)
        self.assertEqual(gradient(problem, allocation), (-0.55, 0.7))
        self.assertAlmostEqual(objective(problem, allocation), 0.27375)

    def test_length_mismatch_is_programmer_error(self):
        problem = validate_input(valid_document())
        with self.assertRaises(ValueError):
            objective(problem, (1.0,))
        with self.assertRaises(ValueError):
            gradient(problem, (1.0,))


if __name__ == "__main__":
    unittest.main()

