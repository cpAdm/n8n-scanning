from pathlib import Path
from typing import Any

from csp_loader import CspLookup
from service_analysis import analyse_generic_service
from service_types import ServiceAnalyserProto


class ServiceAnalyser(ServiceAnalyserProto):
    name: str
    display_name: str
    # TODO Check if all paths are actually correct
    version_paths: list[str] = []

    @staticmethod
    def _extract_value_by_path(obj: dict[str, Any], dotted_path: str) -> Any:
        current: Any = obj
        for segment in dotted_path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
            if current is None:
                return None
        return current

    def get_version(self, module: dict[str, Any]) -> Any:
        for path in self.version_paths:
            value = self._extract_value_by_path(module, path)
            if value not in (None, ""):
                return value

        result = module.get("result")
        if isinstance(result, dict):
            return (
                result.get("version")
                or result.get("server_version")
                or result.get("banner")
                or result.get("product")
            )
        return None

    def analyse(self, jsonl_input_file: Path, csp_lookup: CspLookup, output_root: Path):
        analyse_generic_service(self, jsonl_input_file, csp_lookup, output_root)


class MongoDbService(ServiceAnalyser):
    name = "mongodb"
    display_name = "MongoDB"
    version_paths = ["result.build_info.version", "result.version"]


class MySqlService(ServiceAnalyser):
    name = "mysql"
    display_name = "MySQL"
    version_paths = ["result.server_version", "result.version"]


class PostgresService(ServiceAnalyser):
    name = "postgres"
    display_name = "Postgres"
    version_paths = ["result.server_parameters", "result.supported_versions", "result.version"]


class MssqlService(ServiceAnalyser):
    name = "mssql"
    display_name = "MSSQL"
    version_paths = ["result.version", "result.prelogin_options.version.build_number"]


class OracleService(ServiceAnalyser):
    name = "oracle"
    display_name = "Oracle"
    version_paths = ["result.nsn_version", "result.refuse_version", "result.accept_version"]


class RedisService(ServiceAnalyser):
    name = "redis"
    display_name = "Redis"
    version_paths = ["result.version", "result.build_id"]


class MemcachedService(ServiceAnalyser):
    name = "memcached"
    display_name = "Memcached"
    version_paths = ["result.version"]


class RdpService(ServiceAnalyser):
    name = "rdp"
    display_name = "RDP"
    version_paths = ["result.version", "result.protocol_version", "result.selected_protocol"]


class SshService(ServiceAnalyser):
    name = "ssh"
    display_name = "SSH"
    version_paths = ["result.software_version", "result.protocol_version", "result.banner"]


SERVICE_ANALYSERS: list[ServiceAnalyser] = [
    MongoDbService(),
    MySqlService(),
    PostgresService(),
    MssqlService(),
    OracleService(),
    RedisService(),
    MemcachedService(),
    RdpService(),
    SshService(),
]
