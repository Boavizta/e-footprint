"""The strip of the Python stack (``comprehension_harness/stack.md`` § "The strip of an archive"), on ``ast``.

    python3 -m comprehension_harness.python.strip < file.json

Reads ``{file, text, feature}`` on its input and prints ``{text, taken}``: the file's text with what the archive
of the feature takes off it, and what went, each as ``{line, kind, was}``. The tools choose the files, hold the
strip to the archive gate and write the result (``render.ts --strip``).

Three things go from a Python file, each by its node and never by a pattern over the text:

- each ``built("<feature>#<slug>:<place>")`` statement of the feature, with the lines it stands on; the
  ``built`` name goes from its import with the last use of it in the file;
- the tag and the ``[rule]`` of each test titled ``<feature>#<slug>: <title> [<rule>]`` under ``@titled``,
  ``@reproduces`` or ``@planned_test`` (``declare.py``), which leaves ``<title>``, written as it was;
- the ``planned={…}`` of each ``screen(…)`` of a journey that names the feature (``journey.py``).

From a template, each ``{% built "<feature>#<slug>:<place>" %}`` tag goes, with its line when it has it to
itself, and ``narrate`` goes from the template's ``{% load … %}`` with its last tag.

Another feature's marks stay, and so does a tag written in a comment or in a string that is no title. A file
that is neither Python nor a template comes back as it is.

Refused, with the file and the line: a ``built`` call that cannot go without changing the code around it (one
that is no statement, on a line it shares, or whose block would be left empty), and a Python file the parser
refuses.

Standard library only.
"""
import ast
import io
import json
import re
import sys
import tokenize

from .source_index import TEMPLATE_TAG, TEMPLATE_WORD
from .titles import TITLE_DECORATORS, Refusal, decorator_name, parse

KEBAB = r"[a-z0-9]+(?:-[a-z0-9]+)*"
STRING_OPENING = re.compile(r"""^[A-Za-z]*('''|\"\"\"|'|\")""")
TEMPLATE_LOAD = re.compile(r"\{%-?\s*load\s+(.*?)\s*-?%\}")
BY_HAND = "Take it off by hand"


class Text:
    """A file's text, and where a node of its tree stands in it: ``ast`` counts a column in UTF-8 bytes."""

    def __init__(self, text: str):
        self.text = text
        self.lines = text.split("\n")
        self.starts = [0]
        for line in self.lines[:-1]:
            self.starts.append(self.starts[-1] + len(line) + 1)

    def at(self, line: int, column: int) -> int:
        return self.starts[line - 1] + len(self.lines[line - 1].encode()[:column].decode())

    def span(self, node) -> tuple[int, int]:
        return self.at(node.lineno, node.col_offset), self.at(node.end_lineno, node.end_col_offset)

    def whole_lines(self, start: int, end: int) -> tuple[int, int] | None:
        """The whole lines a stretch stands on, when nothing else is on them: from the start of its first line
        to the start of the line after its last. None when other text shares a line with it."""
        opens = self.text.rfind("\n", 0, start) + 1
        closes = self.text.find("\n", end)
        closes = len(self.text) if closes == -1 else closes
        if self.text[opens:start].strip() or self.text[end:closes].strip():
            return None
        return opens, min(closes + 1, len(self.text))

    def with_its_blank(self, lines: tuple[int, int]) -> tuple[int, int]:
        """A stretch of whole lines, and the blank line under it when one stands over it too: taking the lines
        off leaves one blank line where there were two around them, and none at the head of the file."""
        start, end = lines
        if start == 0:
            return start, end + re.match(r"(?:[ \t]*\n)*", self.text[end:]).end()
        blank_above = re.search(r"\n[ \t]*\n$", self.text[:start]) is not None
        under = re.match(r"[ \t]*\n", self.text[end:])
        return (start, end + under.end()) if blank_above and under else lines

    def list_element(self, elements: list, element) -> tuple[int, int]:
        """One element of a list written between commas (an import's names, a call's arguments): its lines when
        it has them to itself, else the element with the comma that parts it from its neighbour."""
        start, end = self.span(element)
        comma = re.match(r"[ \t]*,", self.text[end:])
        if comma:
            end += comma.end()
        lines = self.whole_lines(start, end)
        if lines:
            return lines
        at = elements.index(element)
        if at + 1 < len(elements):
            return start, self.span(elements[at + 1])[0]
        return (self.span(elements[at - 1])[1], self.span(element)[1]) if at > 0 else (start, end)


