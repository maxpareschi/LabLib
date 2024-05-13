import logging
from typing import Any, Union
from pathlib import Path


class BaseOperator:
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    def __init__(self, path: Union[str, Path], *args, **kwargs):
        self.path = path
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.update(*args, **kwargs)

    def __getitem__(self, k: str) -> Any:
        return getattr(self, k)

    def __setitem__(self, k: str, v: Any) -> None:
        if hasattr(self, k):
            setattr(self, k, v)
        else:
            raise AttributeError(f"Attribute is not implemented: {k}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{self.__dict__}"

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: Union[str, Path]) -> None:
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise Exception(f"Path does not exist: {path}")

        self._path = path

    @property
    def filepath(self) -> Path:
        return self.path

    def update(self, *args, **kwargs) -> None:
        """Update operator attributes from a given file path."""
        raise NotImplementedError("update should be implemented.")
