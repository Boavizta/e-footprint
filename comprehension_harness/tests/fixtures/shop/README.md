# shop: a source index written by hand

A project of three Python files and the index a Python stack would print for it
(`source-index.json`, the shape of `SourceIndexDocument` in `../../../stack.ts`). It is the
example a stack's own index is written to conform to, and what `../../json-source.test.ts`
reads: its first case checks every line and column of the index against the files here.

What the example shows a parser with names and no identities can and cannot say:

- `with_tax` in `shop/checkout.py` is followed through the file's import to `shop/pricing.py`.
- `basket.total()` in `pay` is a call on a value of unknown type: no `uses` entry, so the map lists
  no caller for `Basket.total`.
- `refund` is a shell: its body is the `planned` call and a raise of `planned: <tag>`.
