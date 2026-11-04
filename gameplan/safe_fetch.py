# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import ipaddress
import socket
import threading
from contextvars import ContextVar
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

USER_AGENT = "Mozilla/5.0 (compatible; GameplanBot/1.0; link previews)"
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15
TOTAL_TIMEOUT = 20
READ_CHUNK_BYTES = 8 * 1024
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")


class LinkFetchError(Exception):
	pass


class BlockedURLError(LinkFetchError):
	pass


@dataclass
class FetchedResponse:
	url: str
	body: bytes


def safe_fetch(
	url: str,
	*,
	allowed_content_types: tuple[str, ...],
	max_bytes: int = MAX_BODY_BYTES,
) -> FetchedResponse:
	watchdog = _Watchdog(TOTAL_TIMEOUT)
	token = _active_watchdog.set(watchdog)
	watchdog.start()
	try:
		result = _follow(url, allowed_content_types, max_bytes, watchdog)
	except Exception as error:
		if watchdog.expired:
			raise LinkFetchError("Fetch took too long") from error
		raise
	finally:
		watchdog.stop()
		_active_watchdog.reset(token)
	if watchdog.expired:
		raise LinkFetchError("Fetch took too long")
	return result


def _follow(
	url: str, allowed_content_types: tuple[str, ...], max_bytes: int, watchdog: "_Watchdog"
) -> FetchedResponse:
	for _hop in range(MAX_REDIRECTS + 1):
		if watchdog.expired:
			raise LinkFetchError("Fetch took too long")
		parts = urlsplit(url)
		scheme = parts.scheme.lower()
		if scheme not in ("http", "https"):
			raise BlockedURLError(f"Scheme {scheme or 'none'} is not allowed")

		host = parts.hostname
		if not host:
			raise BlockedURLError("URL has no host")

		port = parts.port or (443 if scheme == "https" else 80)
		ip = resolve_public_ip(host, port)

		accept = ", ".join(allowed_content_types) + ", */*;q=0.1"
		response = _send_once(url, ip, accept)
		try:
			if response.status_code in REDIRECT_STATUSES:
				location = response.headers.get("Location")
				if not location:
					raise LinkFetchError("Redirect without a Location header")
				url = urljoin(url, location)
				continue

			if response.status_code != 200:
				raise LinkFetchError(f"HTTP {response.status_code}")

			content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
			if not content_type.startswith(allowed_content_types):
				raise LinkFetchError(f"Content type {content_type or 'unknown'} is not allowed")

			return FetchedResponse(url=url, body=_read_capped(response, max_bytes))
		finally:
			response.close()

	raise LinkFetchError("Too many redirects")


def resolve_public_ip(host: str, port: int) -> str:
	try:
		infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
	except OSError as error:
		raise LinkFetchError(f"Could not resolve {host}") from error

	addresses = []
	for info in infos:
		ip_string = info[4][0]
		try:
			address = ipaddress.ip_address(ip_string)
		except ValueError as error:
			raise LinkFetchError(f"Bad address for {host}") from error
		if not is_public_address(address):
			raise BlockedURLError(f"{host} resolves to a non-public address")
		addresses.append(ip_string)

	if not addresses:
		raise LinkFetchError(f"Could not resolve {host}")
	return addresses[0]


def is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
	if address.version == 6:
		if address.ipv4_mapped is not None:
			return address.ipv4_mapped.is_global
		if address in NAT64_PREFIX:
			return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF).is_global
		embedded = [address.sixtofour, *(address.teredo or ())]
		if any(ip is not None and not ip.is_global for ip in embedded):
			return False
	return address.is_global


class _Watchdog:
	def __init__(self, seconds: float):
		self.expired = False
		self._lock = threading.Lock()
		self._sockets: list[socket.socket] = []
		self._timer = threading.Timer(seconds, self._expire)
		self._timer.daemon = True

	def start(self):
		self._timer.start()

	def watch(self, sock: socket.socket):
		with self._lock:
			watched = sock.dup()
			self._sockets.append(watched)
			if self.expired:
				_shutdown(watched)

	def _expire(self):
		with self._lock:
			self.expired = True
			for sock in self._sockets:
				_shutdown(sock)

	def stop(self):
		self._timer.cancel()
		with self._lock:
			for sock in self._sockets:
				sock.close()
			self._sockets.clear()


def _shutdown(sock: socket.socket):
	try:
		sock.shutdown(socket.SHUT_RDWR)
	except OSError:
		pass


_active_watchdog: ContextVar[_Watchdog | None] = ContextVar("safe_fetch_watchdog", default=None)


class _WatchedConnection:
	def _new_conn(self):
		sock = super()._new_conn()
		watchdog = _active_watchdog.get()
		if watchdog:
			watchdog.watch(sock)
		return sock


class _WatchedHTTPConnection(_WatchedConnection, HTTPConnection):
	pass


class _WatchedHTTPSConnection(_WatchedConnection, HTTPSConnection):
	pass


class _WatchedHTTPPool(HTTPConnectionPool):
	ConnectionCls = _WatchedHTTPConnection


class _WatchedHTTPSPool(HTTPSConnectionPool):
	ConnectionCls = _WatchedHTTPSConnection


class _PinnedAdapter(HTTPAdapter):
	def __init__(self, tls_hostname: str):
		self._tls_hostname = tls_hostname
		super().__init__(max_retries=0)

	def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
		if self._tls_hostname:
			pool_kwargs["server_hostname"] = self._tls_hostname
			pool_kwargs["assert_hostname"] = self._tls_hostname
		super().init_poolmanager(connections, maxsize, block, **pool_kwargs)
		self.poolmanager.pool_classes_by_scheme = {"http": _WatchedHTTPPool, "https": _WatchedHTTPSPool}


def _send_once(url: str, ip: str, accept: str) -> requests.Response:
	parts = urlsplit(url)

	netloc = f"[{ip}]" if ":" in ip else ip
	if parts.port:
		netloc = f"{netloc}:{parts.port}"
	ip_url = parts._replace(netloc=netloc).geturl()

	host_header = parts.hostname if not parts.port else f"{parts.hostname}:{parts.port}"

	session = requests.Session()
	session.trust_env = False
	adapter = _PinnedAdapter(parts.hostname if parts.scheme == "https" else "")
	session.mount("https://", adapter)
	session.mount("http://", adapter)

	try:
		return session.get(
			ip_url,
			headers={"Host": host_header, "User-Agent": USER_AGENT, "Accept": accept},
			timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
			stream=True,
			allow_redirects=False,
		)
	except requests.RequestException as error:
		raise LinkFetchError(str(error)[:200]) from error


def _read_capped(response: requests.Response, max_bytes: int) -> bytes:
	declared = response.headers.get("Content-Length")
	if declared and declared.isdigit() and int(declared) > max_bytes:
		raise LinkFetchError("Response too large")

	chunks = []
	read = 0
	for chunk in response.iter_content(chunk_size=READ_CHUNK_BYTES):
		read += len(chunk)
		if read > max_bytes:
			raise LinkFetchError("Response too large")
		chunks.append(chunk)
	return b"".join(chunks)
