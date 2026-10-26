# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import json
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import frappe
from bs4 import BeautifulSoup
from requests.utils import requote_uri

from gameplan.safe_fetch import BlockedURLError, LinkFetchError, safe_fetch

MAX_FETCH_ATTEMPTS = 3
MAX_URL_LENGTH = 500
STALE_AFTER_DAYS = 30

JSON_TYPES = ("application/json", "text/json", "text/javascript")
HTML_TYPES = ("text/html", "application/xhtml+xml")

TRACKING_PARAMS = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igsh", "igshid", "si"}

PROVIDER_DOMAINS = [
	("YouTube", ("youtube.com", "youtu.be", "youtube-nocookie.com")),
	("Vimeo", ("vimeo.com",)),
	("Reddit", ("reddit.com", "redd.it")),
	("X", ("x.com", "twitter.com")),
	("Loom", ("loom.com",)),
	("Spotify", ("spotify.com",)),
	("SoundCloud", ("soundcloud.com",)),
	("Wikipedia", ("wikipedia.org",)),
]

OEMBED_ENDPOINTS = {
	"YouTube": "https://www.youtube.com/oembed",
	"Vimeo": "https://vimeo.com/api/oembed.json",
	"Reddit": "https://www.reddit.com/oembed",
	"X": "https://publish.twitter.com/oembed",
	"Loom": "https://www.loom.com/v1/oembed",
	"Spotify": "https://open.spotify.com/oembed",
	"SoundCloud": "https://soundcloud.com/oembed",
}

NOT_FOUND_TITLES = {
	"404",
	"error 404",
	"404 error",
	"not found",
	"page not found",
	"404 not found",
	"404 - page not found",
	"404 | page not found",
	"page missing or moved",
	"this page could not be found",
}


def normalize_url(url: str) -> str | None:
	if not url:
		return None

	try:
		parts = urlsplit(url.strip())
		host = (parts.hostname or "").lower().rstrip(".")
		port = parts.port
	except ValueError:
		return None

	scheme = parts.scheme.lower()
	if scheme not in ("http", "https") or not host:
		return None

	if ":" in host:
		host = f"[{host}]"

	default_port = 80 if scheme == "http" else 443
	netloc = host if port in (None, default_port) else f"{host}:{port}"

	query = urlencode(
		[
			(key, value)
			for key, value in parse_qsl(parts.query, keep_blank_values=True)
			if not is_tracking_param(key)
		]
	)
	fragment = parts.fragment if parts.fragment.startswith("/") else ""

	normalized = urlunsplit((scheme, netloc, parts.path or "/", query, fragment))
	return normalized if len(normalized) <= MAX_URL_LENGTH else None


def is_tracking_param(key: str) -> bool:
	lowered = key.lower()
	return lowered.startswith("utm_") or lowered in TRACKING_PARAMS


def detect_provider(url: str) -> str:
	host = urlsplit(url).hostname or ""
	for provider, domains in PROVIDER_DOMAINS:
		if any(host == domain or host.endswith("." + domain) for domain in domains):
			return provider
	return "Other"


def get_or_fetch_preview(url: str) -> dict | None:
	url = normalize_url(url)
	if not url or is_own_site(url):
		return None

	preview = _find_preview(url) or _insert_preview(url)
	if preview.status == "Pending" or _is_stale(preview):
		fill_preview(preview)

	return _serialize(preview)


def is_own_site(url: str) -> bool:
	own_host = (urlsplit(frappe.utils.get_url()).hostname or "").lower()
	return bool(own_host) and urlsplit(url).hostname == own_host


def _find_preview(url: str, for_update: bool = False):
	name = frappe.db.get_value("GP Link Preview", {"url": url}, for_update=for_update)
	return frappe.get_doc("GP Link Preview", name, for_update=for_update) if name else None


def _insert_preview(url: str):
	preview = frappe.get_doc({"doctype": "GP Link Preview", "url": url, "provider": detect_provider(url)})
	frappe.db.savepoint("link_preview_insert")
	try:
		preview.insert(ignore_permissions=True)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		frappe.db.rollback(save_point="link_preview_insert")
		existing = _find_preview(url, for_update=True)
		if existing is None:
			raise
		return existing
	return preview


def _is_stale(preview) -> bool:
	if not preview.fetched_on:
		return True
	age = frappe.utils.now_datetime() - frappe.utils.get_datetime(preview.fetched_on)
	return age.days >= STALE_AFTER_DAYS


def _serialize(preview) -> dict | None:
	if preview.status != "Fetched" or not preview.title:
		return None
	return {
		"url": preview.url,
		"title": preview.title,
		"description": preview.description,
		"image": preview.image,
		"site_name": preview.site_name,
		"provider": preview.provider,
	}


