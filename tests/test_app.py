from pathlib import Path

from streamlit.testing.v1 import AppTest

import core.summary
from core.data import load_snapshot


def test_app_runs_without_error(monkeypatch):
    # Fake the API so the test never calls the internet.
    sample = load_snapshot(Path("data/sample.json"))
    monkeypatch.setattr(core.summary, "fetch_snapshots", lambda start, end: [sample])
    # The path is relative to this test file.
    app = AppTest.from_file("../streamlit_app.py").run()
    assert not app.exception
