# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter

USER_AGENT = "Mozilla/5.0 (compatible; GameplanBot/1.0; link previews)"
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class LinkFetchError(Exception):
	pass


class BlockedURLError(LinkFetchError):
	pass


@dataclass
class FetchedResponse:
	url: str
	content_type: str
	body: bytes


def safe_fetch(
	url: str,
	*,
	allowed_content_types: tuple[str, ...],
	max_bytes: int = MAX_BODY_BYTES,
) -> FetchedResponse:
	for _hop in range(MAX_REDIRECTS + 1):
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

			return FetchedResponse(url=url, content_type=content_type, body=_read_capped(response, max_bytes))
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
		mapped = getattr(address, "ipv4_mapped", None)
		if mapped is not None:
			address = mapped
		if not address.is_global:
			raise BlockedURLError(f"{host} resolves to a non-public address")
		addresses.append(ip_string)

	if not addresses:
		raise LinkFetchError(f"Could not resolve {host}")
	return addresses[0]


class _PinnedAdapter(HTTPAdapter):
	def __init__(self, tls_hostname: str):
		self._tls_hostname = tls_hostname
		super().__init__(max_retries=0)

	def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
		if self._tls_hostname:
			pool_kwargs["server_hostname"] = self._tls_hostname
			pool_kwargs["assert_hostname"] = self._tls_hostname
		super().init_poolmanager(connections, maxsize, block, **pool_kwargs)


def _send_once(url: str, ip: str, accept: str = "*/*") -> requests.Response:
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
	for chunk in response.iter_content(chunk_size=64 * 1024):
		read += len(chunk)
		if read > max_bytes:
			raise LinkFetchError("Response too large")
		chunks.append(chunk)
	return b"".join(chunks)
