# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

import ipaddress
import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe

import gameplan.safe_fetch as safe_fetch_module
from gameplan.api import LINK_PREVIEW_QUOTA, get_link_preview
from gameplan.link_previews import (
	MAX_FETCH_ATTEMPTS,
	STALE_AFTER_DAYS,
	detect_provider,
	fill_preview,
	get_or_fetch_preview,
	normalize_url,
	parse_open_graph,
)
from gameplan.safe_fetch import BlockedURLError, LinkFetchError, safe_fetch
from gameplan.tests.base import GameplanTestCase
from gameplan.tests.fixtures import (
	create_comment,
	create_community,
	create_discussion,
	create_space,
	declared_http_methods,
)

PUBLIC_IP = "93.184.216.34"
HTML_HEADERS = {"Content-Type": "text/html"}
_real_resolve = safe_fetch_module.resolve_public_ip


class FakeResponse:
	def __init__(self, status_code=200, headers=None, body=b""):
		self.status_code = status_code
		self.headers = headers or {}
		self._body = body

	def iter_content(self, chunk_size):
		for start in range(0, len(self._body), chunk_size):
			yield self._body[start : start + chunk_size]

	def close(self):
		pass


def _stubbed_resolve(host, port):
	try:
		ipaddress.ip_address(host)
	except ValueError:
		return PUBLIC_IP
	return _real_resolve(host, port)


def fake_network(response):
	return (
		patch.object(safe_fetch_module, "resolve_public_ip", side_effect=_stubbed_resolve),
		patch.object(safe_fetch_module, "_send_once", return_value=response),
	)


def fetched(body, content_type="text/html", url="https://example.com/post"):
	return SimpleNamespace(url=url, content_type=content_type, body=body)


class SafeFetchTestCase(GameplanTestCase):
	def test_rejects_bad_schemes(self):
		for url in ("ftp://example.com/x", "file:///etc/passwd", "javascript:alert(1)"):
			with self.assertRaises(BlockedURLError, msg=url):
				safe_fetch(url, allowed_content_types=("text/html",))

	def test_rejects_private_addresses(self):
		for url in (
			"http://127.0.0.1/x",
			"http://10.0.0.5/x",
			"http://192.168.1.1/x",
			"http://169.254.169.254/latest/meta-data/",
			"http://[::1]/x",
			"http://0.0.0.0/x",
			"http://100.64.0.1/x",
			"http://[::ffff:10.0.0.5]/x",
			"http://[64:ff9b::a00:5]/x",
			"http://[64:ff9b::7f00:1]/x",
			"http://[2002:a00:5::1]/x",
		):
			with self.assertRaises(BlockedURLError, msg=url):
				safe_fetch(url, allowed_content_types=("text/html",))

	def test_embedded_ipv4_addresses_are_checked(self):
		for address, public in (
			("64:ff9b::a00:5", False),
			("64:ff9b::5db8:d822", True),
			("2002:a00:5::1", False),
			("2001:0:a00:5::f5ff:fffa", False),
			("::ffff:93.184.216.34", True),
		):
			self.assertEqual(
				safe_fetch_module.is_public_address(ipaddress.ip_address(address)), public, msg=address
			)

	def test_slow_body_hits_the_total_time_cap(self):
		clock = SimpleNamespace(now=0)
		response = FakeResponse(200, HTML_HEADERS, b"x" * (safe_fetch_module.READ_CHUNK_BYTES * 4))
		chunks = response.iter_content

		def slow_chunks(chunk_size):
			for chunk in chunks(chunk_size):
				clock.now += 10
				yield chunk

		response.iter_content = slow_chunks
		resolve, send = fake_network(response)
		with (
			resolve,
			send,
			patch.object(safe_fetch_module, "time", SimpleNamespace(monotonic=lambda: clock.now)),
			self.assertRaisesRegex(LinkFetchError, "too long"),
		):
			safe_fetch("https://example.com/slow", allowed_content_types=("text/html",))

	def test_slow_redirect_chain_hits_the_total_time_cap(self):
		clock = SimpleNamespace(now=0)

		def slow_redirect(*args):
			clock.now += 15
			return FakeResponse(302, {"Location": "https://example.com/next"})

		with (
			patch.object(safe_fetch_module, "resolve_public_ip", side_effect=_stubbed_resolve),
			patch.object(safe_fetch_module, "_send_once", side_effect=slow_redirect) as send,
			patch.object(safe_fetch_module, "time", SimpleNamespace(monotonic=lambda: clock.now)),
			self.assertRaisesRegex(LinkFetchError, "too long"),
		):
			safe_fetch("https://example.com/page", allowed_content_types=("text/html",))
		self.assertEqual(send.call_count, 2)

	def test_redirect_hops_are_revalidated(self):
		redirect = FakeResponse(302, {"Location": "http://169.254.169.254/latest/"})
		resolve, send = fake_network(redirect)
		with resolve, send, self.assertRaises(BlockedURLError):
			safe_fetch("https://example.com/page", allowed_content_types=("text/html",))

	def test_redirect_cap(self):
		redirect = FakeResponse(302, {"Location": "https://example.com/next"})
		resolve, send = fake_network(redirect)
		with resolve, send, self.assertRaisesRegex(LinkFetchError, "redirects"):
			safe_fetch("https://example.com/page", allowed_content_types=("text/html",))

	def test_size_cap_on_streamed_body(self):
		resolve, send = fake_network(FakeResponse(200, HTML_HEADERS, b"x" * 5000))
		with resolve, send, self.assertRaisesRegex(LinkFetchError, "too large"):
			safe_fetch("https://example.com/big", allowed_content_types=("text/html",), max_bytes=1000)

	def test_size_cap_on_declared_length(self):
		headers = {"Content-Type": "text/html", "Content-Length": "9999999"}
		resolve, send = fake_network(FakeResponse(200, headers, b"tiny"))
		with resolve, send, self.assertRaisesRegex(LinkFetchError, "too large"):
			safe_fetch("https://example.com/big", allowed_content_types=("text/html",), max_bytes=1000)

	def test_content_type_allowlist(self):
		resolve, send = fake_network(FakeResponse(200, {"Content-Type": "image/png"}, b"png"))
		with resolve, send, self.assertRaisesRegex(LinkFetchError, "not allowed"):
			safe_fetch("https://example.com/img", allowed_content_types=("text/html",))

	def test_successful_fetch(self):
		response = FakeResponse(200, {"Content-Type": "text/html; charset=utf-8"}, b"<html>hi</html>")
		resolve, send = fake_network(response)
		with resolve, send:
			result = safe_fetch("https://example.com/page", allowed_content_types=("text/html",))
		self.assertEqual(result.content_type, "text/html")
		self.assertEqual(result.body, b"<html>hi</html>")


