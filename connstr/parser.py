"""Parsing for the connection string shapes seen in the wild:

  1. URL style:      scheme://user:password@host:port/database?key=value
  2. keyword style:  Key1=Value1;Key2=Value2;...  (ODBC / ADO.NET drivers)
  3. JDBC style:      jdbc:scheme://... or jdbc:scheme://host:port;key=value;...
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urlsplit, parse_qsl, unquote

REDACTED = "********"

# Aliases seen across SQL Server, MySQL, Postgres ODBC/ADO.NET/JDBC drivers.
_HOST_KEYS = {"server", "host", "data source", "addr", "address", "network address"}
_DATABASE_KEYS = {"database", "initial catalog", "databasename"}
_USER_KEYS = {"uid", "user id", "user", "username"}
_PASSWORD_KEYS = {"pwd", "password"}
_PORT_KEYS = {"port"}


@dataclass
class ConnectionInfo:
    raw: str
    format: str  # "url", "keyword", or "jdbc"
    scheme: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    params: Dict[str, str] = field(default_factory=dict)

    def to_dict(self, reveal: bool = False) -> dict:
        return {
            "format": self.format,
            "scheme": self.scheme,
            "user": self.user,
            "password": self.password if (reveal or self.password is None) else REDACTED,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "params": dict(self.params),
        }


def parse(text: str) -> ConnectionInfo:
    text = text.strip()
    if text.lower().startswith("jdbc:"):
        return _parse_jdbc(text)
    if "://" in text.split(";", 1)[0]:
        return _parse_url(text)
    return _parse_keyword(text)


def _parse_url(text: str) -> ConnectionInfo:
    parts = urlsplit(text)
    params = {k: v for k, v in parse_qsl(parts.query, keep_blank_values=True)}
    return ConnectionInfo(
        raw=text,
        format="url",
        scheme=parts.scheme or None,
        user=unquote(parts.username) if parts.username else None,
        password=unquote(parts.password) if parts.password else None,
        host=parts.hostname or None,
        port=parts.port,
        database=parts.path.lstrip("/") or None,
        params=params,
    )


def _apply_keyword_pair(info: ConnectionInfo, key: str, value: str) -> None:
    key = key.strip().lower()
    value = value.strip()

    if key in _HOST_KEYS:
        # SQL Server drivers pack the port onto the host: "tcp:host,1433"
        host_value = value
        if ":" in host_value:
            host_value = host_value.split(":", 1)[1]
        if "," in host_value:
            host_value, port_value = host_value.split(",", 1)
            if port_value.strip().isdigit():
                info.port = int(port_value.strip())
        info.host = host_value.strip() or None
    elif key in _DATABASE_KEYS:
        info.database = value or None
    elif key in _USER_KEYS:
        info.user = value or None
    elif key in _PASSWORD_KEYS:
        info.password = value or None
    elif key in _PORT_KEYS and value.isdigit():
        info.port = int(value)
    else:
        info.params[key] = value


def _apply_keyword_segments(info: ConnectionInfo, text: str) -> None:
    for segment in text.split(";"):
        segment = segment.strip()
        if not segment or "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        _apply_keyword_pair(info, key, value)


def _parse_keyword(text: str) -> ConnectionInfo:
    info = ConnectionInfo(raw=text, format="keyword")
    _apply_keyword_segments(info, text)
    return info


def _parse_jdbc(text: str) -> ConnectionInfo:
    # JDBC URLs are "jdbc:" plus a driver-specific sub-URL. Most drivers (postgresql,
    # mysql, ...) use a normal scheme://host/database?query shape underneath, but SQL
    # Server's driver puts host:port straight into the authority and everything else
    # -- including the database name -- into "key=value" pairs separated by ";".
    body = text[len("jdbc:") :]
    scheme, sep, rest = body.partition("://")
    if not sep:
        # No authority at all, e.g. "jdbc:h2:mem:testdb" for an embedded database.
        # There's no host/database structure to pull apart, just a driver name.
        return ConnectionInfo(raw=text, format="jdbc", scheme=scheme.split(":", 1)[0] or None)

    idx = len(rest)
    for ch in ("/", "?", ";"):
        pos = rest.find(ch)
        if pos != -1 and pos < idx:
            idx = pos
    authority, remainder = rest[:idx], rest[idx:]

    authority_parts = urlsplit(f"{scheme}://{authority}")
    info = ConnectionInfo(
        raw=text,
        format="jdbc",
        scheme=scheme or None,
        user=unquote(authority_parts.username) if authority_parts.username else None,
        password=unquote(authority_parts.password) if authority_parts.password else None,
        host=authority_parts.hostname or None,
        port=authority_parts.port,
    )

    if remainder.startswith(";"):
        _apply_keyword_segments(info, remainder[1:])
    elif remainder:
        parts = urlsplit(f"{scheme}://{authority}{remainder}")
        info.database = parts.path.lstrip("/") or None
        info.params = {k: v for k, v in parse_qsl(parts.query, keep_blank_values=True)}

    return info
