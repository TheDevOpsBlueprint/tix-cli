import json
from pathlib import Path
from typing import List, Optional
from tix.models import Context


class ContextStorage:
    """JSON-based storage for contexts"""

    def __init__(self, storage_path: Path = None):
        """Initialize context storage with default or custom path"""
        self.storage_path = storage_path or (Path.home() / ".tix" / "contexts.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_context_path = Path.home() / ".tix" / "active_context"
        self._ensure_file()

    def _ensure_file(self):
        """Ensure storage file exists with default context"""
        if not self.storage_path.exists():
            default_context = Context(name="default", description="Default context")
            self._write_data({"contexts": [default_context.to_dict()]})
        
        # Ensure active context is set
        if not self.active_context_path.exists():
            self.set_active_context("default")

    def _read_data(self) -> dict:
        """Read raw data from storage"""
        try:
            raw = json.loads(self.storage_path.read_text())
            if isinstance(raw, dict) and "contexts" in raw:
                return raw
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        
        # Fallback if corrupt or missing
        default_context = Context(name="default", description="Default context")
        return {"contexts": [default_context.to_dict()]}

    def _write_data(self, data: dict):
        """Write data to storage"""
        self.storage_path.write_text(json.dumps(data, indent=2))

    def load_contexts(self) -> List[Context]:
        """Load all contexts from storage"""
        data = self._read_data()
        return [Context.from_dict(item) for item in data["contexts"]]

    def save_contexts(self, contexts: List[Context]):
        """Save all contexts to storage"""
        data = {"contexts": [context.to_dict() for context in contexts]}
        self._write_data(data)

    def add_context(self, name: str, description: Optional[str] = None) -> Context:
        """Add a new context and return it"""
        contexts = self.load_contexts()
        
        # Check if context already exists
        if any(c.name == name for c in contexts):
            raise ValueError(f"Context '{name}' already exists")
        
        new_context = Context(name=name, description=description)
        contexts.append(new_context)
        self.save_contexts(contexts)
        return new_context

    def get_context(self, name: str) -> Optional[Context]:
        """Get a specific context by name"""
        contexts = self.load_contexts()
        for context in contexts:
            if context.name == name:
                return context
        return None

    def delete_context(self, name: str) -> bool:
        """Delete a context by name, return True if deleted"""
        if name == "default":
            raise ValueError("Cannot delete the default context")
        
        contexts = self.load_contexts()
        original_count = len(contexts)
        new_contexts = [c for c in contexts if c.name != name]
        
        if len(new_contexts) < original_count:
            self.save_contexts(new_contexts)
            
            # If deleted context was active, switch to default
            if self.get_active_context() == name:
                self.set_active_context("default")
            
            return True
        return False

    def get_active_context(self) -> str:
        """Get the name of the active context"""
        try:
            return self.active_context_path.read_text().strip()
        except FileNotFoundError:
            return "default"

    def set_active_context(self, name: str):
        """Set the active context"""
        context = self.get_context(name)
        if not context:
            raise ValueError(f"Context '{name}' does not exist")
        
        self.active_context_path.write_text(name)

    def context_exists(self, name: str) -> bool:
        """Check if a context exists"""
        return self.get_context(name) is not None