class OpenGraphTestCase(GameplanTestCase):
	def test_parse_open_graph(self):
		html = b"""
		<html><head>
		<title>Fallback Title</title>
		<meta property="og:title" content="OG Title"/>
		<meta property="og:image" content="/img.png"/>
		<meta name="description" content="A page"/>
		</head></html>
		"""
		data = parse_open_graph(html, "https://example.com/post")
		self.assertEqual(data["title"], "OG Title")
		self.assertEqual(data["description"], "A page")
		self.assertEqual(data["image"], "https://example.com/img.png")
		self.assertEqual(data["site_name"], "example.com")

	def test_title_falls_back_to_title_tag(self):
		data = parse_open_graph(b"<html><head><title>Plain</title></head></html>", "https://example.com/")
		self.assertEqual(data["title"], "Plain")

	def test_site_name_falls_back_to_host_without_www(self):
		data = parse_open_graph(b"<html><head><title>News</title></head></html>", "https://www.bbc.com/news")
		self.assertEqual(data["site_name"], "bbc.com")

	def test_soft_404_page_is_not_a_preview(self):
		html = b'<html><head><meta property="og:title" content="Page Not Found"/></head></html>'
		with self.assertRaises(LinkFetchError):
			parse_open_graph(html, "https://example.com/missing")

	def test_article_about_404_pages_still_previews(self):
		title = "Designing a friendly 404 page"
		html = f'<html><head><meta property="og:title" content="{title}"/></head></html>'
		self.assertEqual(parse_open_graph(html, "https://example.com/")["title"], title)

	def test_image_url_with_raw_spaces_is_percent_encoded(self):
		html = b'<html><head><meta name="image" content="https://example.com/files/a b.png"/></head></html>'
		self.assertEqual(
			parse_open_graph(html, "https://example.com/")["image"], "https://example.com/files/a%20b.png"
		)


class NormalizeUrlTestCase(GameplanTestCase):
	def test_drops_tracking_params_fragment_and_default_port(self):
		self.assertEqual(
			normalize_url("HTTPS://Example.COM:443/Post?utm_source=x&id=7&fbclid=y#intro"),
			"https://example.com/Post?id=7",
		)

	def test_keeps_hash_router_fragments(self):
		self.assertEqual(normalize_url("https://example.com/#/board/1"), "https://example.com/#/board/1")

	def test_drops_credentials(self):
		self.assertEqual(normalize_url("https://user:pass@example.com/x"), "https://example.com/x")

	def test_rejects_non_http_and_overlong_urls(self):
		for url in ("mailto:a@example.com", "javascript:alert(1)", "", "https://example.com/" + "a" * 500):
			self.assertIsNone(normalize_url(url), msg=url[:40])

	def test_detect_provider(self):
		self.assertEqual(detect_provider("https://youtu.be/abc"), "YouTube")
		self.assertEqual(detect_provider("https://en.wikipedia.org/wiki/Frappe"), "Wikipedia")
		self.assertEqual(detect_provider("https://notyoutube.com/x"), "Other")


