"""The source index of the Python stack (``comprehension_harness/stack.md`` § 2), built on ``ast``.

    python3 -m comprehension_harness.python.source_index

Prints the index as one JSON document (``SourceIndexDocument`` of ``comprehension_harness/stack.ts``): every
Python file of the source folders (``source.app`` of ``comprehension.config.json``) and every test file that
declares a narrative or holds a site, each with its sites, functions, declarations, imports, locals and uses.

What this stack knows and the tools do not:

- the three calls are those of the project's own copy of ``narrate.py``, the module ``stack.calls`` of the
  configuration names, imported by name; a function of the same name from anywhere else is no site;
- a narrative is a test class under ``@narrative("…")`` of ``declare.py``; its summary is the first
  paragraph of the class docstring, its first test the first ``test_…`` method;
- a function is named by its ``__qualname__``, which is what a frame of a story prints.

A parser gives names, not identities. A reference is placed at its declaration when Python's own scoping says
where the name is bound: a top-level declaration of the file, an import followed to the file it names (through
a package's re-exports), ``module.name`` on an imported module, ``self.name`` and ``cls.name`` on the class
around them, a function or class of an enclosing function. A call on a value of unknown type is left out.

Refused, with the file and the line: a file the parser refuses, a call imported from the reference and not
from the project's copy, two calls on one line, a tag or a sentence
that is no literal string, a watch that is no lambda, a tag that is not ``<feature>#<slug>``, a shell that
raises anything but ``planned: <tag>``, a narrative that is not declared on a class under one literal title.

The literal and the lambda are what keeps the calls inert in production: Python computes a call's arguments
before the call, and a call does nothing there. A literal and a lambda cost nothing to compute.

Options, for a tree that is not this repository (the stack's own tests): ``--root``, ``--config`` and
``--declare``, the module the declarations are imported from.

Standard library only.
"""
import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

from .titles import Refusal, declared_title, is_test_function, name_position, parse

CONFIG_FILE = "comprehension.config.json"
REFERENCE_CALLS = "comprehension_harness.python.narrate"
DECLARE_MODULE = "comprehension_harness.python.declare"
KINDS = {"narrate": "step", "event": "event", "planned": "planned"}
PLANNED_TAG = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)#([a-z0-9]+(?:-[a-z0-9]+)*)$")
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
# What has names of its own. A list, set or dict comprehension runs in its function's frame; a generator
# expression and a lambda in a frame with no name.
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
SCOPES = (*FUNCTIONS, ast.ClassDef, ast.Lambda, *COMPREHENSIONS)
SKIPPED_FOLDERS = ("__pycache__", "node_modules")


def literal_argument(call: ast.Call, at: int) -> str | None:
    """A call's argument at a position when it is a literal string, else None."""
    argument = call.args[at] if len(call.args) > at else None
    return argument.value if isinstance(argument, ast.Constant) and isinstance(argument.value, str) else None


def scope_walk(nodes):
    """Every node under ``nodes`` that belongs to their scope: a nested scope is given and not entered."""
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, SCOPES):
            stack.extend(reversed(list(ast.iter_child_nodes(node))))


class Binding:
    """What a name is bound to in a scope: a declaration (``at``), an imported name (``source``: the module's
    dotted name and the name there) or an imported module (``module``: its dotted name)."""

    def __init__(self, name, line=None, column=None, source=None, module=None, definition=False):
        self.name, self.line, self.column = name, line, column
        self.source, self.module, self.definition = source, module, definition

    @property
    def declared_here(self) -> bool:
        """A declaration with a place in its file: no import, and no name whose place the parser does not give."""
        return self.line is not None and not self.source and not self.module


class Scope:
    def __init__(self, kind: str, qualname: str | None = None):
        self.kind, self.qualname = kind, qualname
        self.bindings: dict[str, Binding] = {}
        self.outer_names: set[str] = set()

    def bind(self, binding: Binding) -> None:
        self.bindings.setdefault(binding.name, binding)