def blocks_of(tree: ast.Module) -> dict[int, list]:
    """The block each statement of a file stands in, by the statement's identity."""
    blocks = {}
    for node in ast.walk(tree):
        for _, value in ast.iter_fields(node):
            if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                blocks.update({id(statement): value for statement in value})
    return blocks


def strip_python(file: str, text: str, feature: str) -> dict:
    tree, at = parse(file, text), Text(text)
    built_tag = re.compile(rf"^{re.escape(feature)}#{KEBAB}:{KEBAB}$")
    title_tag = re.compile(rf"^{re.escape(feature)}#{KEBAB}:\s*")
    rule_suffix = re.compile(rf"\s*\[{KEBAB}\]$")
    constants = {node.targets[0].id: node.value.value for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}
    blocks = blocks_of(tree)
    statements = {id(node.value): node for node in ast.walk(tree) if isinstance(node, ast.Expr)}
    edits: list[tuple[int, int, str]] = []
    taken: list[dict] = []
    gone: set[int] = set()
    # How many statements of a block go, by the block's identity: Python has no empty block.
    leaving: dict[int, int] = {}

    def literal(node) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    def take_built(call: ast.Call, tag: str) -> None:
        """A built place of the feature: the statement goes, with its lines."""
        where, said = f"{file}:{call.lineno}", f'built("{tag}")'
        statement = statements.get(id(call))
        if statement is None or id(statement) not in blocks:
            raise Refusal(f"{where} — {said} is no statement of a block: taking it off would change the code "
                          f"around it. {BY_HAND}")
        block = blocks[id(statement)]
        leaving[id(block)] = leaving.get(id(block), 0) + 1
        if leaving[id(block)] == len(block):
            raise Refusal(f"{where} — {said} is all its block holds: taking it off would leave the block empty. "
                          f"{BY_HAND}")
        lines = at.whole_lines(*at.span(statement))
        if lines is None:
            raise Refusal(f"{where} — {said} shares its line with other code. {BY_HAND}")
        edits.append((*at.with_its_blank(lines), ""))
        taken.append({"line": call.lineno, "kind": "built", "was": said})
        gone.add(id(call.func))

    def take_title(decorator: ast.Call, title: str) -> None:
        """A test of the feature: its title loses the tag and the rule, and keeps the rest as it is written."""
        start, end = at.span(decorator.args[0])
        # A title may be written as several literals side by side: the tag opens the first, the rule ends the last.
        written = f"({text[start:end]})"
        parts = [token for token in tokenize.generate_tokens(io.StringIO(written).readline)
                 if token.type == tokenize.STRING]
        rows = Text(written)

        def body(token) -> tuple[int, int]:
            quote = len(STRING_OPENING.match(token.string).group(1))
            opens = STRING_OPENING.match(token.string).end()
            return (start - 1 + rows.starts[token.start[0] - 1] + token.start[1] + opens,
                    start - 1 + rows.starts[token.end[0] - 1] + token.end[1] - quote)

        first, last = body(parts[0]), body(parts[-1])
        tag = title_tag.match(text[first[0]:first[1]])
        if tag is None:
            raise Refusal(f"{file}:{decorator.lineno} — the tag of \"{title}\" is not written in one literal. "
                          f"{BY_HAND}")
        rule = rule_suffix.search(text[last[0]:last[1]])
        if first == last:
            edits.append((first[0], first[1], rule_suffix.sub("", text[first[0] + tag.end():first[1]])))
        else:
            edits.append((first[0], first[0] + tag.end(), ""))
            if rule:
                edits.append((last[0] + rule.start(), last[1], ""))
        taken.append({"line": decorator.lineno, "kind": "title", "was": title})

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        first = literal(node.args[0]) if node.args else None
        if isinstance(node.func, ast.Name) and node.func.id == "built" and first and built_tag.match(first):
            take_built(node, first)
        if decorator_name(node) in TITLE_DECORATORS and first and title_tag.match(first) and not node.keywords \
                and len(node.args) == 1:
            take_title(node, first)
        # A planned screen of the feature: the argument goes from the call it stands in.
        if decorator_name(node) == "screen":
            for keyword in node.keywords:
                if keyword.arg != "planned" or not isinstance(keyword.value, ast.Dict):
                    continue
                named = next((value for key, value in zip(keyword.value.keys, keyword.value.values)
                              if key is not None and literal(key) == "feature"), None)
                of = constants.get(named.id) if isinstance(named, ast.Name) else literal(named) if named else None
                if of == feature:
                    edits.append((*at.list_element([*node.args, *node.keywords], keyword), ""))
                    taken.append({"line": keyword.lineno, "kind": "screen",
                                  "was": f'planned={{"feature": "{feature}", …}}'})

    # Another use of `built` keeps its import: a call of another feature, the function handed on.
    elsewhere = any(isinstance(node, ast.Name) and node.id == "built" and id(node) not in gone
                    for node in ast.walk(tree))
    if gone and not elsewhere:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name != "built" or alias.asname is not None:
                    continue
                block = blocks[id(node)]
                alone = len(node.names) == 1 and leaving.get(id(block), 0) + 1 < len(block)
                whole = at.whole_lines(*at.span(node)) if alone else None
                if whole:
                    edits.append((*at.with_its_blank(whole), ""))
                elif len(node.names) > 1:
                    edits.append((*at.list_element(node.names, alias), ""))

    return {"text": applied(file, at, edits), "taken": sorted(taken, key=lambda one: one["line"])}


