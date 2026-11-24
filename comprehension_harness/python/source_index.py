"""The source index of the Python stack (``comprehension_harness/stack.md`` § 2), built on ``ast``.

    python3 -m comprehension_harness.python.source_index

Prints the index as one JSON document (``SourceIndexDocument`` of ``comprehension_harness/stack.ts``): every
Python file of the source folders (``source.app`` of ``comprehension.config.json``) and every test file that
declares a narrative or holds a site, each with its sites, functions, declarations, imports, locals and uses.

What this stack knows and the tools do not:

- the calls (``narrate``, ``event``, ``planned``, ``built``) are those of the project's own copy of
  ``narrate.py``, the module ``stack.calls`` of the configuration names, imported by name; a function of the
  same name from anywhere else is no site;
- a narrative is a test class under ``@narrative("…")`` of ``declare.py``; its summary is the first
  paragraph of the class docstring, its first test the first ``test_…`` method;
- a function is named by its ``__qualname__``, which is what a frame of a story prints;
- a declared name is in PascalCase, snake_case or CONSTANT_CASE (``looksDeclared`` of the document).

A parser gives names, not identities. A reference is placed at its declaration when Python's own scoping says
where the name is bound: a top-level declaration of the file, an import followed to the file it names (through
a package's re-exports), ``module.name`` on an imported module, ``self.name`` and ``cls.name`` on the class
around them, a function or class of an enclosing function. A call on a value of unknown type is left out.

Refused, with the file and the line: a file the parser refuses, a call imported from the reference and not
from the project's copy, two calls on one line, a tag or a sentence
that is no literal string, a watch that is no lambda, an ``expect`` that is neither a literal dict nor a
lambda, a ``distinct`` that is no literal string or tuple of them, a tag that is not ``<feature>#<slug>`` or
``<feature>#<slug>:<place>``, a place named on a removing or an evidence call, a ``built`` call that is not one
literal naming its place, a shell that raises anything but ``planned: <feature>#<slug>``, a narrative that is not
declared on a class under one literal title.

``planned("<feature>#<slug>:<place>", …)`` names the place of its piece the site is, which the site says as
``place``. ``built("<feature>#<slug>:<place>")`` stands where such a call stood once the place is code: a planned
site whose change is ``built``, with its place and an empty sentence.

The literal and the lambda are what keeps the calls inert in production: Python computes a call's arguments
before the call, and a call does nothing there. A literal and a lambda cost nothing to compute.

``planned.evidence(…)`` is a planned site whose change is ``evidence``: a place a bug shows, which goes with the
fix. ``expect=`` on it, or on a ``planned`` call, is what the place should see, a key of the watch each: a
literal dict, or a lambda where the right value depends on the crossing. The site says it as ``expect``, the
expression as written; its value at each crossing is the story's. ``distinct=`` names the keys of the watch each
crossing should see a value of its own for, where the bug is a value two crossings share: the site lists them
as ``distinct``, and no run reads them.

A template makes the calls as tags, and no ``ast`` reads it: an ``.html`` file of the source folders is read for
``{% narrate "…" %}``, ``{% event "…" %}``, ``{% planned "<feature>#<slug>:<place>" "…" %}``, ``{% evidence
"<feature>#<slug>" "…" %}`` and ``{% built "<feature>#<slug>:<place>" %}``, one a line, each a site of the file in
no function. After the sentence a tag gives
its watch as ``key=value`` pairs, and after the word ``expect`` the values the place should see, as pairs too:
``{% evidence "a#b" "…" drawn_as="row" expect drawn_as=row.kind %}``. The template resolves both when a run
collects. After the word ``distinct`` it names keys of its watch: ``{% planned "a#b" "…" id=row.id distinct id %}``.

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
# A `built` call is a site of the plan too: the place it stands for is code.
KINDS = {"narrate": "step", "event": "event", "planned": "planned", "built": "planned"}
# The shape of a name Python declares: a class in PascalCase, a function or a variable in snake_case, with the
# underscores a private name opens with, a constant in CONSTANT_CASE. A backticked token of that shape that the
# index cannot place fails `--check`. Written to be read the same by `re` and by JavaScript.
LOOKS_DECLARED = r"^(?:[A-Z][A-Za-z0-9]{2,}|_*[a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$"
# A tag names its piece, then the place of the piece the site is: `<feature>#<slug>:<place>`.
PLANNED_TAG = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)#([a-z0-9]+(?:-[a-z0-9]+)*)(?::([a-z0-9]+(?:-[a-z0-9]+)*))?$")
NOT_A_TAG = "is not <feature>#<slug> or <feature>#<slug>:<place>, kebab-case names"
BUILT_SHAPE = 'takes one literal, "<feature>#<slug>:<place>"'
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
# What has names of its own. A list, set or dict comprehension runs in its function's frame; a generator
# expression and a lambda in a frame with no name.
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
# The forms of `planned` that are written `planned.<form>(…)`, and the change each says.
PLANNED_FORMS = {"remove": "removed", "evidence": "evidence"}
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

    def call_kind(self, node: ast.Call) -> tuple[str, str] | None:
        """The kind of site a call is and the change it says: that of its form for a call written
        ``planned.<form>``, ``built`` for a ``built`` call, ``changed`` for any other; None for a call that is no
        site."""
        callee = node.func
        if isinstance(callee, ast.Attribute):
            if self.imported_as(callee.value, self.calls) == "planned" and callee.attr in PLANNED_FORMS:
                return "planned", PLANNED_FORMS[callee.attr]
            if callee.attr in KINDS and self.dotted_of(callee.value) == self.calls:
                self.refuse(node, f"the calls are imported by name: from {self.calls} import {callee.attr}")
            return None
        name = self.imported_as(callee, self.calls) or ""
        kind = KINDS.get(name)
        if kind is None and self.calls != REFERENCE_CALLS and self.imported_as(callee, REFERENCE_CALLS) in KINDS:
            self.refuse(node, f"the calls are imported from this project's copy, {self.calls}, not from the reference")
        return (kind, "built" if name == "built" else "changed") if kind else None

    def visit_Call(self, node) -> None:
        found = self.call_kind(node)
        if found is None:
            self.generic_visit(node)
            return
        # A site, and nothing inside it is read as a use: a watch is documentation.
        kind, change = found
        if node.lineno in self.site_lines:
            self.refuse(node, f"one narrate, event, planned or built call a line: a site is a file and a line, and "
                              f"this line already holds a {self.site_lines[node.lineno]}")
        self.site_lines[node.lineno] = kind
        if change == "built":
            tag = literal_argument(node, 0)
            if tag is None or len(node.args) != 1 or node.keywords:
                self.refuse(node, f"built(…) {BUILT_SHAPE}")
            self.sites.append({"kind": kind, "line": node.lineno, "column": node.col_offset + 1,
                               "fn": self.frame_name(), "sentence": "", "planned": self.planned(node, tag, "", change)})
            return
        literals = 2 if kind == "planned" else 1
        site = {"kind": kind, "line": node.lineno, "column": node.col_offset + 1, "fn": self.frame_name(),
                "sentence": literal_argument(node, literals - 1)}
        expected = [keyword for keyword in node.keywords if keyword.arg == "expect"]
        distinct = [keyword for keyword in node.keywords if keyword.arg == "distinct"]
        if kind == "planned":
            site["planned"] = self.planned(node, literal_argument(node, 0), site["sentence"], change)
            if expected and change != "removed":
                site["planned"]["expect"] = self.expect(expected[0].value)
            if distinct and change != "removed":
                site["planned"]["distinct"] = self.distinct(distinct[0].value)
        elif site["sentence"] is None:
            self.refuse(node, "the sentence of a narrate or event call is a literal string: anything else is "
                              "computed in production, where the call does nothing")
        said = [*expected, *distinct] if kind == "planned" else []
        watches = [keyword.value for keyword in node.keywords if keyword not in said]
        for argument in [*node.args[literals:], *watches]:
            if not isinstance(argument, ast.Lambda):
                self.refuse(argument, "the watch is a lambda (lambda: {…}): anything else is computed in production, "
                                      "where nobody reads it")
        self.sites.append(site)

    def expect(self, node) -> str:
        """What ``expect=`` says, as written: a literal dict, or the body of a lambda, which costs production
        nothing to compute."""
        if isinstance(node, ast.Lambda):
            return ast.unparse(node.body)
        try:
            said = ast.literal_eval(node)
        except (ValueError, SyntaxError):
            said = None
        if not isinstance(said, dict) or not said or not all(isinstance(key, str) for key in said):
            self.refuse(node, 'expect is a literal dict, a key of the watch each (expect={"status": 200}), or a '
                              'lambda (expect=lambda: {…}): anything else is computed in production, where nobody '
                              'reads it')
        return ast.unparse(node)

    def distinct(self, node) -> list[str]:
        """The keys ``distinct=`` names: a literal string, or a literal tuple or list of them."""
        try:
            said = ast.literal_eval(node)
        except (ValueError, SyntaxError):
            said = None
        keys = [said] if isinstance(said, str) else list(said) if isinstance(said, (tuple, list)) else []
        if not keys or not all(isinstance(key, str) and key.isidentifier() for key in keys):
            self.refuse(node, 'distinct names keys of the watch, as a literal string or a literal tuple of them '
                              '(distinct="id"): anything else is computed in production, where nobody reads it')
        return keys

    def planned(self, node: ast.Call, tag: str | None, sentence: str | None, change: str) -> dict:
        if tag is None or sentence is None:
            self.refuse(node, 'planned(…) needs a literal "<feature>#<slug>:<place>" and a literal sentence')
        piece = planned_piece(tag, change, lambda what: self.refuse(node, what))
        if change != "changed":
            return {**piece, "change": change, "signature": None}
        shell = self.shell_around(node)
        if shell is None:
            return {**piece, "change": "changed", "signature": None}
        raised = shell.body[-1].exc
        said = literal_argument(raised, 0) if isinstance(raised, ast.Call) else None
        # A shell raises its piece: the place is the call's to name.
        named = f'{piece["feature"]}#{piece["slug"]}'
        if said not in (f"planned: {named}", f"planned: {tag}"):
            self.refuse(shell.body[-1], f'the shell must raise NotImplementedError("planned: {named}") right after '
                                        f'its planned(…) call{"" if said is None else f", not {said!r}"}')
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


def planned_piece(tag: str, change: str, refuse) -> dict:
    """What a tag names: its feature and its piece, and the place of the piece where it names one. A place is
    the id of a site that becomes code: a ``built`` call names one, a removing or an evidence call none, since
    neither keeps a call once its piece is built."""
    parsed = PLANNED_TAG.match(tag)
    if parsed is None:
        refuse(f'"{tag}" {NOT_A_TAG}')
    feature, slug, place = parsed.groups()
    if change == "built" and place is None:
        refuse(f"a built call {BUILT_SHAPE}, and \"{tag}\" names no place")
    if change in PLANNED_FORMS.values() and place is not None:
        refuse(f'"{tag}" names a place, and only a place that becomes code has one: a function that goes and a '
               f'place a bug shows are tagged "{feature}#{slug}"')
    return {"feature": feature, "slug": slug, **({} if place is None else {"place": place})}


def files_under(root: Path, folder: str, suffix: str) -> list[str]:
    """The files of one kind under a folder, as paths from the root."""
    found = []
    for directory, folders, files in os.walk(root / folder):
        folders[:] = sorted(f for f in folders if not f.startswith(".") and f not in SKIPPED_FOLDERS)
        found.extend((Path(directory) / f).relative_to(root).as_posix() for f in sorted(files) if f.endswith(suffix))
    return found


def python_files(root: Path, folder: str) -> list[str]:
    return files_under(root, folder, ".py")


# A call a template makes: a tag named after it. What a function is to a Python site, a template has none of.
TEMPLATE_TAG = re.compile(r"\{%-?\s*(narrate|event|planned|evidence|built)\s+(.*?)\s*-?%\}")
TEMPLATE_WORD = re.compile(r'''"(?:[^"\\]|\\.)*"|[^\s"]+(?:"(?:[^"\\]|\\.)*")?''')
TEMPLATE_FN = "(template)"
# The words of a tag that open what the place should see: values, then the keys that should differ at each crossing.
TEMPLATE_PARTS = ("expect", "distinct")


def template_sites(file: str, text: str) -> list[dict]:
    """The sites of a template: its ``narrate``, ``event``, ``planned``, ``evidence`` and ``built`` tags, one a
    line."""
    sites = []
    for number, line in enumerate(text.split("\n"), start=1):
        found = list(TEMPLATE_TAG.finditer(line))
        if not found:
            continue
        where = f"{file}:{number}"
        if len(found) > 1:
            raise Refusal(f"{where} — one narrate, event, planned, evidence or built tag a line: a site is a file "
                          f"and a line")
        call, words = found[0].group(1), TEMPLATE_WORD.findall(found[0].group(2))

        def refuse(what: str):
            raise Refusal(f"{where} — {what}")

        if call == "built":
            if len(words) != 1 or not (words[0].startswith('"') and words[0].endswith('"') and len(words[0]) > 1):
                refuse(f"{{% built %}} {BUILT_SHAPE}, in double quotes")
            sites.append({"kind": "planned", "line": number, "column": found[0].start() + 1, "fn": TEMPLATE_FN,
                          "sentence": "", "planned": {**planned_piece(words[0][1:-1], "built", refuse),
                                                      "change": "built", "signature": None}})
            continue
        literals = 2 if call in ("planned", "evidence") else 1
        said = [word[1:-1].replace('\\"', '"') for word in words[:literals] if word.startswith('"') and word.endswith('"')]
        if len(said) < literals:
            raise Refusal(f'{where} — {{% {call} %}} opens with {"its tag and its sentence" if literals == 2 else "its sentence"}'
                          f', in double quotes: anything else is computed in production, where the tag does nothing')
        rest = words[literals:]
        # The watch, then what follows each of the two words, in either order.
        parts = {"watch": [], "expect": [], "distinct": []}
        part = "watch"
        for word in rest:
            if word in TEMPLATE_PARTS:
                part = word
            else:
                parts[part].append(word)
        watched, expected, distinct = parts.values()
        pairs = [word.partition("=") for word in [*watched, *expected]]
        if any(not key.isidentifier() or not separator or not value for key, separator, value in pairs) or (
                "expect" in rest and not expected):
            raise Refusal(f"{where} — after the sentence a tag gives key=value pairs, the watch, then after the word "
                          f"expect the values the place should see")
        if ("distinct" in rest and not distinct) or not set(distinct) <= {word.partition("=")[0] for word in watched}:
            raise Refusal(f"{where} — after the word distinct a tag names keys of its watch, those each crossing "
                          f"should see a value of its own for")
        site = {"kind": KINDS.get(call, "planned"), "line": number, "column": found[0].start() + 1,
                "fn": TEMPLATE_FN, "sentence": said[-1]}
        if literals == 2:
            change = "evidence" if call == "evidence" else "changed"
            site["planned"] = {**planned_piece(said[0], change, refuse), "change": change, "signature": None}
            if expected:
                site["planned"]["expect"] = " ".join(expected)
            if distinct:
                site["planned"]["distinct"] = distinct
        elif expected or distinct:
            raise Refusal(f"{where} — expect and distinct are said of a planned or an evidence tag: a step expects "
                          f"nothing")
        sites.append(site)
    return sites


def build(root: Path, settings: dict, declare: str = DECLARE_MODULE) -> dict:
    try:
        source_folders, test_roots = settings["source"]["app"], settings["tests"]["roots"]
        test_pattern = re.compile(settings["tests"]["files"])
        calls = settings["stack"]["calls"]
    except (KeyError, TypeError) as error:
        raise Refusal(f'{CONFIG_FILE} — "source.app", "tests.roots", "tests.files" and "stack.calls" are read '
                      f'from it, and {error} is missing') from None
    source_files = sorted({file for folder in source_folders for file in python_files(root, folder)})
    templates = sorted({file for folder in source_folders for file in files_under(root, folder, ".html")})
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
    # A template is listed when it holds a site: it has no function, no declaration and no reference to index.
    for file in templates:
        text = (root / file).read_text()
        sites = template_sites(file, text) if "{%" in text else []
        if sites:
            files[file] = {"sites": sites, "functions": [], "declarations": [], "imports": [], "locals": [], "uses": []}
    return {"looksDeclared": LOOKS_DECLARED, "narratives": narratives, "files": files}


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
