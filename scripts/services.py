from pathlib import Path
from typing import Any

from csp_loader import CspLookup
from service_analysis import analyse_generic_service
from service_types import ServiceAnalyserProto
from vuln_lookup import NvdVulnerabilityLookup


class ServiceAnalyser(ServiceAnalyserProto):
    name: str
    display_name: str
    # Can be found via https://nvd.nist.gov/products/cpe/search
    nvd_cpe_prefixes: tuple[str, ...] = ()

    def get_version(self, result: dict[str, Any] | None) -> str | None:
        return None

    def analyse(self,
                jsonl_input_file: Path,
                csp_lookup: CspLookup,
                output_root: Path,
                vuln_lookup: NvdVulnerabilityLookup):
        analyse_generic_service(self, jsonl_input_file, csp_lookup, output_root, vuln_lookup)


# TODO Also interesting:
#  result.build_info.build_environment.target_os
#  Read databases: jq -r '.data.mongodb.result.database_info // empty' data/2026-03-26T15-33-23-646Z-zgrab2-output.json | sort -u
#   - also seems to indicate that some databases have been pwned
class MongoDbService(ServiceAnalyser):
    name = "mongodb"
    display_name = "MongoDB"
    nvd_cpe_prefixes = ("cpe:2.3:a:mongodb:mongodb:",)

    def get_version(self, result):
        return result.get("build_info", {}).get("version")


class MySqlService(ServiceAnalyser):
    name = "mysql"
    display_name = "MySQL"
    nvd_cpe_prefixes = ("cpe:2.3:a:oracle:mysql:", "cpe:2.3:a:mysql:mysql:")

    def get_version(self, result):
        return result.get("server_version")


class PostgresService(ServiceAnalyser):
    name = "postgres"
    display_name = "Postgres"
    nvd_cpe_prefixes = ("cpe:2.3:a:postgresql:postgresql:",)


# TODO Some services have result.encrypt_mode set to ENCRYPT_OFF/ENCRYPT_NOT_SUP
class MssqlService(ServiceAnalyser):
    name = "mssql"
    display_name = "MSSQL"
    nvd_cpe_prefixes = ()

    def get_version(self, result):
        return result.get("version")


class OracleService(ServiceAnalyser):
    name = "oracle"
    display_name = "Oracle Database"
    nvd_cpe_prefixes = ("cpe:2.3:a:oracle:database_server:", "cpe:2.3:a:oracle:oracle_database:")


# TODO Also interesting: result.os, result.uptime_in_seconds, result.used_memory, result.total_connections_received, result.total_commands_processed
class RedisService(ServiceAnalyser):
    name = "redis"
    display_name = "Redis"
    nvd_cpe_prefixes = ("cpe:2.3:a:redis:redis:", "cpe:2.3:a:redislabs:redis:")

    def get_version(self, result):
        return result.get("version")


# TODO Also interesting: result.libevent_version, result.stats.uptime, result.stats.rusage_system, many more stats
class MemcachedService(ServiceAnalyser):
    name = "memcached"
    display_name = "Memcached"
    nvd_cpe_prefixes = ("cpe:2.3:a:memcached:memcached:",)

    def get_version(self, result):
        return result.get("version")


class RdpService(ServiceAnalyser):
    name = "rdp"
    display_name = "RDP"
    # ntlm.os_version below only returns 3-part version, not full 4-part which we need to match to CPEs with confidence
    nvd_cpe_prefixes = ()

    def get_version(self, result):
        return result.get("ntlm", {}).get("os_version") # E.g. 10.0.20348.0, 6.3.9600.0


# TODO Also see other interesting fields of result.server_id
class SshService(ServiceAnalyser):
    name = "ssh"
    display_name = "SSH"
    # We don't know the exact SSH server version that is used
    nvd_cpe_prefixes = ()

    def get_version(self, result):
        return result.get("server_id", {}).get("version")  # E.g. 1.99, 2.0, 2.1


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
