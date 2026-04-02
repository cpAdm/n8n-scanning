from typing import Any, Protocol


class ServiceAnalyserProto(Protocol):
    name: str
    display_name: str

    def get_version(self, module: dict[str, Any]) -> Any: ...