def fill_preview(preview) -> bool:
	fetched = False
	try:
		data = fetch_preview_data(preview.url, preview.provider)
	except BlockedURLError as error:
		preview.status = "Blocked"
		preview.fetch_error = str(error)[:400]
	except LinkFetchError as error:
		_record_failure(preview, str(error)[:400])
	except Exception:
		frappe.log_error(f"Link preview fetch crashed for {preview.url}")
		_record_failure(preview, "Unexpected error while fetching")
	else:
		_apply(preview, data)
		fetched = True

	preview.fetched_on = frappe.utils.now_datetime()
	preview.save(ignore_permissions=True)
	return fetched


def _record_failure(preview, error: str):
	preview.fetch_error = error
	if preview.status == "Fetched":
		return
	preview.fetch_attempts = (preview.fetch_attempts or 0) + 1
	preview.status = "Failed" if preview.fetch_attempts >= MAX_FETCH_ATTEMPTS else "Pending"


def _apply(preview, data: dict):
	preview.title = (data.get("title") or "")[:400]
	preview.description = (data.get("description") or "")[:1000]
	preview.site_name = (data.get("site_name") or "")[:140]
	image = data.get("image") or ""
	preview.image = image if len(image) <= MAX_URL_LENGTH else ""
	preview.status = "Fetched"
	preview.fetch_error = ""
	preview.fetch_attempts = 0


def fetch_preview_data(url: str, provider: str) -> dict:
	endpoint = OEMBED_ENDPOINTS.get(provider)
	if endpoint:
		return fetch_oembed(endpoint, url)

	if provider == "Wikipedia":
		data = fetch_wikipedia_summary(url)
		if data is not None:
			return data

	return fetch_open_graph(url)


def fetch_oembed(endpoint: str, url: str) -> dict:
	query = urlencode({"url": url, "format": "json"})
	response = safe_fetch(f"{endpoint}?{query}", allowed_content_types=JSON_TYPES)
	payload = _parse_json(response.body)

	title = payload.get("title") or ""
	description = ""
	if not title and payload.get("html"):
		title = payload.get("author_name") or ""
		soup = BeautifulSoup(payload["html"], "html.parser")
		tweet_text = soup.find("p")
		description = (tweet_text or soup).get_text(" ", strip=True)

	return {
		"title": title or payload.get("author_name") or "",
		"description": description,
		"image": payload.get("thumbnail_url") or "",
		"site_name": payload.get("provider_name") or "",
	}


def fetch_wikipedia_summary(url: str) -> dict | None:
	parts = urlsplit(url)
	prefix = "/wiki/"
	if not parts.path.startswith(prefix):
		return None
	title = parts.path[len(prefix) :]
	if not title or "/" in title:
		return None

	endpoint = f"https://{parts.hostname}/api/rest_v1/page/summary/{title}"
	response = safe_fetch(endpoint, allowed_content_types=JSON_TYPES)
	payload = _parse_json(response.body)
	thumbnail = payload.get("thumbnail") or {}

	return {
		"title": payload.get("title") or "",
		"description": payload.get("extract") or "",
		"image": thumbnail.get("source") or "",
		"site_name": "Wikipedia",
	}


def fetch_open_graph(url: str) -> dict:
	response = safe_fetch(url, allowed_content_types=HTML_TYPES)
	return parse_open_graph(response.body, response.url)


def parse_open_graph(html: bytes | str, base_url: str) -> dict:
	soup = BeautifulSoup(html, "html.parser")

	def meta(*names) -> str:
		for name in names:
			tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
			content = tag.get("content") if tag else None
			if content:
				return content.strip()
		return ""

	title = meta("og:title", "twitter:title")
	if not title and soup.title and soup.title.string:
		title = soup.title.string.strip()

	if title.strip().lower() in NOT_FOUND_TITLES:
		raise LinkFetchError("Page reports itself as not found")

	image = meta("og:image", "twitter:image", "image")
	if image:
		image = requote_uri(urljoin(base_url, image))

	return {
		"title": title,
		"description": meta("og:description", "twitter:description", "description"),
		"image": image,
		"site_name": meta("og:site_name") or (urlsplit(base_url).hostname or "").removeprefix("www."),
	}


def _parse_json(body: bytes) -> dict:
	try:
		payload = json.loads(body)
	except ValueError as error:
		raise LinkFetchError("Response was not valid JSON") from error
	if not isinstance(payload, dict):
		raise LinkFetchError("Response was not a JSON object")
	return payload
