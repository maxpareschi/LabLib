import logging
from typing import Any
from pathlib import Path


class BaseOperator:
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    def __init__(self, *args, **kwargs):
        pass

    def __getitem__(self, k: str) -> Any:
        return getattr(self, k)

    def __setitem__(self, k: str, v: Any) -> None:
        if hasattr(self, k):
            setattr(self, k, v)
        else:
            self.log.error(f"Cannot set {k}={v}. Key {k} not found.", stack_info=True)

    def __repr__(self) -> str:
        if hasattr(self, "filename"):
            return f"{self.__class__.__name__}({self.filename})"
        return f"{self})"

    def update_from_path(self, path: Path) -> None:
        """Update operator attributes from a given file path."""
        raise NotImplementedError("update_from_path should be implemented.")
