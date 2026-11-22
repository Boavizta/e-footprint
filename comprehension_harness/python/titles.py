"""The test titles of the Python stack (``comprehension_harness/stack.md`` § 3), read with ``ast``.

    python3 -m comprehension_harness.python.titles < files.json

Reads ``[{file, text}]`` on its input and prints ``[{file, tests, stands, journeyCases}]`` in the same order.
It is asked for a file's text and not for the checkout: the lot check reads a test file on both sides of a
commit.

- A test is a function named ``test_…`` at the top of the file or in a class named ``Test…``. Its title is its
  function's name, or the string of ``@titled("…")`` above it. ``@planned_test("…")`` on a function with an
  empty body is a test to write (``declare.py``).
- A stand is the line that opens a test, a class or another declaration of the file or of a class: its first
  decorator when it has one. A ``@planned`` comment right above that line stands on it.
- Journeys are not drawn from a run here: ``journeyCases`` is always empty.

A file that is not Python has no test and no stand. A Python file the parser refuses, or a title that is not
one string, stops the command with the file and the line.

Standard library only.
"""
import ast
import json
import re
import sys

TITLE_DECORATORS = ("titled", "planned_test")
DEFINITION = re.compile(r"(?:async\s+)?(?:def|class)\s+")


class Refusal(Exception):
    """Something that does not have the contract's shape, said with its file and its line."""


def parse(file: str, text: str) -> ast.Module:
    try:
        return ast.parse(text)
    except SyntaxError as error:
        raise Refusal(f"{file}:{error.lineno} — the Python parser refuses the file: {error.msg}") from None


def name_position(node, lines: list[str]) -> tuple[int, int]:
    """Where the name of a function or of a class is written: the line of its ``def`` and the name's column."""
    keyword = DEFINITION.match(lines[node.lineno - 1], node.col_offset)
    return node.lineno, (keyword.end() if keyword else node.col_offset) + 1


def opening_line(node) -> int:
    """The line that opens a definition: its first decorator's, else its own."""
    return min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))])


def decorator_name(decorator) -> str | None:
    function = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(function, ast.Name):
        return function.id
    return function.attr if isinstance(function, ast.Attribute) else None


def is_test_function(node) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")


def is_test_class(node) -> bool:
    return isinstance(node, ast.ClassDef) and node.name.startswith("Test")


def has_empty_body(function) -> bool:
    """A body that is a docstring, ``pass`` or ``...`` and nothing else."""
    def says_nothing(statement) -> bool:
        return isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)

    return all(isinstance(statement, ast.Pass) or says_nothing(statement) for statement in function.body)


def declared_title(function, file: str) -> tuple[str, bool]:
    """A function's title and whether it is a test to write, as its decorators say; refuses a title that is not
    one string, two titles, a title on a function pytest does not collect, a planned test with a body."""
    found = [d for d in function.decorator_list if decorator_name(d) in TITLE_DECORATORS]
    if not found:
        return function.name, False
    where = f"{file}:{found[0].lineno}"
    if len(found) > 1:
        raise Refusal(f"{where} — a test has one title: @titled(…) or @planned_test(…), not both")
    decorator, kind = found[0], decorator_name(found[0])
    arguments = decorator.args if isinstance(decorator, ast.Call) and not decorator.keywords else []
    if len(arguments) != 1 or not isinstance(arguments[0], ast.Constant) or not isinstance(arguments[0].value, str):
        raise Refusal(f"{where} — @{kind}(…) takes the test's title as one literal string")
    if not function.name.startswith("test_"):
        raise Refusal(f"{where} — @{kind}(…) stands on a test function, and pytest does not collect `{function.name}`")
    if kind == "planned_test" and not has_empty_body(function):
        raise Refusal(f"{where} — @planned_test stands on a test with an empty body; "
                      f"a written test carries its title with @titled(…)")
    return arguments[0].value, kind == "planned_test"


def read(file: str, text: str) -> dict:
    """What one file's text holds: its tests, in file order, and what each of its lines opens."""
    answer = {"file": file, "tests": [], "stands": [], "journeyCases": []}
    if not file.endswith(".py"):
        return answer
    lines = text.split("\n")

    def visit(statements, collected: bool) -> None:
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                title, planned = declared_title(node, file)
                test = collected and is_test_function(node)
                if test:
                    line, column = name_position(node, lines)
                    answer["tests"].append({"title": title, "line": line, "column": column, "planned": planned})
                answer["stands"].append({"line": opening_line(node), "label": f'test "{title}"' if test else node.name,
                                         "test": title if test else None})
            elif isinstance(node, ast.ClassDef):
                answer["stands"].append({"line": opening_line(node), "label": node.name, "test": None})
                visit(node.body, collected and is_test_class(node))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if isinstance(target, ast.Name):
                    answer["stands"].append({"line": node.lineno, "label": target.id, "test": None})

    visit(parse(file, text).body, True)
    return answer


def is_asked_file(one) -> bool:
    return isinstance(one, dict) and all(isinstance(one.get(key), str) for key in ("file", "text"))


def main() -> int:
    try:
        asked = json.load(sys.stdin)
        if not isinstance(asked, list) or not all(is_asked_file(one) for one in asked):
            raise Refusal("the input is not [{file, text}], a file's path and its text each")
        answers = [read(one["file"], one["text"]) for one in asked]
    except json.JSONDecodeError as error:
        print(f"comprehension-titles: the input is not JSON — {error}", file=sys.stderr)
        return 1
    except Refusal as refusal:
        print(f"comprehension-titles: {refusal}", file=sys.stderr)
        return 1
    json.dump(answers, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