def applied(file: str, at: Text, edits: list[tuple[int, int, str]]) -> str:
    out, floor = at.text, None
    for start, end, put in sorted(edits, reverse=True):
        if floor is not None and end > floor:
            line = at.text.count("\n", 0, start) + 1
            raise Refusal(f"{file}:{line} — two of the stretches to take off overlap. {BY_HAND}")
        out, floor = out[:start] + put + out[end:], start
    return out


def strip_template(file: str, text: str, feature: str) -> dict:
    """A template's ``built`` tags of the feature go: a tag renders nothing, so one that shares its line goes
    alone and leaves the line."""
    at = Text(text)
    built_tag = re.compile(rf'^"{re.escape(feature)}#{KEBAB}:{KEBAB}"$')
    edits, taken, kept = [], [], 0
    for found in TEMPLATE_TAG.finditer(text):
        words = TEMPLATE_WORD.findall(found.group(2))
        if found.group(1) != "built" or len(words) != 1 or not built_tag.match(words[0]):
            kept += 1
            continue
        lines = at.whole_lines(found.start(), found.end())
        edits.append((*(lines or (found.start(), found.end())), ""))
        taken.append({"line": text.count("\n", 0, found.start()) + 1, "kind": "built", "was": f"{{% built {words[0]} %}}"})
    # The tag library goes with the template's last tag, as an import goes with its last call.
    if taken and kept == 0:
        for load in TEMPLATE_LOAD.finditer(text):
            libraries = load.group(1).split()
            if "narrate" not in libraries or "from" in libraries:
                continue
            if libraries == ["narrate"]:
                edits.append((*(at.whole_lines(load.start(), load.end()) or (load.start(), load.end())), ""))
            else:
                word = re.search(r"\s+narrate(?=\s|-?%\})", load.group(0))
                edits.append((load.start() + word.start(), load.start() + word.end(), ""))
    return {"text": applied(file, at, edits), "taken": taken}


def strip(file: str, text: str, feature: str) -> dict:
    """One file's text with what the archive of ``feature`` takes off it, and what went."""
    if feature not in text:
        return {"text": text, "taken": []}
    if file.endswith(".py"):
        return strip_python(file, text, feature)
    if file.endswith(".html"):
        return strip_template(file, text, feature)
    return {"text": text, "taken": []}


def main() -> int:
    try:
        asked = json.load(sys.stdin)
        if not isinstance(asked, dict) or not all(isinstance(asked.get(key), str) for key in ("file", "text", "feature")):
            raise Refusal("the input is not {file, text, feature}, a file's path, its text and a feature's name")
        answer = strip(asked["file"], asked["text"], asked["feature"])
    except json.JSONDecodeError as error:
        print(f"comprehension-strip: the input is not JSON — {error}", file=sys.stderr)
        return 1
    except Refusal as refusal:
        print(f"comprehension-strip: {refusal}", file=sys.stderr)
        return 1
    json.dump(answer, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
