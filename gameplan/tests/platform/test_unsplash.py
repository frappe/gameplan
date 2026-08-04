# Copyright (c) 2026, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

"""The Unsplash proxy's contract with the picker that calls it.

Nothing here touches the network: every test stubs `requests.get`, because a
suite that reaches api.unsplash.com fails on an offline CI box, spends a real
rate limit, and needs a real key to be meaningful.

What is worth pinning down is the shape of each answer — a guest is refused, an
unconfigured site says so instead of raising, a search returns only our trimmed
fields, and an upstream failure arrives as a sentence rather than a traceback.
"""

from unittest.mock import MagicMock, patch

import frappe
import requests

from gameplan.tests.base import GameplanTestCase
from gameplan.unsplash import (
	CACHE_PREFIX,
	CONFIG_KEY,
	NOT_CONFIGURED_MESSAGE,
	search_photos,
	track_download,
)

DOWNLOAD_LOCATION = "https://api.unsplash.com/photos/abc123/download?ixid=xyz"

# One result, as Unsplash actually returns it: far more fields than the picker
# uses, which is the point — the proxy must hand back only the trimmed subset.
PHOTO_PAYLOAD = {
	"id": "abc123",
	"created_at": "2026-01-01T00:00:00Z",
	"width": 4000,
	"height": 3000,
	"color": "#262626",
	"blur_hash": "LKO2?U%2Tw=w]~RBVZRi};RPxuwH",
	"alt_description": "  a desk by a window  ",
	"description": None,
	"urls": {
		"raw": "https://images.unsplash.com/photo-abc123",
		"full": "https://images.unsplash.com/photo-abc123?q=85",
		"regular": "https://images.unsplash.com/photo-abc123?w=1080",
		"small": "https://images.unsplash.com/photo-abc123?w=400",
		"thumb": "https://images.unsplash.com/photo-abc123?w=200",
	},
	"links": {
		"self": "https://api.unsplash.com/photos/abc123",
		"html": "https://unsplash.com/photos/abc123",
		"download": "https://unsplash.com/photos/abc123/download",
		"download_location": DOWNLOAD_LOCATION,
	},
	"user": {
		"id": "u1",
		"username": "aphotographer",
		"name": "A Photographer",
		"links": {"html": "https://unsplash.com/@aphotographer"},
	},
}

SEARCH_PAYLOAD = {"total": 137, "total_pages": 14, "results": [PHOTO_PAYLOAD]}


def make_response(status_code=200, json_body=None, headers=None):
	response = MagicMock()
	response.status_code = status_code
	response.headers = headers or {}
	response.json.return_value = json_body if json_body is not None else {}
	return response


