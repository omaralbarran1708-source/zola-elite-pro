import pytest

from zola.store import Store, set_store


@pytest.fixture(autouse=True)
def tmp_store(tmp_path):
    s = Store(path=str(tmp_path / "test.db"))
    set_store(s)
    yield s
