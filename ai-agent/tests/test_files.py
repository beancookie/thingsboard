import pytest

from app.agent.files import FileStore
from app.common.errors import AgentError


def test_file_store_owner_and_size() -> None:
    store = FileStore(ttl_seconds=60, max_bytes=10)
    file = store.create(b"hello", "a.txt", "text/plain", "user-1")

    assert store.get(file.id, "user-1") is not None
    assert store.get(file.id, "user-2") is None

    with pytest.raises(AgentError) as error:
        store.create(b"12345678901", "big.txt", "text/plain", "user-1")
    assert error.value.code == "FILE_TOO_LARGE"
