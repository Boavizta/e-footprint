"""Skip markers for tests that exercise an optional dependency group, so the suite also runs on a bare core install."""
from importlib.util import find_spec
from unittest import skipUnless

needs_viz = skipUnless(
    all(find_spec(package) for package in ("matplotlib", "plotly", "pyvis")), "needs efootprint[viz]")
needs_boaviztapi = skipUnless(find_spec("boaviztapi"), "needs efootprint[boaviztapi]")
