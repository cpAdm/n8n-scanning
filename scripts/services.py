from pathlib import Path
from typing import Any

from csp_loader import CspLookup
from service_analysis import analyse_generic_service
from service_types import ServiceAnalyserProto
from zgrab2_parser import BaseScanResponse, extract_value_by_path


# TODO Check for all services all the CLI options to see if we can get more info
class ServiceAnalyser(ServiceAnalyserProto):
    name: str
    display_name: str
    version_path: str | None = None

    def get_version(self, module: BaseScanResponse) -> Any:
        if not self.version_path:
            return None
        return extract_value_by_path(module, self.version_path)

    def analyse(self, jsonl_input_file: Path, csp_lookup: CspLookup, output_root: Path):
        analyse_generic_service(self, jsonl_input_file, csp_lookup, output_root)


# TODO Also interesting:
#  result.build_info.build_environment.target_os
#  Read databases: jq -r '.data.mongodb.result.database_info // empty' data/2026-03-26T15-33-23-646Z-zgrab2-output.json | sort -u
#   - also seems to indicate that some databases have been pwned
class MongoDbService(ServiceAnalyser):
    name = "mongodb"
    display_name = "MongoDB"
    version_path = "result.build_info.version"


class MySqlService(ServiceAnalyser):
    name = "mysql"
    display_name = "MySQL"
    version_path = "result.server_version"


class PostgresService(ServiceAnalyser):
    name = "postgres"
    display_name = "Postgres"
    # TODO Maybe "result.supported_versions"? -> does need some parsing
    version_path = None


# TODO Some services have result.encrypt_mode set to ENCRYPT_OFF/ENCRYPT_NOT_SUP
class MssqlService(ServiceAnalyser):
    name = "mssql"
    display_name = "MSSQL"
    version_path = "result.version"


class OracleService(ServiceAnalyser):
    name = "oracle"
    display_name = "Oracle"
    version_path = None


# TODO Also interesting: result.os, result.uptime_in_seconds, result.used_memory, result.total_connections_received, result.total_commands_processed
class RedisService(ServiceAnalyser):
    name = "redis"
    display_name = "Redis"
    version_path = "result.version"


# TODO Also interesting: result.libevent_version, result.stats.uptime, result.stats.rusage_system, many more stats
class MemcachedService(ServiceAnalyser):
    name = "memcached"
    display_name = "Memcached"
    version_path = "result.version"


class RdpService(ServiceAnalyser):
    name = "rdp"
    display_name = "RDP"
    version_path = "result.ntlm.os_version"


# TODO Also see other interesting fields of result.server_id
class SshService(ServiceAnalyser):
    name = "ssh"
    display_name = "SSH"
    version_path = "result.server_id.version"  # E.g. 1.99/2.0/2.1


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
