"""随机四则运算公式生成、求值与格式化工具。

这个模块有两个用途：

1. 作为一个小工具：生成随机四则运算公式、安全求值、导出到文件；
2. 作为 git 指令功能测试的随机内容来源：测试脚本会在多个分支、提交之间
   写入不同的随机公式文件，用来验证 add / commit / diff / merge / rebase 等命令。
"""

from __future__ import annotations

import argparse
import ast
import operator
import random
import sys
from dataclasses import dataclass
from pathlib import Path

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_NUMBER_RANGE = (1, 20)
_MAX_DEPTH = 4


@dataclass(frozen=True)
class Formula:
    """一条随机公式：表达式文本和期望值。"""

    expression: str
    expected: float

    def format(self) -> str:
        """返回 ``表达式 = 值`` 形式的文本。"""
        return f"{self.expression} = {self.expected:g}"


def _random_leaf(rng: random.Random) -> tuple[str, float]:
    value = rng.randint(*_NUMBER_RANGE)
    return str(value), float(value)


def _random_expression(rng: random.Random, depth: int) -> tuple[str, float]:
    if depth <= 1:
        return _random_leaf(rng)

    left_text, left_value = _random_expression(rng, depth - 1)
    operator_symbol = rng.choice("+-*/")

    if operator_symbol == "/":
        # 除数固定为非零整数，从生成阶段就避免除零
        divisor = float(rng.randint(1, 9))
        right_text = str(int(divisor))
        value = left_value / divisor
    else:
        right_text, right_value = _random_expression(rng, depth - 1)
        if operator_symbol == "+":
            value = left_value + right_value
        elif operator_symbol == "-":
            value = left_value - right_value
        else:
            value = left_value * right_value

    expression = f"{left_text} {operator_symbol} {right_text}"
    if depth > 1:
        expression = f"({expression})"
    return expression, value


def generate_formula(rng: random.Random | None = None, depth: int = 2) -> Formula:
    """生成一条随机公式。传入相同的 ``rng`` 状态可以得到可复现的结果。"""
    rng = rng or random.Random()
    depth = max(1, min(depth, _MAX_DEPTH))
    expression, value = _random_expression(rng, depth)
    if expression.startswith("(") and expression.endswith(")"):
        expression = expression[1:-1]
    return Formula(expression=expression, expected=round(value, 6))


def generate_formulas(count: int, seed: int | None = None, depth: int = 2) -> list[Formula]:
    """批量生成公式；指定 ``seed`` 时结果可复现。"""
    if count < 0:
        raise ValueError("count 不能为负数")
    rng = random.Random(seed)
    return [generate_formula(rng, depth=depth) for _ in range(count)]


def evaluate(expression: str) -> float:
    """安全求值：只允许数字、括号和 + - * /，拒绝函数调用、变量、幂运算等。"""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError(f"表达式语法错误：{expression}") from error
    return round(float(_evaluate_node(tree.body)), 6)


def _evaluate_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        operator_function = _BINARY_OPERATORS.get(type(node.op))
        if operator_function is None:
            raise ValueError("只支持 + - * / 运算符")
        return operator_function(_evaluate_node(node.left), _evaluate_node(node.right))
    if isinstance(node, ast.UnaryOp):
        operator_function = _UNARY_OPERATORS.get(type(node.op))
        if operator_function is None:
            raise ValueError("不支持的一元运算符")
        return operator_function(_evaluate_node(node.operand))
    raise ValueError(f"不支持的语法节点：{type(node).__name__}")


def write_formulas(path: Path, formulas: list[Formula]) -> Path:
    """把公式逐行写入文件，返回写入的路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(formula.format() for formula in formulas) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="random_formula",
        description="生成随机四则运算公式并求值",
    )
    parser.add_argument("--count", type=int, default=5, help="生成公式的数量（默认 5）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子，指定后结果可复现")
    parser.add_argument("--depth", type=int, default=2, help="表达式嵌套深度（1-4，默认 2）")
    parser.add_argument("--output", type=Path, default=None, help="同时写入指定文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    formulas = generate_formulas(args.count, seed=args.seed, depth=args.depth)
    for formula in formulas:
        print(formula.format())
    if args.output is not None:
        write_formulas(args.output, formulas)
        print(f"已写入 {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
