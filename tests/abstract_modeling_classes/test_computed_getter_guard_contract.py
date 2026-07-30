import ast
from pathlib import Path
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_PACKAGE = PROJECT_ROOT / "efootprint"
COMPUTED_DECORATORS = {"computed_attribute", "computed_dict"}


def _computed_decorator(function: ast.FunctionDef):
    for decorator in function.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id in COMPUTED_DECORATORS:
            return decorator
    return None


def _is_guard(function: ast.FunctionDef, decorator) -> bool:
    if function.name.endswith("_validation"):
        return True
    if not isinstance(decorator, ast.Call):
        return False
    return any(
        keyword.arg == "guard"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in decorator.keywords
    )


class _DirectFailureFinder(ast.NodeVisitor):
    """Find explicit failures in one getter without entering nested functions or classes."""

    def __init__(self):
        self.failures = []

    def visit_Raise(self, node):
        self.failures.append(node)

    def visit_Assert(self, node):
        self.failures.append(node)

    def visit_FunctionDef(self, node):
        pass

    def visit_AsyncFunctionDef(self, node):
        pass

    def visit_Lambda(self, node):
        pass

    def visit_ClassDef(self, node):
        pass


def _direct_failures(function: ast.FunctionDef):
    finder = _DirectFailureFinder()
    for statement in function.body:
        finder.visit(statement)
    return finder.failures


class TestComputedGetterGuardContract(TestCase):
    def test_getters_with_explicit_failures_are_guards(self):
        """Test computed getters with direct raise or assert statements are declared as guards."""
        violations = []
        for source_path in sorted(PRODUCTION_PACKAGE.rglob("*.py")):
            source = source_path.read_text()
            tree = ast.parse(source, filename=str(source_path))
            for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
                decorator = _computed_decorator(function)
                failures = _direct_failures(function) if decorator is not None else []
                if failures and not _is_guard(function, decorator):
                    relative_path = source_path.relative_to(PROJECT_ROOT)
                    failure_lines = ", ".join(str(node.lineno) for node in failures)
                    violations.append(
                        f"{relative_path}:{function.lineno} {function.name} "
                        f"(failure lines: {failure_lines})"
                    )

        self.assertEqual(
            [],
            violations,
            "Computed getters with intentional direct failures must use guard=True or have a "
            "name ending in _validation. This static contract detects direct raise/assert "
            "statements only; it cannot detect exceptions raised transitively by called code.\n"
            + "\n".join(violations),
        )
