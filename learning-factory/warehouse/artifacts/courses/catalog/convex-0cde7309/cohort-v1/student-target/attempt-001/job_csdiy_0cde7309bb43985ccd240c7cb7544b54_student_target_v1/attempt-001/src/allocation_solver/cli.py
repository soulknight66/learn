"""Command-line adapter and exit-code mapping."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .model import (
    ALGORITHM,
    COURSE_ID,
    UNIT_ID,
    VALIDATION_LABEL,
    InvalidInput,
    NumericalFailure,
    Problem,
    parse_input_bytes,
)
from .solver import SolveResult, solve


def _write_json(stream: Any, document: dict[str, Any]) -> None:
    stream.write(
        json.dumps(
            document,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    )


def _error_document(status: str, code: str, message: str) -> dict[str, Any]:
    return {"status": status, "error": {"code": code, "message": message}}


def _result_document(problem: Problem, result: SolveResult, digest: str) -> dict[str, Any]:
    return {
        "status": result.status,
        "allocations": [
            {"id": item.item_id, "amount": amount}
            for item, amount in zip(problem.items, result.allocation)
        ],
        "objective": result.objective,
        "diagnostics": {
            "iterations": result.diagnostics.iterations,
            "tolerance": result.diagnostics.tolerance,
            "fixed_point_residual": result.diagnostics.fixed_point_residual,
            "feasibility_residual": result.diagnostics.feasibility_residual,
        },
        "provenance": {
            "course_id": COURSE_ID,
            "unit_id": UNIT_ID,
            "input_sha256": digest,
            "algorithm": ALGORITHM,
            "validation_label": VALIDATION_LABEL,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        _write_json(
            sys.stderr,
            _error_document(
                "INVALID_INPUT", "INVALID_STRUCTURE", "exactly one input path is required"
            ),
        )
        return 2

    try:
        try:
            raw = Path(arguments[0]).read_bytes()
        except OSError:
            raise InvalidInput("INPUT_READ_ERROR", "input file could not be read") from None

        problem = parse_input_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        result = solve(problem)
        document = _result_document(problem, result, digest)
        _write_json(sys.stdout, document)
        return 0 if result.status == "CONVERGED" else 3
    except InvalidInput as error:
        _write_json(
            sys.stderr,
            _error_document("INVALID_INPUT", error.code, error.message),
        )
        return 2
    except NumericalFailure:
        _write_json(
            sys.stderr,
            _error_document(
                "NUMERICAL_FAILURE",
                "NONFINITE_INTERMEDIATE",
                "numerical result is not finite",
            ),
        )
        return 4
    except Exception:
        _write_json(
            sys.stderr,
            _error_document(
                "INTERNAL_ERROR", "INTERNAL_ERROR", "internal solver failure"
            ),
        )
        return 1
