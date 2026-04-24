from typing import Any, Protocol


class ServiceAnalyserProto(Protocol):
    name: str
    display_name: str
    nvd_cpe_prefixes: tuple[str, ...]

    def get_version(self, result: dict[str, Any] | None) -> str | None: ...

    def extra_analysis(
        self,
        frame: Any,
        csp_lookup: Any,
        output_root: Any,
        vuln_lookup: Any,
    ) -> None: ...