class TestUnsplashProxy(GameplanTestCase):
	def setUp(self):
		super().setUp()
		# The proxy caches a search for an hour, so without this a query would be
		# answered from a *previous* test's stub and the assertions below would
		# pass without the stub under test ever being called.
		frappe.cache.delete_keys(CACHE_PREFIX)
		self.addCleanup(frappe.cache.delete_keys, CACHE_PREFIX)
		frappe.set_user(self.member.name)

	def configured(self, key="test-access-key"):
		"""Put an access key in the site config for one test."""
		patcher = patch.dict(frappe.conf, {CONFIG_KEY: key})
		self.addCleanup(patcher.stop)
		patcher.start()

	def stub_request(self, *responses):
		"""Replace the outbound HTTP call. Returns the mock, for call assertions."""
		patcher = patch("gameplan.unsplash.requests.get", side_effect=list(responses))
		self.addCleanup(patcher.stop)
		return patcher.start()

	def test_refuses_a_guest(self):
		"""The key is ours, so an anonymous visitor may not spend it."""
		get = self.stub_request()
		self.configured()

		with self.as_user("Guest"), self.assertRaises(frappe.PermissionError):
			search_photos(query="desk")

		get.assert_not_called()

	def test_refuses_a_guest_for_download_tracking(self):
		get = self.stub_request()
		self.configured()

		with self.as_user("Guest"), self.assertRaises(frappe.PermissionError):
			track_download(download_location=DOWNLOAD_LOCATION)

		get.assert_not_called()

	def test_reports_a_missing_key_instead_of_raising(self):
		"""A site that never set this up should see an explanation, not a traceback."""
		get = self.stub_request()

		with patch.dict(frappe.conf):
			frappe.conf.pop(CONFIG_KEY, None)
			result = search_photos(query="desk")

		self.assertFalse(result["configured"])
		self.assertEqual(result["photos"], [])
		self.assertEqual(result["message"], NOT_CONFIGURED_MESSAGE)
		self.assertIn(CONFIG_KEY, result["message"])
		get.assert_not_called()

	def test_reads_a_hand_edited_key_as_unconfigured(self):
		""" "0" and "false" are strings out of `site_config.json`, and both are
		truthy in plain Python — a key that is not a key must not be sent."""
		for value in ("", "   ", "0", "false", 0, False, None):
			with self.subTest(value=value):
				get = self.stub_request()
				self.configured(value)

				result = search_photos(query="desk")

				self.assertFalse(result["configured"])
				get.assert_not_called()

	def test_maps_a_search_result_to_the_trimmed_shape(self):
		self.configured()
		get = self.stub_request(make_response(json_body=SEARCH_PAYLOAD))

		result = search_photos(query="desk", per_page=5)

		self.assertTrue(result["configured"])
		self.assertEqual(result["total"], 137)
		self.assertEqual(
			result["photos"],
			[
				{
					"id": "abc123",
					"width": 4000,
					"height": 3000,
					"thumb_url": "https://images.unsplash.com/photo-abc123?w=400",
					"url": "https://images.unsplash.com/photo-abc123?w=1080",
					"alt": "a desk by a window",
					"photographer_name": "A Photographer",
					"photographer_url": (
						"https://unsplash.com/@aphotographer?utm_source=gameplan&utm_medium=referral"
					),
					"photo_url": (
						"https://unsplash.com/photos/abc123?utm_source=gameplan&utm_medium=referral"
					),
					"download_location": DOWNLOAD_LOCATION,
				}
			],
		)

		# The key travels in the header, never in a query parameter that could end
		# up in a proxy log or a browser-visible URL.
		_, kwargs = get.call_args
		self.assertEqual(kwargs["headers"]["Authorization"], "Client-ID test-access-key")
		self.assertEqual(kwargs["params"], {"query": "desk", "page": 1, "per_page": 5})

	def test_does_not_call_unsplash_with_neither_a_query_nor_a_topic(self):
		"""Only answers `configured`, which is the one thing that costs nothing."""
		self.configured()
		get = self.stub_request()

		result = search_photos(query="   ")

		self.assertEqual(result, {"configured": True, "photos": [], "total": 0, "query": "", "topic": ""})
		get.assert_not_called()

	def test_browses_the_editorial_feed_for_the_featured_topic(self):
		"""`featured` is not a topic of Unsplash's, so it has its own endpoint."""
		self.configured()
		get = self.stub_request(make_response(json_body=[PHOTO_PAYLOAD]))

		result = search_photos(topic="featured", per_page=5)

		self.assertEqual(result["topic"], "featured")
		self.assertEqual(result["query"], "")
		# A browse answers with a bare list, so the count comes from its length.
		self.assertEqual(result["total"], 1)
		self.assertEqual(result["photos"][0]["id"], "abc123")

		args, kwargs = get.call_args
		self.assertEqual(args[0], "https://api.unsplash.com/photos")
		self.assertEqual(kwargs["params"], {"page": 1, "per_page": 5})

	def test_browses_a_named_topic(self):
		self.configured()
		get = self.stub_request(make_response(json_body=[PHOTO_PAYLOAD]))

		result = search_photos(topic="Nature")

		self.assertEqual(result["topic"], "nature")
		self.assertEqual(get.call_args[0][0], "https://api.unsplash.com/topics/nature/photos")

	def test_refuses_a_topic_it_does_not_know(self):
		"""The slug lands in the request path, so an arbitrary one is not passed on."""
		self.configured()
		get = self.stub_request()

		with self.assertRaises(frappe.ValidationError):
			search_photos(topic="../../users/someone")

		get.assert_not_called()

	def test_prefers_the_query_when_a_topic_comes_with_it(self):
		"""Typing is the more specific intent, and the chips clear on it anyway."""
		self.configured()
		get = self.stub_request(make_response(json_body=SEARCH_PAYLOAD))

		result = search_photos(query="desk", topic="nature")

		self.assertEqual(result["query"], "desk")
		self.assertEqual(result["topic"], "")
		self.assertEqual(get.call_args[0][0], "https://api.unsplash.com/search/photos")

	def test_serves_a_repeated_query_from_cache(self):
		"""A demo key allows 50 requests an hour; a debounced search box would eat it."""
		self.configured()
		get = self.stub_request(make_response(json_body=SEARCH_PAYLOAD))

		first = search_photos(query="Desk")
		second = search_photos(query="desk")

		self.assertEqual(first, second)
		get.assert_called_once()

	def test_caches_a_topic_apart_from_a_query(self):
		"""Both go through one cache key, so the two must not collide."""
		self.configured()
		get = self.stub_request(
			make_response(json_body=SEARCH_PAYLOAD), make_response(json_body=[PHOTO_PAYLOAD])
		)

		searched = search_photos(query="desk")
		browsed = search_photos(topic="nature")

		self.assertEqual(searched["total"], 137)
		self.assertEqual(browsed["total"], 1)
		self.assertEqual(get.call_count, 2)

	def test_surfaces_an_upstream_failure_as_a_readable_message(self):
		self.configured()
		self.stub_request(make_response(status_code=500))

		with self.assertRaises(frappe.ValidationError) as caught:
			search_photos(query="desk")

		self.assertIn("500", str(caught.exception))
		self.assertIn("Unsplash", str(caught.exception))

	def test_names_a_rejected_key(self):
		self.configured("wrong-key")
		self.stub_request(make_response(status_code=401))

		with self.assertRaises(frappe.ValidationError) as caught:
			search_photos(query="desk")

		self.assertIn(CONFIG_KEY, str(caught.exception))

	def test_names_an_exhausted_rate_limit(self):
		"""Unsplash reports a spent quota as a 403, which reads as "forbidden"
		unless the remaining-count header is looked at."""
		self.configured()
		self.stub_request(make_response(status_code=403, headers={"X-Ratelimit-Remaining": "0"}))

		with self.assertRaises(frappe.ValidationError) as caught:
			search_photos(query="desk")

		self.assertIn("rate limit", str(caught.exception))

	def test_surfaces_a_timeout(self):
		self.configured()
		self.stub_request(requests.Timeout())

		with self.assertRaises(frappe.ValidationError) as caught:
			search_photos(query="desk")

		self.assertIn("too long", str(caught.exception))

	def test_tracks_a_download(self):
		self.configured()
		get = self.stub_request(make_response(json_body={"url": "https://example.com/x"}))

		result = track_download(download_location=DOWNLOAD_LOCATION)

		self.assertEqual(result, {"configured": True, "tracked": True})
		self.assertEqual(get.call_args.args[0], DOWNLOAD_LOCATION)

	def test_refuses_to_fetch_a_url_that_is_not_unsplash(self):
		"""Otherwise this endpoint is a way to make the server call any URL with
		our access key in the header."""
		self.configured()
		get = self.stub_request()

		for url in ("https://evil.example.com/steal", "http://api.unsplash.com/x", "", None):
			with self.subTest(url=url):
				with self.assertRaises(frappe.ValidationError):
					track_download(download_location=url)

		get.assert_not_called()


class TestUnsplashCoverImage(GameplanTestCase):
	"""Whether the profile can hold an Unsplash URL at all.

	The picker hotlinks: it writes `https://images.unsplash.com/...` straight into
	`cover_image` instead of downloading the photo into a Frappe File. That only
	works because `cover_image` is an `Attach Image`, which is a plain text column
	with no local-path rule — and the whole approach collapses quietly if that
	ever stops being true, so it is asserted rather than assumed.
	"""

	def test_the_owner_can_store_a_remote_cover_url(self):
		url = "https://images.unsplash.com/photo-abc123?w=1080"

		with self.as_user(self.member.name):
			profile = frappe.get_doc("GP User Profile", {"user": self.member.name})
			profile.cover_image = url
			profile.save()

		profile.reload()
		self.assertEqual(profile.cover_image, url)
