from typing import Any, Protocol

from zgrab2_parser import BaseScanResponse


class ServiceAnalyserProto(Protocol):
    name: str
    display_name: str
    nvd_cpe_prefixes: tuple[str, ...]

    def get_version(self, result: dict[str, Any] | None) -> str | None: ...
