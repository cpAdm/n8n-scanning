from typing import Any, Protocol

from zgrab2_parser import BaseScanResponse


class ServiceAnalyserProto(Protocol):
    name: str
    display_name: str

    def get_version(self, module: BaseScanResponse) -> Any: ...
