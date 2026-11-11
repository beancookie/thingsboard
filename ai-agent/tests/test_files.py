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


def test_file_store_preserves_chinese_filename() -> None:
    store = FileStore()

    file = store.create(b"{}", "温度传感器.json", "application/json", "user-1")

    assert file.name == "温度传感器.json"


def test_file_store_strips_path_from_chinese_filename() -> None:
    store = FileStore()

    unix_path = store.create(b"{}", "../../温度传感器.json", "application/json", "user-1")
    windows_path = store.create(b"{}", r"..\..\湿度传感器.json", "application/json", "user-1")

    assert unix_path.name == "温度传感器.json"
    assert windows_path.name == "湿度传感器.json"


def test_file_store_replaces_unsafe_filename_characters() -> None:
    store = FileStore()

    file = store.create(b"{}", '温度<1>:"测试".json', "application/json", "user-1")

    assert file.name == "温度_1_测试_.json"


def test_file_store_removes_control_characters() -> None:
    store = FileStore()

    file = store.create(b"{}", "温度\x00\n\t传感器.json", "application/json", "user-1")

    assert file.name == "温度传感器.json"


def test_file_store_falls_back_for_blank_filename() -> None:
    store = FileStore()

    assert store.create(b"{}", "   ", "application/json", "user-1").name == "upload.bin"
    assert store.create(b"{}", "..", "application/json", "user-1").name == "upload.bin"


def test_file_store_truncates_long_filename_and_keeps_extension() -> None:
    store = FileStore()

    file = store.create(b"{}", "温" * 300 + ".json", "application/json", "user-1")

    assert len(file.name) == 255
    assert file.name.endswith(".json")
