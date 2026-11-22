"""The tools' tests are vitest's. A project whose pytest run collects from its root must not take the Python files
of their fixtures for tests of its own."""
collect_ignore = ["fixtures"]
