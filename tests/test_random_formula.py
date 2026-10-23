"""random_formula 的 pytest 测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from random_formula import (
    Formula,
    evaluate,
    generate_formula,
    generate_formulas,
    write_formulas,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_generate_is_deterministic_with_seed() -> None:
    first = [formula.format() for formula in generate_formulas(10, seed=2026)]
    second = [formula.format() for formula in generate_formulas(10, seed=2026)]
    assert first == second


def test_generate_without_seed_produces_formulas() -> None:
    formulas = generate_formulas(20)
    assert len(formulas) == 20
    assert all(isinstance(formula, Formula) for formula in formulas)
    assert all(" " in formula.expression for formula in formulas)


def test_generated_formulas_evaluate_to_expected_value() -> None:
    for formula in generate_formulas(200, seed=42, depth=3):
        assert evaluate(formula.expression) == pytest.approx(formula.expected, abs=1e-6)


def test_generation_never_creates_division_by_zero() -> None:
    # 生成阶段保证除数非零，因此随机生成 300 条也不会触发 ZeroDivisionError
    formulas = generate_formulas(300, seed=7, depth=4)
    for formula in formulas:
        evaluate(formula.expression)


def test_evaluate_respects_operator_precedence() -> None:
    assert evaluate("1 + 2 * 3") == 7
    assert evaluate("(1 + 2) * 3") == 9
    assert evaluate("10 / 4") == 2.5


def test_evaluate_rejects_unsafe_input() -> None:
    unsafe_expressions = [
        "__import__('os').system('dir')",
        "1 ** 2",
        "name + 1",
        "[1, 2, 3]",
        "'text'",
    ]
    for expression in unsafe_expressions:
        with pytest.raises(ValueError):
            evaluate(expression)


def test_evaluate_rejects_invalid_syntax() -> None:
    with pytest.raises(ValueError):
        evaluate("1 +")


def test_generate_formulas_validates_count() -> None:
    with pytest.raises(ValueError):
        generate_formulas(-1)


def test_depth_is_bounded() -> None:
    shallow = generate_formula(depth=1)
    assert "(" not in shallow.expression


def test_write_formulas(tmp_path: Path) -> None:
    formulas = generate_formulas(3, seed=11)
    output = write_formulas(tmp_path / "nested" / "formulas.txt", formulas)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    for line, formula in zip(lines, formulas, strict=True):
        # 去掉空格后比较，避免格式化差异
        assert " = " in line
        expression = line.rsplit(" = ", 1)[0]
        assert expression.replace(" ", "") == formula.expression.replace(" ", "")


def test_cli_generates_requested_count() -> None:
    result = subprocess.run(
        [sys.executable, "random_formula.py", "--count", "4", "--seed", "7"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 4
    for line in lines:
        expression = line.rsplit(" = ", 1)[0]
        evaluate(expression)
