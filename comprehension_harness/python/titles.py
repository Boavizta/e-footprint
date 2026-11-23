"""The test titles of the Python stack (``comprehension_harness/stack.md`` § 3), read with ``ast``.

    python3 -m comprehension_harness.python.titles < files.json

Reads ``[{file, text}]`` on its input and prints ``[{file, tests, stands, journeyCases}]`` in the same order.
It is asked for a file's text and not for the checkout: the lot check reads a test file on both sides of a
commit.

- A test is a function named ``test_…`` at the top of the file or in a class named ``Test…``. Its title is its
  function's name, or the string of ``@titled("…")`` above it. ``@planned_test("…")`` on a function with an
  empty body is a test to write, and ``@reproduces("…")`` a written test that fails today for a bug to fix
  (``declare.py``).
- A stand is the line that opens a test, a class or another declaration of the file or of a class: its first
  decorator when it has one. A ``@planned`` comment right above that line stands on it.
- A journey case is ``@planned_case("<feature>", "<screen>", "<title>")`` on a test with an empty body, in a
  class under ``@journey("<name>", …)`` (``journey.py``): a case a feature will add to that journey. It is no
  test of the file until it is written. The feature is a string, or a constant of the file holding one.

A file that is not Python has no test and no stand. A Python file the parser refuses, or a title that is not
one string, stops the command with the file and the line.

Standard library only.
"""
import ast
import json
import re
import sys

TITLE_DECORATORS = ("titled", "planned_test", "reproduces")
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


def declared_title(function, file: str) -> tuple[str, str | None]:
    """A function's title and what declares it, ``planned_test`` for a test to write and ``reproduces`` for one
    that fails today, as its decorators say; refuses a title that is not one string, two titles, a title on a
    function pytest does not collect, a planned test with a body, a reproduction without one."""
    found = [d for d in function.decorator_list if decorator_name(d) in TITLE_DECORATORS]
    if not found:
        return function.name, None
    where = f"{file}:{found[0].lineno}"
    if len(found) > 1:
        raise Refusal(f"{where} — a test has one title: @titled(…), @planned_test(…) or @reproduces(…), not two")
    decorator, kind = found[0], decorator_name(found[0])
    arguments = decorator.args if isinstance(decorator, ast.Call) and not decorator.keywords else []
    if len(arguments) != 1 or not isinstance(arguments[0], ast.Constant) or not isinstance(arguments[0].value, str):
        raise Refusal(f"{where} — @{kind}(…) takes the test's title as one literal string")
    if not function.name.startswith("test_"):
        raise Refusal(f"{where} — @{kind}(…) stands on a test function, and pytest does not collect `{function.name}`")
    if kind == "planned_test" and not has_empty_body(function):
        raise Refusal(f"{where} — @planned_test stands on a test with an empty body; "
                      f"a written test carries its title with @titled(…)")
    if kind == "reproduces" and has_empty_body(function):
        raise Refusal(f"{where} — @reproduces stands on a written test, which fails today; "
                      f"a test to write is declared with @planned_test(…)")
    return arguments[0].value, kind


def journey_name(node) -> str | None:
    """The journey a class walks, as ``@journey("<name>", …)`` above it says."""
    for decorator in node.decorator_list:
        if decorator_name(decorator) == "journey" and isinstance(decorator, ast.Call) and decorator.args:
            name = decorator.args[0]
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                return name.value
    return None


def planned_case(function, file: str, journey: str | None, constants: dict[str, str]) -> dict | None:
    """The case a function declares with ``@planned_case(…)``, if it does; refuses one that is not three strings,
    that stands outside a journey, on a function pytest does not collect, on a body, or beside a title."""
    found = [d for d in function.decorator_list if decorator_name(d) == "planned_case"]
    if not found:
        return None
    decorator = found[0]
    where = f"{file}:{decorator.lineno}"

    def string(node) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    arguments = decorator.args if isinstance(decorator, ast.Call) and not decorator.keywords else []
    feature = constants.get(arguments[0].id) if arguments and isinstance(arguments[0], ast.Name) else None
    said = [feature or string(arguments[0]), string(arguments[1]), string(arguments[2])] if len(arguments) == 3 else []
    if len(found) > 1 or len(said) != 3 or not all(said):
        raise Refusal(f"{where} — @planned_case(feature, screen, title) takes three strings, the feature a string "
                      f"or a constant of the file holding one")
    if journey is None:
        raise Refusal(f"{where} — @planned_case stands on a test of a class under @journey(\"<name>\", …)")
    if not function.name.startswith("test_"):
        raise Refusal(f"{where} — @planned_case stands on a test function, and pytest does not collect "
                      f"`{function.name}`")
    if any(decorator_name(d) in TITLE_DECORATORS for d in function.decorator_list) or not has_empty_body(function):
        raise Refusal(f"{where} — @planned_case stands on a test with an empty body; "
                      f"a written case carries its title with @titled(…)")
    return {"feature": said[0], "journey": journey, "screen": said[1], "title": said[2], "file": file,
            "line": decorator.lineno, "column": decorator.col_offset + 1}


def read(file: str, text: str) -> dict:
    """What one file's text holds: its tests, in file order, and what each of its lines opens."""
    answer = {"file": file, "tests": [], "stands": [], "journeyCases": []}
    if not file.endswith(".py"):
        return answer
    lines = text.split("\n")
    tree = parse(file, text)
    constants = {node.targets[0].id: node.value.value for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}

    def visit(statements, collected: bool, journey: str | None) -> None:
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                case = planned_case(node, file, journey, constants)
                if case:
                    answer["journeyCases"].append(case)
                    answer["stands"].append({"line": opening_line(node), "label": f'case "{case["title"]}"',
                                             "test": None})
                    continue
                title, declared_by = declared_title(node, file)
                test = collected and is_test_function(node)
                if test:
                    line, column = name_position(node, lines)
                    answer["tests"].append({"title": title, "line": line, "column": column,
                                            "planned": declared_by == "planned_test",
                                            **({"reproduction": True} if declared_by == "reproduces" else {})})
                answer["stands"].append({"line": opening_line(node), "label": f'test "{title}"' if test else node.name,
                                         "test": title if test else None})
            elif isinstance(node, ast.ClassDef):
                answer["stands"].append({"line": opening_line(node), "label": node.name, "test": None})
                visit(node.body, collected and is_test_class(node), journey_name(node))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                if isinstance(target, ast.Name):
                    answer["stands"].append({"line": node.lineno, "label": target.id, "test": None})

    visit(tree.body, True, None)
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