class FillPreviewTestCase(GameplanTestCase):
	def new_preview(self, url="https://example.com/post"):
		return frappe.get_doc({"doctype": "GP Link Preview", "url": url, "provider": detect_provider(url)})

	def test_open_graph_preview_is_stored(self):
		page = fetched(b'<html><head><meta property="og:title" content="Hello"/></head></html>')
		preview = self.new_preview()
		with patch("gameplan.link_previews.safe_fetch", return_value=page):
			self.assertTrue(fill_preview(preview))
		saved = frappe.get_doc("GP Link Preview", {"url": "https://example.com/post"})
		self.assertEqual(saved.status, "Fetched")
		self.assertEqual(saved.title, "Hello")
		self.assertIsNotNone(saved.fetched_on)

	def test_oembed_is_used_for_known_providers(self):
		payload = {
			"title": "A video",
			"thumbnail_url": "https://i.ytimg.com/a.jpg",
			"provider_name": "YouTube",
		}
		response = fetched(json.dumps(payload).encode(), "application/json")
		preview = self.new_preview("https://www.youtube.com/watch?v=abc123")
		with patch("gameplan.link_previews.safe_fetch", return_value=response) as fetch:
			fill_preview(preview)
		self.assertTrue(fetch.call_args[0][0].startswith("https://www.youtube.com/oembed?"))
		self.assertEqual((preview.title, preview.image), ("A video", "https://i.ytimg.com/a.jpg"))

	def test_blocked_url_is_never_retried(self):
		preview = self.new_preview("http://127.0.0.1/admin")
		self.assertFalse(fill_preview(preview))
		self.assertEqual(preview.status, "Blocked")

	def test_failures_retry_until_the_cap(self):
		preview = self.new_preview()
		with patch("gameplan.link_previews.safe_fetch", side_effect=LinkFetchError("HTTP 500")):
			for _ in range(MAX_FETCH_ATTEMPTS - 1):
				fill_preview(preview)
				self.assertEqual(preview.status, "Pending")
			fill_preview(preview)
		self.assertEqual(preview.status, "Failed")
		self.assertEqual(preview.fetch_error, "HTTP 500")


OG_PAGE = fetched(b'<html><head><meta property="og:title" content="Hello"/></head></html>')


def stored_preview(url="https://example.com/post", **fields):
	values = {
		"status": "Fetched",
		"title": "Cached",
		"site_name": "example.com",
		"fetched_on": frappe.utils.now_datetime(),
		**fields,
	}
	return frappe.get_doc(
		{"doctype": "GP Link Preview", "url": url, "provider": detect_provider(url), **values}
	).insert(ignore_permissions=True)


