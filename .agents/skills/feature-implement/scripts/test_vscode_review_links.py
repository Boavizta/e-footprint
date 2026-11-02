"""Regression checks for browser documentation links versus editor source links."""
import tempfile
import unittest
from pathlib import Path

from vscode_review_links import rewrite


class ReviewLinksTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.plan_dir = self.root / 'specs/features/example'
        self.plan_dir.mkdir(parents=True)

    def file(self, relative):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<h2 id="section">Documentation</h2>')
        return path

    def test_documentation_links_preserve_sections_and_are_idempotent(self):
        for directory in ('specs', 'docs', 'docs_sources'):
            with self.subTest(directory=directory):
                self.file(f'{directory}/architecture/page.html')
                source = f'<a href="../../../{directory}/architecture/page.html#section" target="_self" rel="noreferrer">Docs</a>'
                result, _, missing = rewrite(source, self.plan_dir, False)
                self.assertIn('#section"', result)
                self.assertIn('target="_blank"', result)
                self.assertIn('rel="noreferrer noopener"', result)
                self.assertNotIn('_self', result)
                self.assertNotIn('vscode:', result)
                self.assertNotIn('data-review-source-href', result)
                self.assertEqual([], missing)
                self.assertEqual(result, rewrite(result, self.plan_dir, False)[0])

    def test_legacy_documentation_links_are_repaired_with_or_without_marker(self):
        path = self.file('specs/architecture/page.html')
        for marker in ('', ' data-review-source-href="../../architecture/page.html#L12"'):
            with self.subTest(marker=marker):
                source = f'<a href="vscode://file/{path}:12:1"{marker}>Docs</a>'
                result, _, _ = rewrite(source, self.plan_dir, False)
                self.assertEqual('<a href="../../architecture/page.html" target="_blank" rel="noopener">Docs</a>', result)

    def test_production_templates_and_python_remain_source_links(self):
        for relative in ('model_builder/templates/card.html', 'model_builder/views.py'):
            with self.subTest(relative=relative):
                path = self.file(relative)
                original = f'../../../{relative}#L12:3'
                source = f'<a href="{original}">Source</a>'
                result, _, _ = rewrite(source, self.plan_dir, False)
                self.assertIn(f'href="vscode://file/{path}:12:3"', result)
                self.assertIn(f'data-review-source-href="{original}"', result)
                self.assertEqual(source, rewrite(result, self.plan_dir, True)[0])

    def test_external_and_plan_section_links_are_untouched(self):
        for href in ('https://example.org/docs/page.html', '#task-1'):
            source = f'<a href="{href}">Link</a>'
            self.assertEqual(source, rewrite(source, self.plan_dir, False)[0])


if __name__ == '__main__':
    unittest.main()
