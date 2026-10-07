#!/usr/bin/env python3
"""Make local file links in an HTML plan open in VS Code for review."""

import argparse
from html import escape, unescape
from pathlib import Path
import os
import re
from urllib.parse import quote, unquote, urlsplit


ANCHOR = re.compile(r"<a\b[^>]*>", re.IGNORECASE | re.DOTALL)
HREF = re.compile(r'\bhref="([^"]*)"', re.IGNORECASE)
SOURCE = re.compile(r'\sdata-review-source-href="([^"]*)"', re.IGNORECASE)
LOCATION = re.compile(r":\d+(?::\d+)?$")
LINE_FRAGMENT = re.compile(r"L(\d+)(?::(\d+))?")


def original_from_vscode(href: str, plan_dir: Path) -> str:
    url = urlsplit(href)
    if url.netloc != "file" or not url.path.startswith("//"):
        raise ValueError(f"Unrecognized VS Code file URL: {href}")
    location = LOCATION.search(url.path)
    path = Path(unquote(LOCATION.sub("", url.path[1:])))
    relative = os.path.relpath(path, plan_dir)
    if location is not None:
        return relative + "#L" + location.group(0)[1:]
    return relative


def rewrite(source: str, plan_dir: Path, restore: bool) -> tuple[str, int, list[str]]:
    count = 0
    missing = []

    def convert(match: re.Match[str]) -> str:
        nonlocal count
        tag = match.group(0)
        href_match = HREF.search(tag)
        if href_match is None:
            return tag
        href = unescape(href_match.group(1))
        source_match = SOURCE.search(tag)

        if restore:
            if source_match is None:
                return tag
            original = unescape(source_match.group(1))
            tag = SOURCE.sub("", tag, count=1)
            count += 1
            return HREF.sub(f'href="{escape(original, quote=True)}"', tag, count=1)

        if source_match is not None:
            return tag
        if href.startswith("vscode://"):
            original = original_from_vscode(href, plan_dir)
            vscode_href = href
        else:
            url = urlsplit(href)
            if url.scheme or href.startswith("#") or url.query:
                return tag
            location = LINE_FRAGMENT.fullmatch(url.fragment) if url.fragment else None
            if url.fragment and location is None:
                return tag
            path = (plan_dir / unquote(url.path)).resolve()
            if not path.is_file():
                missing.append(href)
                return tag
            original = href
            vscode_href = "vscode://file/" + quote(str(path), safe="/")
            if location is not None:
                vscode_href += f":{location.group(1)}:{location.group(2) or '1'}"

        tag = HREF.sub(f'href="{escape(vscode_href, quote=True)}"', tag, count=1)
        tag = tag[:-1] + f' data-review-source-href="{escape(original, quote=True)}">'
        count += 1
        return tag

    return ANCHOR.sub(convert, source), count, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Source HTML plan")
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--in-place", action="store_true", help="Edit the source plan")
    destination.add_argument("--output", type=Path, help="Write a separate local review copy")
    parser.add_argument("--restore", action="store_true", help="Restore original relative links")
    args = parser.parse_args()

    plan = args.plan.resolve()
    output = plan if args.in_place else args.output.resolve()
    if not args.in_place and output == plan:
        parser.error("Use --in-place to edit the source plan")
    converted, count, missing = rewrite(plan.read_text(), plan.parent, args.restore)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(converted)
    print(f"{'Restored' if args.restore else 'Converted'} {count} file links in {output}")
    if missing:
        print("Skipped links without an existing file: " + ", ".join(sorted(set(missing))))


if __name__ == "__main__":
    main()
