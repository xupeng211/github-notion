import pytest
from app.notion import NotionClient

def test_load_mapping():
    # ... 测试映射加载逻辑 ...
    # ... 测试映射加载逻辑 ...
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        yml = Path(d)/"mapping.yml"
        yml.write_text("mapping:\n  title: Task\n  state: Status\n")
        client = NotionClient("t")
        m = client.load_mapping(str(yml))
        assert m["title"] == "Task"
        assert m["state"] == "Status"
