import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from database import db as db_module


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db_module, "DB_PATH", path)
    db_module.init_db()
    return path


@pytest.fixture
def client(db_path):
    db_module.seed_db()
    app_module.app.testing = True
    with app_module.app.test_client() as test_client:
        yield test_client
