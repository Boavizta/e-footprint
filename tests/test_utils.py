from unittest.mock import MagicMock


def mock_class(cls):
    class meta(type):
        def __getattribute__(self, name):
            try:
                return getattr(mock, name)
            except AttributeError:
                return getattr(cls, name)

    mock = MagicMock(spec_set=cls)

    return meta(cls.__name__, cls.__bases__, {})
