import json
from pathlib import Path
from typing import List, Optional

class HistoryManager:
    """JSON-based manager for operations history"""

    def __init__(self, history_path: Path = None, limit: int = 10):
        """Initialize history manager with path and undo limit"""
        self.history_path = history_path or (Path.home() / ".tix" / "history.json")
        self.limit = limit
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        """Ensure the history file exists, create if missing"""
        if not self.history_path.exists():
            self._write_data({"undo": [], "redo": []})

    def _read_data(self):
        """Read history data from JSON file"""
        return json.loads(self.history_path.read_text())

    def _write_data(self, data):
        """Write history data to JSON file"""
        self.history_path.write_text(json.dumps(data, indent=2))

    def record(self, operation: dict):
        """Record a new operation into undo stack"""
        data = self._read_data()
        data["undo"].append(operation)
        if len(data["undo"]) > self.limit:
            data["undo"].pop(0)
        data["redo"] = [] 
        self._write_data(data)

    def pop_undo(self):
        """Pop the latest operation form uno stack and push to redo stack"""
        data = self._read_data()
        if not data["undo"]:
            return None
        op = data["undo"].pop()
        data["redo"].append(op)
        self._write_data(data)
        return op

    def pop_redo(self):
        """Pop the latest operation from redo stack and push to undo stack"""
        data = self._read_data()
        if not data["redo"]:
            return None
        op = data["redo"].pop()
        data["undo"].append(op)
        self._write_data(data)
        return op