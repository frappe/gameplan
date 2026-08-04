# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Server-side proxy for the Unsplash image API.

The access key is a site secret: it is rate-limited per application, and anyone
holding it can spend our quota. So the browser never sees it — it asks this
module, and this module talks to Unsplash.

Two consequences shape everything below:

- Guests are refused. This is our key in front of a third-party API, not a
  public service, so `Guest` gets a PermissionError rather than a search.
- A missing key is a *configuration* answer, not a crash. `search_photos`
  returns `configured: False` so the picker can say what to set, instead of the
  UI showing a stack trace on a site that simply never enabled this.

Only the fields the picker needs are returned. Unsplash's photo payload is large
and changes over time; passing it through would make the frontend depend on a
shape we do not control.
"""

import frappe
import requests
from frappe.utils import cint

BASE_URL = "https://api.unsplash.com"
CONFIG_KEY = "unsplash_access_key"

# Unsplash requires every link back to a photo or photographer to carry the
# application's UTM parameters. See https://help.unsplash.com/en/articles/2511315.
ATTRIBUTION_UTM = "utm_source=gameplan&utm_medium=referral"
UNSPLASH_URL = f"https://unsplash.com/?{ATTRIBUTION_UTM}"

REQUEST_TIMEOUT = 10
MAX_PER_PAGE = 30

# Browsable topics, so the picker opens on something to look at instead of an
# empty box. `featured` is not one of Unsplash's topics: it is their editorial
# feed, which has its own endpoint. The rest are real topic slugs.
#
# A whitelist rather than a passthrough, because the slug goes into the request
# path — an arbitrary one would let a caller aim `_request` anywhere under
# api.unsplash.com. `unsplashTopics` in the picker mirrors this list.
FEATURED_TOPIC = "featured"
TOPIC_SLUGS = frozenset(
	{
		FEATURED_TOPIC,
		"wallpapers",
		"nature",
		"textures-patterns",
		"architecture-interior",
		"travel",
		"3d-renders",
	}
)

# A demo Unsplash key allows 50 requests an hour, and a debounced search box can
# spend that in a couple of minutes. Repeat queries — the same word typed again,
# a second user searching "desk" — are served from cache instead.
CACHE_PREFIX = "gameplan:unsplash:search"
CACHE_TTL = 60 * 60

NOT_CONFIGURED_MESSAGE = (
	f"Unsplash is not set up on this site. Add an Unsplash access key as "
	f'"{CONFIG_KEY}" in site_config.json to search for images.'
)


def get_access_key() -> str | None:
	"""The configured access key, or None when the site has not set one.

	`site_config.json` is hand-edited, so the key can arrive as an empty string,
	as JSON `false`, or as the *string* "0" — all of which mean "not set up" and
	only the first of which plain Python truth agrees about.
	"""
	key = frappe.conf.get(CONFIG_KEY)
	if not isinstance(key, str):
		return None

	key = key.strip()
	if not key or key.lower() in ("0", "false", "none", "null"):
		return None

	return key


def assert_can_search():
	"""Every endpoint here spends our Unsplash quota, so no anonymous access."""
	if frappe.session.user == "Guest":
		frappe.throw("You are not permitted to search Unsplash", frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def search_photos(query: str | None = None, topic: str | None = None, page: int = 1, per_page: int = 24):
	"""Photos to show in the picker, trimmed to what it renders.

	Two ways in, and a query wins when both arrive: `query` searches all of
	Unsplash, `topic` browses one of `TOPIC_SLUGS` so the picker has something to
	show before anything is typed. With neither, this answers nothing but
	`configured` — that costs no quota, and it is the only way the browser can ask
	whether a key is set at all.

	Returns `{configured, photos, total, query, topic}`.
	"""
	assert_can_search()

	access_key = get_access_key()
	if not access_key:
		return {"configured": False, "message": NOT_CONFIGURED_MESSAGE, "photos": [], "total": 0}

	query = (query or "").strip()
	topic = (topic or "").strip().lower()
	page = max(1, cint(page) or 1)
	per_page = min(MAX_PER_PAGE, max(1, cint(per_page) or 24))

	if not query and topic and topic not in TOPIC_SLUGS:
		frappe.throw(f"Unknown Unsplash topic: {topic}", frappe.ValidationError)

	if not query and not topic:
		return {"configured": True, "photos": [], "total": 0, "query": "", "topic": ""}

	cache_key = f"{CACHE_PREFIX}:{query.lower()}:{topic}:{page}:{per_page}"
	cached = frappe.cache.get_value(cache_key)
	if cached is not None:
		return cached

	if query:
		payload = _request(
			"/search/photos",
			access_key,
			params={"query": query, "page": page, "per_page": per_page},
		)
	elif topic == FEATURED_TOPIC:
		payload = _request("/photos", access_key, params={"page": page, "per_page": per_page})
	else:
		payload = _request(f"/topics/{topic}/photos", access_key, params={"page": page, "per_page": per_page})

	# `/search/photos` answers with an envelope; the browse endpoints answer with a
	# bare list, and Unsplash gives no total for those.
	photos = payload.get("results") if isinstance(payload, dict) else payload
	total = cint(payload.get("total")) if isinstance(payload, dict) else len(photos or [])

	result = {
		"configured": True,
		"query": query,
		"topic": "" if query else topic,
		"total": total,
		"photos": [_serialize_photo(photo) for photo in (photos or [])],
	}
	frappe.cache.set_value(cache_key, result, expires_in_sec=CACHE_TTL)
	return result


@frappe.whitelist(methods=["POST"])
def track_download(download_location: str | None = None):
	"""Tell Unsplash a photo was actually used.

	Required by the API guidelines: hotlinking an image is not a download, so the
	count only moves when the app pings the photo's own `download_location`. That
	URL comes back from `search_photos`, so it is checked against Unsplash's host
	rather than trusted — this endpoint must not become a way to make the server
	fetch arbitrary URLs with our key attached.

	POST because it is an outbound side effect, even though it writes nothing of
	ours; nothing useful is returned beyond whether the ping was sent.
	"""
	assert_can_search()

	access_key = get_access_key()
	if not access_key:
		return {"configured": False, "tracked": False}

	if not _is_unsplash_api_url(download_location):
		frappe.throw("Not an Unsplash download link", frappe.ValidationError)

	_request(download_location, access_key)
	return {"configured": True, "tracked": True}


def _is_unsplash_api_url(url: str | None) -> bool:
	from urllib.parse import urlparse

	if not url or not isinstance(url, str):
		return False

	parsed = urlparse(url)
	return parsed.scheme == "https" and parsed.netloc == "api.unsplash.com"


def _serialize_photo(photo: dict) -> dict:
	"""One Unsplash photo, reduced to the fields the picker needs.

	`urls.regular` is what gets stored on the profile: `raw` has no sizing applied
	and `full` is multi-megabyte, while `regular` is a ~1080px render that the
	cover card can still narrow further with Unsplash's own query parameters.

	The pixel dimensions are along so the picker can reserve each tile's shape
	before its image arrives. Without them a wall of lazily loaded photos starts
	as a row of zero-height boxes and reflows on every load.
	"""
	urls = photo.get("urls") or {}
	user = photo.get("user") or {}
	user_links = user.get("links") or {}
	links = photo.get("links") or {}

	return {
		"id": photo.get("id"),
		"width": cint(photo.get("width")),
		"height": cint(photo.get("height")),
		# `small` (~400px), not `thumb` (~200px): the picker's columns are wider
		# than a thumb on any desktop dialog, and a stretched thumb looks soft.
		"thumb_url": urls.get("small") or urls.get("thumb"),
		"url": urls.get("regular") or urls.get("full") or urls.get("raw"),
		"alt": (photo.get("alt_description") or photo.get("description") or "").strip(),
		"photographer_name": user.get("name") or user.get("username") or "Unsplash",
		"photographer_url": _with_utm(user_links.get("html")),
		"photo_url": _with_utm(links.get("html")),
		"download_location": links.get("download_location"),
	}


def _with_utm(url: str | None) -> str:
	"""An attribution link with the UTM parameters Unsplash requires on it."""
	if not url:
		return UNSPLASH_URL

	separator = "&" if "?" in url else "?"
	return f"{url}{separator}{ATTRIBUTION_UTM}"


def _request(path: str, access_key: str, params: dict | None = None):
	"""One call to Unsplash, with every failure turned into a readable message.

	Callers get either a parsed body or a `frappe.throw` a person can act on —
	never a bare requests exception, because these surface directly in the
	picker's error state.
	"""
	url = path if path.startswith("https://") else f"{BASE_URL}{path}"

	try:
		response = requests.get(
			url,
			params=params,
			headers={
				"Accept-Version": "v1",
				"Authorization": f"Client-ID {access_key}",
			},
			timeout=REQUEST_TIMEOUT,
		)
	except requests.Timeout:
		frappe.throw("Unsplash took too long to respond. Try again.")
	except requests.RequestException:
		frappe.throw("Could not reach Unsplash. Check the server's internet connection.")

	if response.status_code == 401:
		frappe.throw(f'The Unsplash access key in site_config.json ("{CONFIG_KEY}") was rejected.')

	# Unsplash reports an exhausted quota as 403 with the remaining count at zero,
	# which is worth telling apart from a genuinely forbidden request.
	if response.status_code == 403 and response.headers.get("X-Ratelimit-Remaining") == "0":
		frappe.throw("Unsplash's hourly rate limit is used up. Try again later.")

	if response.status_code >= 400:
		frappe.throw(f"Unsplash returned an error ({response.status_code}).")

	try:
		return response.json() or {}
	except ValueError:
		frappe.throw("Unsplash returned a response that could not be read.")


# --- Legacy helpers -------------------------------------------------------
# `gameplan.api.get_unsplash_photos` (and the old `UnsplashImageBrowser.vue`
# behind it) still import these. They predate the endpoints above and should go
# when that api.py endpoint does; nothing new should call them.


def get_by_keyword(keyword):
	access_key = get_access_key()
	if not access_key:
		frappe.throw(NOT_CONFIGURED_MESSAGE)

	return _request("/search/photos", access_key, params={"query": keyword}).get("results")


def get_list():
	access_key = get_access_key()
	if not access_key:
		frappe.throw(NOT_CONFIGURED_MESSAGE)

	return _request("/photos", access_key)
