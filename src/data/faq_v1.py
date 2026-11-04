"""
FAQ v1 数据加载
"""
import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent.parent / "data"
FAQ_FILE = DATA_DIR / "faq_v1.json"


def load_documents(data_file: Path = None) -> list[dict]:
    """加载文档库"""
    file_path = data_file or FAQ_FILE
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