class GetOrFetchPreviewTestCase(GameplanTestCase):
	def test_fresh_cached_row_is_served_without_fetching(self):
		stored_preview()
		with patch("gameplan.link_previews.safe_fetch") as fetch:
			result = get_or_fetch_preview("https://example.com/post")
		fetch.assert_not_called()
		self.assertEqual(
			result,
			{
				"url": "https://example.com/post",
				"title": "Cached",
				"description": None,
				"image": None,
				"site_name": "example.com",
				"provider": "Other",
			},
		)

	def test_new_url_is_fetched_once_then_served_from_cache(self):
		with patch("gameplan.link_previews.safe_fetch", return_value=OG_PAGE) as fetch:
			first = get_or_fetch_preview("https://example.com/post")
			second = get_or_fetch_preview("https://example.com/post")
		self.assertEqual(fetch.call_count, 1)
		self.assertEqual(first["title"], "Hello")
		self.assertEqual(first, second)
		self.assertEqual(frappe.db.count("GP Link Preview", {"url": "https://example.com/post"}), 1)

	def test_tracking_param_variant_hits_the_same_row(self):
		stored_preview()
		with patch("gameplan.link_previews.safe_fetch") as fetch:
			result = get_or_fetch_preview("https://Example.com/post?utm_source=x&fbclid=y")
		fetch.assert_not_called()
		self.assertEqual(result["url"], "https://example.com/post")
		self.assertEqual(frappe.db.count("GP Link Preview", {"url": ["like", "%example.com/post%"]}), 1)

	def test_blocked_and_failed_rows_return_none_without_fetching(self):
		stored_preview("https://example.com/blocked", status="Blocked", title="")
		stored_preview("https://example.com/failed", status="Failed", title="")
		with patch("gameplan.link_previews.safe_fetch") as fetch:
			self.assertIsNone(get_or_fetch_preview("https://example.com/blocked"))
			self.assertIsNone(get_or_fetch_preview("https://example.com/failed"))
		fetch.assert_not_called()

	def test_non_http_urls_return_none(self):
		with patch("gameplan.link_previews.safe_fetch") as fetch:
			for url in ("mailto:a@example.com", "javascript:alert(1)", ""):
				self.assertIsNone(get_or_fetch_preview(url), msg=url)
		fetch.assert_not_called()

	def test_own_site_urls_return_none_without_fetching(self):
		own_url = frappe.utils.get_url("/g/discussion/1")
		with patch("gameplan.link_previews.safe_fetch") as fetch:
			self.assertIsNone(get_or_fetch_preview(own_url))
		fetch.assert_not_called()
		self.assertFalse(frappe.db.exists("GP Link Preview", {"url": normalize_url(own_url)}))

	def test_stale_row_is_refetched(self):
		stored_preview(fetched_on=frappe.utils.add_days(frappe.utils.now_datetime(), -(STALE_AFTER_DAYS + 1)))
		with patch("gameplan.link_previews.safe_fetch", return_value=OG_PAGE) as fetch:
			result = get_or_fetch_preview("https://example.com/post")
		self.assertEqual(fetch.call_count, 1)
		self.assertEqual(result["title"], "Hello")

	def test_pending_row_is_retried(self):
		stored_preview(status="Pending", title="", fetch_attempts=1, fetched_on=None)
		with patch("gameplan.link_previews.safe_fetch", return_value=OG_PAGE) as fetch:
			result = get_or_fetch_preview("https://example.com/post")
		self.assertEqual(fetch.call_count, 1)
		self.assertEqual(result["title"], "Hello")

	def test_concurrent_insert_reuses_the_existing_row(self):
		existing = stored_preview()
		with (
			patch("gameplan.link_previews._find_preview", side_effect=[None, existing]),
			patch("gameplan.link_previews.safe_fetch") as fetch,
		):
			result = get_or_fetch_preview("https://example.com/post")
		fetch.assert_not_called()
		self.assertEqual(result["title"], "Cached")
		self.assertEqual(frappe.db.count("GP Link Preview", {"url": "https://example.com/post"}), 1)

	def test_page_without_a_title_is_not_a_preview(self):
		page = fetched(b'<html><head><meta name="description" content="No title"/></head></html>')
		with patch("gameplan.link_previews.safe_fetch", return_value=page):
			self.assertIsNone(get_or_fetch_preview("https://example.com/untitled"))


class LinkPreviewEndpointTestCase(GameplanTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(self.clear_quota)
		self.clear_quota()

	def clear_quota(self):
		for user in (self.member.name, self.second_member.name):
			frappe.cache.delete(frappe.cache.make_key(f"gameplan:link-preview-count:{user}"))

	def test_the_endpoint_is_post_only(self):
		self.assertEqual(declared_http_methods(get_link_preview), {"POST"})

	def test_guest_is_refused(self):
		with self.as_user("Guest"):
			with self.assertRaises(frappe.PermissionError):
				frappe.is_whitelisted(get_link_preview)
			with self.assertRaises(frappe.PermissionError):
				get_link_preview(url="https://example.com/post")

	def test_member_gets_a_preview(self):
		with self.as_user(self.member), patch("gameplan.link_previews.safe_fetch", return_value=OG_PAGE):
			result = get_link_preview(url="https://example.com/post")
		self.assertEqual(result["title"], "Hello")
		self.assertEqual(result["url"], "https://example.com/post")

	def test_rate_limit_is_per_user(self):
		stored_preview()
		with self.as_user(self.member):
			for _index in range(LINK_PREVIEW_QUOTA):
				get_link_preview(url="https://example.com/post")
			with self.assertRaises(frappe.RateLimitExceededError):
				get_link_preview(url="https://example.com/post")
		with self.as_user(self.second_member):
			self.assertEqual(get_link_preview(url="https://example.com/post")["title"], "Cached")


class LinkCardContentTestCase(GameplanTestCase):
	def test_link_card_survives_sanitizing(self):
		community = create_community("Card Community", members=[self.member])
		discussion = create_discussion("Cards", create_space("Card Space", community), owner=self.member)
		card = (
			'<div data-type="link-card" data-description="About it" '
			'data-image="https://example.com/a.png" data-site-name="Example">'
			'<a href="https://example.com/post">A post</a></div>'
		)
		comment = create_comment(discussion, content=card)
		saved = frappe.db.get_value("GP Comment", comment.name, "content")
		for fragment in (
			'data-type="link-card"',
			'data-description="About it"',
			'data-image="https://example.com/a.png"',
			'data-site-name="Example"',
			'href="https://example.com/post"',
		):
			self.assertIn(fragment, saved)
