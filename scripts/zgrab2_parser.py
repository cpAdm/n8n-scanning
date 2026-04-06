import json
from pathlib import Path
from typing import Generator, Literal, NotRequired, Required, TypedDict, Any

type StatusValue = Literal[
    "success",
    "connection-refused",
    "connection-timeout",
    "connection-closed",
    "io-timeout",
    "protocol-error",
    "application-error",
    "unknown-error",
]


class BaseScanResponse(TypedDict, total=False):
    # Based on zgrab2 base_scan_response schema from the comment above.
    status: Required[StatusValue]
    protocol: Required[str]
    port: Required[int]
    timestamp: Required[str]
    # See https://github.com/zmap/zgrab2/tree/master/zgrab2_schemas/zgrab2 for more accurate types based on the service
    result: NotRequired[dict[str, Any]]
    error: NotRequired[str]


# Based on https://github.com/zmap/zgrab2/blob/master/zgrab2_schemas/zgrab2/zgrab2.py
class ZGrab2Response(TypedDict, total=False):
    ip: Required[str]
    data: Required[dict[str, BaseScanResponse]]
    domain: NotRequired[str]


def iter_jsonl(path: Path | str) -> Generator[ZGrab2Response, None, None]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if stripped_line := line.strip():
                yield json.loads(stripped_line)


def extract_value_by_path(obj: BaseScanResponse, dotted_path: str) -> Any:
    current: Any = obj
    for segment in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current
