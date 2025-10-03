class ContextStorage:
    """Minimal stub for context storage. Extend as needed."""
    def __init__(self):
        self._active_context = None

    def get_active_context(self):
        return self._active_context or "default"

    def set_active_context(self, context):
        self._active_context = context

    def list_contexts(self):
        return ["default"]

    def __repr__(self):
        return f"<ContextStorage active={self._active_context}>"