class Module:
    """One file, parsed: its dotted name, its tree and the names its top level binds."""

    def __init__(self, file: str, text: str):
        self.file, self.lines = file, text.split("\n")
        self.tree = parse(file, text)
        parts = file[:-len(".py")].split("/")
        self.is_package = parts[-1] == "__init__"
        self.package = parts[:-1]
        self.name = ".".join(self.package if self.is_package else parts)
        self.scope = Scope("module")
        collect_bindings(self, self.scope, self.tree.body)

    def absolute(self, level: int, module: str | None) -> str | None:
        """The dotted name a ``from`` clause names, a relative one read from this file's package."""
        if level == 0:
            return module
        if level - 1 > len(self.package):
            return None
        base = self.package[:len(self.package) - (level - 1)]
        return ".".join([*base, *([module] if module else [])])


def collect_bindings(module: Module, scope: Scope, statements) -> None:
    """The names the statements of one scope bind, each at its first binding."""
    for node in scope_walk(statements):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            scope.outer_names.update(node.names)
        elif isinstance(node, (*FUNCTIONS, ast.ClassDef)):
            scope.bind(Binding(node.name, *name_position(node, module.lines), definition=True))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            scope.bind(Binding(node.id, node.lineno, node.col_offset + 1))
        elif isinstance(node, ast.ExceptHandler) and node.name:
            written = re.search(rf"\bas\s+({re.escape(node.name)})\b", module.lines[node.lineno - 1])
            scope.bind(Binding(node.name, *((node.lineno, written.start(1) + 1) if written else (None, None))))
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            scope.bind(Binding(node.name, node.end_lineno, node.end_col_offset - len(node.name) + 1))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                # `import a.b` binds `a`; `import a.b as c` binds `c` to `a.b`.
                package = alias.name.split(".")[0]
                scope.bind(Binding(alias.asname or package, module=alias.name if alias.asname else package))
        elif isinstance(node, ast.ImportFrom):
            source = module.absolute(node.level, node.module)
            for alias in node.names:
                if alias.name != "*" and source is not None:
                    scope.bind(Binding(alias.asname or alias.name, source=(source, alias.name)))
    for name in scope.outer_names:
        scope.bindings.pop(name, None)


class Source:
    """The files of the index, by path, and what a dotted name leads to among them."""

    def __init__(self, modules: dict[str, Module]):
        self.modules = modules
        self.by_name = {module.name: module for module in modules.values()}

    def declaration(self, module_name: str, name: str, seen=()) -> dict | None:
        """Where ``name`` of a module is declared, followed through the names that module imports."""
        module = self.by_name.get(module_name)
        binding = module.scope.bindings.get(name) if module else None
        if binding is None or (module_name, name) in seen:
            return None
        if binding.source:
            return self.declaration(*binding.source, seen=(*seen, (module_name, name)))
        if binding.module or binding.line is None:
            return None
        return {"file": module.file, "line": binding.line, "column": binding.column}

    def dotted(self, binding: Binding) -> str | None:
        """The dotted name a binding stands for when it is a module: `import a.b as c`, `from a import b`."""
        if binding.module:
            return binding.module
        if binding.source and self.declaration(*binding.source) is None:
            return f"{binding.source[0]}.{binding.source[1]}"
        return None


