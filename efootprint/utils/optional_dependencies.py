from contextlib import contextmanager


@contextmanager
def requires_extra(extra: str):
    """Wrap the imports of an optional dependency group so that a missing package names the group to install."""
    try:
        yield
    except ImportError as error:
        raise ImportError(
            f"{error}. This feature needs the optional '{extra}' dependencies of efootprint: "
            f"install them with `pip install \"efootprint[{extra}]\"`.") from error
