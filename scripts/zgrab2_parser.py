import json
from pathlib import Path
from typing import Generator, Literal, NotRequired, Required, TypedDict

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

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


# See official ZGrab2 types: https://github.com/zmap/zgrab2/blob/master/zgrab2_schemas/zgrab2/zgrab2.py
class BaseScanResponse(TypedDict, total=False):
    # Based on zgrab2 base_scan_response schema from the comment above.
    status: Required[StatusValue]
    protocol: Required[str]
    port: Required[int]
    timestamp: Required[str]
    result: NotRequired[dict[str, JsonValue]]
    error: NotRequired[str]


# TODO More accurate types based on service?
class ZGrab2Response(TypedDict, total=False):
    ip: Required[str]
    data: Required[dict[str, BaseScanResponse]]
    domain: NotRequired[str]


def iter_jsonl(path: Path | str) -> Generator[ZGrab2Response, None, None]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if stripped_line := line.strip():
                yield json.loads(stripped_line)