class FileIndex(ast.NodeVisitor):
    """One file's tables, read in one walk that keeps Python's scopes."""

    def __init__(self, module: Module, source: Source, calls: str, declare: str, is_test: bool):
        self.module, self.source, self.calls, self.declare, self.is_test = module, source, calls, declare, is_test
        self.file, self.lines = module.file, module.lines
        self.scopes: list[Scope] = [module.scope]
        self.classes: list[Scope] = []
        self.sites, self.functions, self.locals, self.uses, self.narratives = [], [], [], [], []
        self.site_lines: dict[int, str] = {}
        self.generic_visit(module.tree)
        self.declarations = self.placed(b for b in module.scope.bindings.values() if b.declared_here)
        self.imports = [{"name": b.name, "at": at} for b in self.all_imports() if (at := source.declaration(*b.source))]

    def tables(self) -> dict:
        ordered = lambda rows: sorted(rows, key=lambda row: (row["line"], row["column"]))  # noqa: E731
        return {"sites": ordered(self.sites), "functions": ordered(self.functions), "declarations": self.declarations,
                "imports": self.imports, "locals": ordered(self.locals), "uses": ordered(self.uses)}

    @staticmethod
    def placed(bindings) -> list[dict]:
        rows = [{"name": b.name, "line": b.line, "column": b.column} for b in bindings]
        return sorted(rows, key=lambda row: (row["line"], row["column"]))

    def all_imports(self) -> list[Binding]:
        """Every imported name of the file, wherever the import stands, each name once, in source order."""
        found: dict[str, Binding] = {}
        for node in ast.walk(self.module.tree):
            if isinstance(node, ast.ImportFrom) and (source := self.module.absolute(node.level, node.module)):
                for alias in node.names:
                    name = alias.asname or alias.name
                    found.setdefault(name, Binding(name, source=(source, alias.name)))
        return list(found.values())

    def refuse(self, node, what: str):
        raise Refusal(f"{self.file}:{node.lineno} — {what}")

    # ── Scopes ──────────────────────────────────────────────────────────────────────────────────────

    def lookup(self, name: str) -> tuple[Scope, Binding] | None:
        """The binding a name read here refers to, as Python finds it: the scopes around, innermost first, a
        class's names being seen from its own body only."""
        for depth, scope in enumerate(reversed(self.scopes)):
            if name in scope.outer_names or (scope.kind == "class" and depth > 0):
                continue
            if name in scope.bindings:
                return scope, scope.bindings[name]
        return None

    def qualname(self, name: str) -> str:
        """The ``__qualname__`` of a function or a class defined here."""
        for scope in reversed(self.scopes):
            if scope.kind == "function":
                return f"{scope.qualname}.<locals>.{name}"
            if scope.kind == "class":
                return f"{scope.qualname}.{name}"
        return name

    def frame_name(self) -> str:
        """The function a call here runs in, named as its frame is."""
        for scope in reversed(self.scopes):
            if scope.kind in ("function", "class"):
                return scope.qualname
            if scope.kind == "anonymous":
                return "(anonymous)"
        return "(module)"

    def enter(self, scope: Scope, inside) -> None:
        self.locals.extend(self.placed(b for b in scope.bindings.values() if b.declared_here))
        self.scopes.append(scope)
        if scope.kind == "class":
            self.classes.append(scope)
        for node in inside:
            self.visit(node)
        if scope.kind == "class":
            self.classes.pop()
        self.scopes.pop()

    def visit_all(self, nodes) -> None:
        for node in nodes:
            if node is not None:
                self.visit(node)

    def visit_signature(self, node) -> list[ast.arg]:
        """The parts of a function's header that are read where it is defined; returns its parameters."""
        arguments = node.args
        parameters = [*arguments.posonlyargs, *arguments.args, *([arguments.vararg] if arguments.vararg else []),
                      *arguments.kwonlyargs, *([arguments.kwarg] if arguments.kwarg else [])]
        self.visit_all([*arguments.defaults, *arguments.kw_defaults, *(p.annotation for p in parameters)])
        return parameters

    def visit_FunctionDef(self, node) -> None:
        self.visit_all(node.decorator_list)
        parameters = self.visit_signature(node)
        self.visit_all([node.returns])
        if any(self.narrative_decorator(d) for d in node.decorator_list):
            self.refuse(node, "a narrative is declared on a test class, not on a function")
        line, column = name_position(node, self.lines)
        scope = Scope("function", self.qualname(node.name))
        self.functions.append({"fn": scope.qualname, "line": line, "column": column, "endLine": node.end_lineno})
        for parameter in parameters:
            scope.bind(Binding(parameter.arg, parameter.lineno, parameter.col_offset + 1))
        collect_bindings(self.module, scope, node.body)
        self.enter(scope, node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node) -> None:
        scope = Scope("anonymous")
        for parameter in self.visit_signature(node):
            scope.bind(Binding(parameter.arg, parameter.lineno, parameter.col_offset + 1))
        self.enter(scope, [node.body])

    def visit_ClassDef(self, node) -> None:
        self.visit_all([*node.decorator_list, *node.bases, *(keyword.value for keyword in node.keywords)])
        for decorator in node.decorator_list:
            if self.narrative_decorator(decorator):
                self.narratives.append(self.narrative(node, decorator))
        scope = Scope("class", self.qualname(node.name))
        collect_bindings(self.module, scope, node.body)
        self.enter(scope, node.body)

    def visit_comprehension_scope(self, node) -> None:
        # The first iterable is read where the comprehension stands, the rest inside it.
        first, *others = node.generators
        self.visit(first.iter)
        scope = Scope("anonymous" if isinstance(node, ast.GeneratorExp) else "comprehension")
        collect_bindings(self.module, scope, [generator.target for generator in node.generators])
        results = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
        self.enter(scope, [*first.ifs, *(part for g in others for part in (g.iter, *g.ifs)), *results])

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_comprehension_scope

    # ── References ──────────────────────────────────────────────────────────────────────────────────

    def use(self, name: str, line: int, column: int, at: dict | None) -> None:
        if at is not None and not (at["file"] == self.file and at["line"] == line and at["column"] == column):
            self.uses.append({"name": name, "line": line, "column": column, "at": at})

    def placed_at(self, scope: Scope, binding: Binding) -> dict | None:
        """The declaration a binding leads to, when a reference to it is one the index lists: a top-level
        declaration, an imported one, a function or a class of an enclosing scope."""
        if binding.source:
            return self.source.declaration(*binding.source)
        if binding.module or binding.line is None or not (scope.kind == "module" or binding.definition):
            return None
        return {"file": self.file, "line": binding.line, "column": binding.column}

    def visit_Name(self, node) -> None:
        found = self.lookup(node.id) if isinstance(node.ctx, ast.Load) else None
        if found:
            self.use(node.id, node.lineno, node.col_offset + 1, self.placed_at(*found))

    def dotted_of(self, node) -> str | None:
        """The dotted name an expression spells, from an imported module on: `pricing`, `shop.pricing`."""
        if isinstance(node, ast.Name):
            found = self.lookup(node.id)
            return self.source.dotted(found[1]) if found else None
        if isinstance(node, ast.Attribute):
            package = self.dotted_of(node.value)
            return f"{package}.{node.attr}" if package else None
        return None

    def module_of(self, node) -> str | None:
        """The module of the index an expression names."""
        dotted = self.dotted_of(node)
        return dotted if dotted in self.source.by_name else None

    def visit_Attribute(self, node) -> None:
        line, column = node.end_lineno, node.end_col_offset - len(node.attr) + 1
        owner = node.value
        module = self.module_of(owner) if isinstance(node.ctx, ast.Load) else None
        if module:
            self.use(node.attr, line, column, self.source.declaration(module, node.attr))
            return
        on_own_class = isinstance(owner, ast.Name) and owner.id in ("self", "cls") and self.classes
        if isinstance(node.ctx, ast.Load) and on_own_class:
            member = self.classes[-1].bindings.get(node.attr)
            if member and member.declared_here:
                self.use(node.attr, line, column, {"file": self.file, "line": member.line, "column": member.column})
        self.generic_visit(node)

    # ── Sites ───────────────────────────────────────────────────────────────────────────────────────

    def imported_as(self, node, module: str) -> str | None:
        """The name a ``Name`` was imported under from ``module``, when that is where it comes from."""
        found = self.lookup(node.id) if isinstance(node, ast.Name) else None
        source = found[1].source if found else None
        return source[1] if source and source[0] == module else None

    def call_kind(self, node: ast.Call) -> tuple[str, bool] | None:
        """The kind of site a call is and whether it is ``planned.remove``; None for any other call."""
        callee = node.func
        if isinstance(callee, ast.Attribute):
            if self.imported_as(callee.value, self.calls) == "planned" and callee.attr == "remove":
                return "planned", True
            if callee.attr in KINDS and self.dotted_of(callee.value) == self.calls:
                self.refuse(node, f"the calls are imported by name: from {self.calls} import {callee.attr}")
            return None
        kind = KINDS.get(self.imported_as(callee, self.calls) or "")
        if kind is None and self.calls != REFERENCE_CALLS and self.imported_as(callee, REFERENCE_CALLS) in KINDS:
            self.refuse(node, f"the calls are imported from this project's copy, {self.calls}, not from the reference")
        return (kind, False) if kind else None

    def visit_Call(self, node) -> None:
        found = self.call_kind(node)
        if found is None:
            self.generic_visit(node)
            return
        # A site, and nothing inside it is read as a use: a watch is documentation.
        kind, removes = found
        if node.lineno in self.site_lines:
            self.refuse(node, f"one narrate, event or planned call a line: a site is a file and a line, and this "
                              f"line already holds a {self.site_lines[node.lineno]}")
        self.site_lines[node.lineno] = kind
        literals = 2 if kind == "planned" else 1
        site = {"kind": kind, "line": node.lineno, "column": node.col_offset + 1, "fn": self.frame_name(),
                "sentence": literal_argument(node, literals - 1)}
        if kind == "planned":
            site["planned"] = self.planned(node, literal_argument(node, 0), site["sentence"], removes)
        elif site["sentence"] is None:
            self.refuse(node, "the sentence of a narrate or event call is a literal string: anything else is "
                              "computed in production, where the call does nothing")
        for argument in [*node.args[literals:], *(keyword.value for keyword in node.keywords)]:
            if not isinstance(argument, ast.Lambda):
                self.refuse(argument, "the watch is a lambda (lambda: {…}): anything else is computed in production, "
                                      "where nobody reads it")
        self.sites.append(site)

    def planned(self, node: ast.Call, tag: str | None, sentence: str | None, removes: bool) -> dict:
        if tag is None or sentence is None:
            self.refuse(node, 'planned(…) needs a literal "<feature>#<slug>" and a literal sentence')
        parsed = PLANNED_TAG.match(tag)
        if parsed is None:
            self.refuse(node, f'"{tag}" is not <feature>#<slug>, two kebab-case names around one #')
        piece = {"feature": parsed.group(1), "slug": parsed.group(2)}
        if removes:
            return {**piece, "change": "removed", "signature": None}
        shell = self.shell_around(node)
        if shell is None:
            return {**piece, "change": "changed", "signature": None}
        raised = shell.body[-1].exc
        said = literal_argument(raised, 0) if isinstance(raised, ast.Call) else None
        if said != f"planned: {tag}":
            self.refuse(shell.body[-1], f'the shell must raise NotImplementedError("planned: {tag}") right after its '
                                        f'planned(…) call{"" if said is None else f", not {said!r}"}')
        return {**piece, "change": "added", "signature": self.signature(shell)}

    def shell_around(self, call: ast.Call):
        """The function whose whole body is this call then a ``raise``, a docstring allowed above them."""
        function = next((n for n in ast.walk(self.module.tree) if isinstance(n, FUNCTIONS)
                         and any(isinstance(s, ast.Expr) and s.value is call for s in n.body)), None)
        if function is None:
            return None
        body = function.body[1:] if ast.get_docstring(function, clean=False) is not None else function.body
        opens_with_the_call = len(body) == 2 and isinstance(body[0], ast.Expr) and body[0].value is call
        return function if opens_with_the_call and isinstance(body[1], ast.Raise) else None

    def signature(self, function) -> str:
        """A function's declaration up to its body, on one line."""
        first = function.body[0]
        header = self.lines[function.lineno - 1:first.lineno]
        header[-1] = header[-1][:first.col_offset]
        header[0] = header[0][function.col_offset:]
        return re.sub(r"\s+", " ", "\n".join(header)).strip()

    # ── Narratives ──────────────────────────────────────────────────────────────────────────────────

    def narrative_decorator(self, decorator) -> bool:
        """``@narrative(…)`` or ``@narrative.mechanism(…)``, the name being the one ``declare.py`` gives."""
        callee = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(callee, ast.Attribute) and callee.attr == "mechanism":
            callee = callee.value
        return self.imported_as(callee, self.declare) == "narrative"

    def narrative(self, cls: ast.ClassDef, decorator) -> dict:
        arguments = decorator.args if isinstance(decorator, ast.Call) and not decorator.keywords else []
        if len(arguments) != 1 or not isinstance(arguments[0], ast.Constant) or not isinstance(arguments[0].value, str):
            self.refuse(decorator, "a narrative is declared under one literal title: @narrative(\"…\")")
        if not self.is_test or len(self.scopes) > 1:
            self.refuse(decorator, "a narrative is declared on a class at the top of a test file")
        first = next((declared_title(node, self.file)[0] for node in cls.body if is_test_function(node)), None)
        paragraph = (ast.get_docstring(cls) or "").split("\n\n")[0]
        return {"file": self.file, "title": arguments[0].value, "line": decorator.lineno,
                "summary": re.sub(r"\s+", " ", paragraph).strip(), "firstTest": first}


