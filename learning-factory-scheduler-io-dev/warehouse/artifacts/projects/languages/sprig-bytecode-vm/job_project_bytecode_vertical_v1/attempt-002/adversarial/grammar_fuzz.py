from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path


OPS = ("+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=", "&&", "||")


def trunc_div(left: int, right: int) -> int:
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def literal(value: int) -> str:
    return str(value) if value >= 0 else f"-{abs(value)}"


def expression(randomizer: random.Random, depth: int) -> tuple[str, int]:
    if depth <= 0 or randomizer.random() < 0.30:
        value = randomizer.randint(-12, 12)
        return literal(value), value
    if randomizer.random() < 0.18:
        source, value = expression(randomizer, depth - 1)
        if randomizer.choice((True, False)):
            return f"(-({source}))", -value
        return f"(!({source}))", int(value == 0)
    left_source, left = expression(randomizer, depth - 1)
    right_source, right = expression(randomizer, depth - 1)
    operator = randomizer.choice(OPS)
    if operator in {"/", "%"} and right == 0:
        right_source, right = "1", 1
    if operator == "+": value = left + right
    elif operator == "-": value = left - right
    elif operator == "*": value = left * right
    elif operator == "/": value = trunc_div(left, right)
    elif operator == "%": value = left - trunc_div(left, right) * right
    elif operator == "<": value = int(left < right)
    elif operator == "<=": value = int(left <= right)
    elif operator == ">": value = int(left > right)
    elif operator == ">=": value = int(left >= right)
    elif operator == "==": value = int(left == right)
    elif operator == "!=": value = int(left != right)
    elif operator == "&&": value = int(left != 0 and right != 0)
    else: value = int(left != 0 or right != 0)
    return f"({left_source} {operator} {right_source})", value


def invoke(path: str, programs: list[str]) -> dict[str, object]:
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": path}
    process = subprocess.run(
        [sys.executable, "adversarial/batch_runner.py"],
        input=json.dumps(programs), text=True, capture_output=True,
        env=environment, timeout=30, check=False,
    )
    if process.returncode:
        raise RuntimeError(f"engine {path} failed: {process.stderr[-500:]}")
    return json.loads(process.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7401)
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    if not 1 <= arguments.iterations <= 500:
        raise SystemExit("iterations must be in [1, 500]")
    randomizer = random.Random(arguments.seed)
    programs, expected = [], []
    for _ in range(arguments.iterations):
        start = randomizer.randint(0, 8)
        scale = randomizer.randint(-6, 6)
        divisor = randomizer.choice(tuple(value for value in range(-7, 8) if value))
        expression_source, expression_value = expression(randomizer, 4)
        total = scale * start * (start + 1) // 2
        quotient = trunc_div(total, divisor)
        remainder = total - quotient * divisor
        programs.append(
            f"""// deterministic generated stateful case
            let n = {start}; let total = 0; let scale = {literal(scale)};
            while (n > 0) {{ total = total + scale * n; n = n - 1; }}
            print total; print total / {literal(divisor)}; print total % {literal(divisor)};
            if ((total > 0 && n == 0) || false) {{ print 1; }} else {{ print 0; }}
            print false && (1 / 0); print true || missing; print {expression_source};
            """
        )
        expected.append(
            {
                "outputs": [total, quotient, remainder, int(total > 0), 0, 1, expression_value],
                "globals": {"n": 0, "scale": scale, "total": total},
            }
        )
    bytecode = invoke("sealed/reference", programs)
    treewalk = invoke("alternatives/treewalk", programs)
    if bytecode["results"] != expected or treewalk["results"] != expected:
        print("differential/oracle mismatch", file=sys.stderr)
        return 1
    output = Path(arguments.output)
    allowed = (Path.cwd() / "reports").resolve()
    try: output.resolve().relative_to(allowed)
    except ValueError: raise SystemExit("output must remain under reports/")
    output.parent.mkdir(parents=True, exist_ok=True)
    corpus = json.dumps(programs, separators=(",", ":"), ensure_ascii=True).encode()
    report = {
        "schema_version": 1, "seed": arguments.seed, "iterations": arguments.iterations,
        "corpus_sha256": hashlib.sha256(corpus).hexdigest(),
        "engines": [bytecode["engine"], treewalk["engine"]],
        "properties": ["independent arithmetic oracle", "cross-architecture agreement", "deterministic stateful grammar corpus"],
        "coverage": {
            "programs": arguments.iterations,
            "features": [
                "declarations", "assignment", "while", "if/else", "comments",
                "division/remainder", "unary", "comparison", "short-circuit",
            ],
        },
        "failures": 0,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"checked {arguments.iterations} deterministic grammar programs; corpus={report['corpus_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