def python_files(root: Path, folder: str) -> list[str]:
    """The Python files under a folder, as paths from the root."""
    found = []
    for directory, folders, files in os.walk(root / folder):
        folders[:] = sorted(f for f in folders if not f.startswith(".") and f not in SKIPPED_FOLDERS)
        found.extend((Path(directory) / f).relative_to(root).as_posix() for f in sorted(files) if f.endswith(".py"))
    return found


def build(root: Path, settings: dict, declare: str = DECLARE_MODULE) -> dict:
    try:
        source_folders, test_roots = settings["source"]["app"], settings["tests"]["roots"]
        test_pattern = re.compile(settings["tests"]["files"])
        calls = settings["stack"]["calls"]
    except (KeyError, TypeError) as error:
        raise Refusal(f'{CONFIG_FILE} — "source.app", "tests.roots", "tests.files" and "stack.calls" are read '
                      f'from it, and {error} is missing') from None
    source_files = sorted({file for folder in source_folders for file in python_files(root, folder)})
    # A test file can only declare a narrative or hold a site if it names where they are imported from.
    words = {calls.split(".")[-1], declare.split(".")[-1]}
    test_files = sorted({file for folder in test_roots for file in python_files(root, folder)
                         if test_pattern.search(file) and file not in source_files
                         and any(word in (root / file).read_text() for word in words)})
    modules = {file: Module(file, (root / file).read_text()) for file in [*source_files, *test_files]}
    source = Source(modules)
    narratives, files = [], {}
    for file, module in modules.items():
        index = FileIndex(module, source, calls, declare, is_test=file in test_files)
        if file in source_files or index.narratives or index.sites:
            narratives.extend(index.narratives)
            files[file] = index.tables()
    return {"narratives": narratives, "files": files}


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the source index of the Python stack as JSON.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2], help="the repository root")
    parser.add_argument("--config", type=Path, help=f"the configuration, {CONFIG_FILE} of the root by default")
    parser.add_argument("--declare", default=DECLARE_MODULE, help="the module narrative is imported from")
    asked = parser.parse_args()
    try:
        config = asked.config or asked.root / CONFIG_FILE
        try:
            settings = json.loads(config.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise Refusal(f"{config} is not a configuration that can be read — {error}") from None
        document = build(asked.root.resolve(), settings, asked.declare)
    except Refusal as refusal:
        print(f"comprehension-source: {refusal}", file=sys.stderr)
        return 1
    json.dump(document, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
