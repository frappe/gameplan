# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
"""Discourse ``posts.cooked`` HTML -> Gameplan editor HTML.

Two gates decide what survives an import, so every rule here is written against
both of them:

1. ``gameplan.utils.sanitizer.sanitize_content`` (bleach). Output of this module
   is designed to pass through it byte-identical.
2. The TipTap/ProseMirror schema used by ``GPEditor.vue`` (frappe-ui
   ``CommentKit`` / ``RichTextKit``). Anything the schema cannot parse is simply
   not rendered, so Discourse chrome is removed here rather than left in the DB.

File resolution and user resolution are NOT done here. The importer supplies a
:class:`TransformContext`; this module only asks it questions.

Rule numbers in comments refer to
``.scratch/discuss-migration/research/04-cooked-html-transforms.md``.
"""

from __future__ import annotations

import importlib.util
import os
import re
from html import escape
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.dammit import EntitySubstitution
from bs4.formatter import HTMLFormatter

__all__ = [
	"TransformContext",
	"transform_cooked",
	"strip_poll_markup",
	"accepted_answer_badge",
	"synthesized_quote",
	"rewrite_internal_links",
]


class TransformContext(Protocol):
	"""What the importer must provide. Implemented by the importer, never here."""

	def resolve_image(self, src: str | None, orig_src: str | None, base62_sha1: str | None) -> str | None:
		"""Return a Gameplan file URL (``/files/x.png``), or ``None`` to strip the element.

		Called for every non-emoji ``<img>`` and for every upload-bearing anchor,
		including images hosted outside Discourse. ``src`` is ``None`` when the
		cooked HTML carries no usable src (lazy placeholder, dead ``/404`` link),
		in which case ``orig_src`` holds the ``upload://<base62>.<ext>`` short URL.
		Return the input unchanged to keep a remote image as-is.
		"""

	def resolve_mention(self, username: str) -> str | None:
		"""Return the Gameplan user id (email) for a Discourse username, else ``None``."""


DISCOURSE_HOSTS = ("discuss.frappe.io", "discuss.erpnext.com")
DISCOURSE_CANONICAL_HOST = "discuss.frappe.io"

# Mirrors gameplan.utils.sanitizer.ALLOWED_IFRAME_DOMAINS. Duplicated so this
# module imports without frappe; keep the two lists in step.
ALLOWED_IFRAME_DOMAINS = (
	"youtube.com",
	"www.youtube.com",
	"youtu.be",
	"vimeo.com",
	"player.vimeo.com",
	"codepen.io",
	"codesandbox.io",
	"figma.com",
	"www.figma.com",
	"embed.figma.com",
	"docs.google.com",
	"drive.google.com",
	"notion.so",
	"www.notion.so",
)

# Rule 11. Discourse writes `lang-<info string>`; only these become
# `language-<x>` for CodeBlockLowlight. Everything else loses the class.
# Built from the info strings actually present in the corpus.
KNOWN_CODE_LANGUAGES = {
	"ansible": "ansible",
	"bash": "bash",
	"batch": "batch",
	"c": "c",
	"console": "shell",
	"cpp": "cpp",
	"csharp": "csharp",
	"css": "css",
	"csv": "csv",
	"diff": "diff",
	"dockerfile": "dockerfile",
	"go": "go",
	"html": "html",
	"ini": "ini",
	"java": "java",
	"javascript": "javascript",
	"jinja": "jinja",
	"js": "javascript",
	"json": "json",
	"log": "log",
	"lua": "lua",
	"markdown": "markdown",
	"md": "markdown",
	"mermaid": "mermaid",
	"nginx": "nginx",
	"perl": "perl",
	"php": "php",
	"plaintext": "plaintext",
	"py": "python",
	"python": "python",
	"ruby": "ruby",
	"rust": "rust",
	"scss": "scss",
	"sh": "bash",
	"shell": "bash",
	"sql": "sql",
	"text": "plaintext",
	"toml": "toml",
	"ts": "typescript",
	"txt": "plaintext",
	"typescript": "typescript",
	"vue": "vue",
	"xml": "xml",
	"yaml": "yaml",
	"yml": "yaml",
}

# Final scrub. Any attribute not listed for a tag is dropped, which is what
# keeps the output stable under bleach (it strips `srcset`, `loading`, `rel`,
# and rewrites `style`). Tags absent from this map keep no attributes at all.
ALLOWED_ATTRS: dict[str, set[str]] = {
	"a": {"href", "title", "target"},
	"blockquote": {"data-rich-quote-id", "data-author"},
	"code": {"class"},
	"iframe": {"src", "width", "height", "frameborder", "allowfullscreen", "title"},
	"img": {"src", "alt", "title", "width", "height"},
	"ol": {"start", "type"},
	"p": {"data-discourse-poll"},
	"span": {"class", "data-type", "data-id", "data-label"},
	"td": {"colspan", "rowspan", "colwidth"},
	"th": {"colspan", "rowspan", "colwidth"},
	"ul": {"data-discourse-poll"},
	# No `controls`: the Video node renders its own player, and html5lib
	# minimises boolean attributes, which would make output unstable under bleach.
	"video": {"src", "width", "height", "poster"},
}

# Tags kept in the output. Anything else is unwrapped: bleach escapes tags it
# does not know (`<wbr>` becomes `&lt;wbr&gt;`), and TipTap ignores them anyway.
ALLOWED_TAGS = {
	"a", "abbr", "b", "blockquote", "br", "caption", "cite", "code", "col", "colgroup",
	"dd", "del", "dl", "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5",
	"h6", "hr", "i", "iframe", "img", "ins", "kbd", "li", "mark", "ol", "p", "pre", "q",
	"s", "samp", "small", "span", "strong", "sub", "sup", "table", "tbody", "td",
	"tfoot", "th", "thead", "tr", "u", "ul", "var", "video",
}

# Discourse chrome that carries no content once its wrapper is rewritten.
CHROME_SELECTORS = (
	"div.meta",
	"div.quote-controls",
	"div.onebox-metadata",
	"div.aspect-image",
	"span.badge-category",
	"a.badge-category__wrapper",
	"span.hashtag-icon-placeholder",
	"img.site-icon",
	"img.thumbnail",
	"img.avatar",
	"div.poll-info",
	"div.poll-buttons",
)

_BLOCK_TAGS = [
	"address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset",
	"figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
	"li", "ol", "p", "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead",
	"tr", "ul", "video",
]

_UPLOAD_SHORT_URL = "upload://"
_TRANSPARENT_RE = re.compile(r"/images/transparent\.(png|gif)", re.I)
_IMAGE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|webp|bmp|svg|avif|heic)(\?|$)", re.I)
_SIZE_SUFFIX_RE = re.compile(r"\|\d+x\d+\s*$")
_AVATAR_RE = re.compile(r"/(letter_avatar_proxy|user_avatar)/", re.I)
_USER_AVATAR_NAME_RE = re.compile(r"/user_avatar/[^/]+/([^/]+)/")
_TOPIC_PATH_RE = re.compile(r"^/t/(?:[^/]+/)?(\d+)(?:/\d+)?/?$")
_USER_PATH_RE = re.compile(r"^/u/([^/]+)(?:/.*)?$")
_CATEGORY_PATH_RE = re.compile(r"^/c/(.+?)/?$")

# Hrefs that already point at Gameplan (resolved files, app routes). The second
# pass must never absolutize these onto discuss.frappe.io.
_LOCAL_HREF_PREFIXES = ("/files/", "/private/", "/api/", "/g/", "/app/", "/assets/")

# Anchors the second pass must not touch: chrome, not prose.
_CHROME_ANCHOR_CLASSES = frozenset(
	{"mention", "mention-group", "hashtag", "hashtag-cooked", "anchor", "badge-category__wrapper"}
)

_POLL_MARKER = "data-discourse-poll"

# Serialization that bleach reproduces byte for byte: bare `&` escaped, void
# elements without the XML slash, empty attributes kept as `attr=""`.
_FORMATTER = HTMLFormatter(
	entity_substitution=EntitySubstitution.substitute_xml,
	void_element_close_prefix="",
	empty_attributes_are_booleans=False,
)

_emoji_cache: dict[str, str] | None = None


def _emoji_map() -> dict[str, str]:
	"""Shortcode -> unicode, from the importer's ``emojis.py``.

	Loaded from the file directly so importing this module never executes the
	package ``__init__`` (which pulls in frappe and the importer itself).
	"""
	global _emoji_cache
	if _emoji_cache is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emojis.py")
		spec = importlib.util.spec_from_file_location("_discourse_emojis", path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		_emoji_cache = {
			row["name"]: "".join(chr(int(part, 16)) for part in row["code"].split("-"))
			for row in module.emojis
		}
	return _emoji_cache


# ---------------------------------------------------------------------------
# small tree helpers
# ---------------------------------------------------------------------------


def _classes(tag: Tag) -> list[str]:
	value = tag.get("class") or []
	return value if isinstance(value, list) else str(value).split()


def _has_class(tag: Tag, name: str) -> bool:
	return name in _classes(tag)


def _text(node: Tag | NavigableString) -> str:
	if isinstance(node, NavigableString):
		return str(node)
	return node.get_text(" ", strip=True)


def _replace_with_text(tag: Tag, text: str) -> None:
	tag.replace_with(NavigableString(text))


def _is_blank(tag: Tag) -> bool:
	"""True when a paragraph-ish tag has neither text nor a meaningful child."""
	if tag.find(["img", "br", "iframe", "video", "table", "hr", "span"]):
		return False
	return not tag.get_text(strip=True)


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------


def _strip_svg(soup: BeautifulSoup) -> None:
	"""Rule 21. Every inline svg in the corpus is a Discourse UI icon."""
	for svg in soup.find_all("svg"):
		svg.decompose()


def _unwrap_lightboxes(soup: BeautifulSoup) -> None:
	"""Rule 5. Keep the inner img; drop the zoom anchor and the meta strip."""
	for anchor in soup.select("a.lightbox"):
		for chrome in anchor.select("div.meta, span.filename, span.informations"):
			chrome.decompose()
		anchor.unwrap()
	for wrapper in soup.select("div.lightbox-wrapper"):
		wrapper.unwrap()


def _quote_header(soup: BeautifulSoup, aside: Tag, username: str | None) -> Tag | None:
	"""Attribution line for a quote aside.

	31% of quote asides (about 10k) quote a topic rather than a person and carry
	no ``data-username``. Those fall back to the topic link from ``div.title``,
	which the second pass can then point at the imported discussion.
	"""
	head = soup.new_tag("p")
	strong = soup.new_tag("strong")
	head.append(strong)

	if username:
		strong.string = f"@{username}:"
		return head

	for anchor in aside.select("div.title a[href]"):
		if _has_class(anchor, "badge-category__wrapper"):
			continue
		label = _text(anchor)
		if not label:
			continue
		link = soup.new_tag("a", href=anchor["href"])
		link.string = label
		strong.append(NavigableString("Quoted from "))
		strong.append(link)
		strong.append(NavigableString(":"))
		return head

	return None


def _rewrite_quotes(soup: BeautifulSoup) -> None:
	"""Rule 6. ``aside.quote`` -> a plain blockquote headed by the author."""
	for aside in soup.select("aside.quote"):
		username = aside.get("data-username")
		if not username:
			avatar = aside.find("img", class_="avatar")
			if avatar:
				match = _USER_AVATAR_NAME_RE.search(avatar.get("src") or "")
				if match:
					username = match.group(1)

		quote = soup.new_tag("blockquote")
		head = _quote_header(soup, aside, username)
		if head:
			quote.append(head)

		inner = aside.find("blockquote")
		if inner:
			for child in list(inner.contents):
				quote.append(child.extract())
		else:  # malformed aside: keep whatever prose it held
			for title in aside.select("div.title"):
				title.decompose()
			for child in list(aside.contents):
				quote.append(child.extract())

		aside.replace_with(quote)


def _rewrite_oneboxes(soup: BeautifulSoup) -> None:
	"""Rule 7. Full onebox -> ``<p><a href=URL>title</a></p>``."""
	for box in soup.find_all(["aside", "div"], class_="onebox"):
		if box.find("video"):  # video-onebox: rule 18 owns it, just drop the wrapper
			box.unwrap()
			continue

		url = box.get("data-onebox-src")
		title_anchor = box.select_one("h3 a[href], h4 a[href]")
		header_anchor = box.select_one("header.source a[href]")
		if not url:
			source = title_anchor or header_anchor
			url = source.get("href") if source else None
		if not url:
			box.decompose()
			continue

		label = _text(title_anchor) if title_anchor else ""
		if not label:
			label = _text(header_anchor) if header_anchor else ""
		if not label:
			label = url

		para = soup.new_tag("p")
		link = soup.new_tag("a", href=url)
		link.string = label
		para.append(link)
		box.replace_with(para)


def _plain_onebox_links(soup: BeautifulSoup) -> None:
	"""Rule 8. Inline and bare oneboxes stay links; only the styling class goes."""
	for anchor in soup.find_all("a", class_=True):
		classes = _classes(anchor)
		if any(c in ("onebox", "inline-onebox", "inline-onebox-loading") for c in classes):
			del anchor["class"]


def _rewrite_mentions(soup: BeautifulSoup, ctx: TransformContext) -> None:
	"""Rule 9. ``a.mention`` -> ``span.mention[data-type=mention]``, else plain text.

	``data-label`` is the Discourse username: the seam returns a user id only, and
	the mention node renders ``@{label || id}``, so a username beats an email.
	"""
	for anchor in soup.find_all("a", class_=True):
		classes = _classes(anchor)
		if "mention" not in classes and "mention-group" not in classes:
			continue

		label = _text(anchor).lstrip("@").strip()
		if "mention-group" in classes:
			# Group mentions have no Gameplan counterpart; keep the readable text.
			_replace_with_text(anchor, f"@{label}" if label else "")
			continue

		username = label
		if not username:
			href = anchor.get("href") or ""
			match = _USER_PATH_RE.match(href if href.startswith("/u/") else "")
			username = match.group(1) if match else ""
		if not username:
			anchor.unwrap()
			continue

		user_id = ctx.resolve_mention(username)
		if not user_id:
			_replace_with_text(anchor, f"@{username}")
			continue

		span = soup.new_tag("span")
		span["class"] = ["mention"]
		span["data-type"] = "mention"
		span["data-id"] = user_id
		span["data-label"] = username
		span.string = f"@{username}"
		anchor.replace_with(span)


def _rewrite_emojis(soup: BeautifulSoup) -> None:
	"""Rule 10. ``img.emoji`` -> the unicode character; unknown ones keep ``:name:``."""
	table = _emoji_map()
	for img in soup.find_all("img", class_=True):
		if not _has_class(img, "emoji"):
			continue
		shortcode = (img.get("title") or img.get("alt") or "").strip().strip(":")
		char = table.get(shortcode)
		_replace_with_text(img, char or (f":{shortcode}:" if shortcode else ""))


def _rewrite_images(soup: BeautifulSoup, ctx: TransformContext) -> None:
	"""Rules 1-3. Every remaining img goes through ``ctx.resolve_image``."""
	for img in soup.find_all("img"):
		src = img.get("src") or None
		if src and _AVATAR_RE.search(src):  # quote avatars that escaped rule 6
			img.decompose()
			continue

		# Rule 3: the lazy placeholder is never the real image.
		if src and _TRANSPARENT_RE.search(src):
			src = None

		resolved = ctx.resolve_image(src, img.get("data-orig-src") or None, img.get("data-base62-sha1") or None)
		if not resolved:
			img.decompose()
			continue
		img["src"] = resolved


def _rewrite_upload_links(soup: BeautifulSoup, ctx: TransformContext) -> None:
	"""Rules 4 and 22. Dead ``/404`` links, attachments and bare upload hrefs."""
	for anchor in soup.find_all("a"):
		href = anchor.get("href") or ""
		orig_href = anchor.get("data-orig-href") or ""
		is_attachment = _has_class(anchor, "attachment")

		if orig_href.startswith(_UPLOAD_SHORT_URL):
			resolved = ctx.resolve_image(None, orig_href, None)
			label = _SIZE_SUFFIX_RE.sub("", _text(anchor)).strip()
			if resolved and _IMAGE_EXT_RE.search(resolved):
				img = soup.new_tag("img", src=resolved)
				if label:
					img["alt"] = label
				anchor.replace_with(img)
			elif resolved:
				anchor.attrs = {"href": resolved}
				anchor.string = label or resolved
			else:
				_replace_with_text(anchor, label)
			continue

		if "/uploads/" in href:
			resolved = ctx.resolve_image(href, None, None)
			if resolved:
				anchor["href"] = resolved
			else:
				_replace_with_text(anchor, _text(anchor))
			continue

		if is_attachment:  # /export_csv/... and friends: dead routes, keep the name
			_replace_with_text(anchor, _text(anchor))


def _rewrite_code_blocks(soup: BeautifulSoup) -> None:
	"""Rule 11. Map ``lang-*`` onto CodeBlockLowlight's ``language-*``."""
	for pre in soup.find_all("pre"):
		if "data-code-wrap" in pre.attrs:
			del pre["data-code-wrap"]
	for code in soup.find_all("code", class_=True):
		languages = [c[5:] for c in _classes(code) if c.startswith("lang-")]
		if not languages:
			continue
		mapped = KNOWN_CODE_LANGUAGES.get(languages[0].lower())
		if mapped:
			code["class"] = [f"language-{mapped}"]
		else:  # lang-auto, lang-import and other bogus info strings
			del code["class"]


def _rewrite_details(soup: BeautifulSoup) -> None:
	"""Rule 14. No details node in the schema: drop email trims, unwrap the rest."""
	for details in soup.find_all("details"):
		if _has_class(details, "elided"):
			details.decompose()
			continue
		summary = details.find("summary")
		if summary:
			para = soup.new_tag("p")
			strong = soup.new_tag("strong")
			strong.string = _text(summary)
			para.append(strong)
			summary.replace_with(para)
		details.unwrap()


def _rewrite_headings(soup: BeautifulSoup) -> None:
	"""Rule 15. Drop the empty self-link, demote h1 (schema allows 2-6)."""
	for anchor in soup.select("a.anchor"):
		anchor.decompose()
	for heading in soup.find_all("h1"):
		heading.name = "h2"


def _rewrite_hashtags(soup: BeautifulSoup) -> None:
	"""Rule 16. Hashtags become plain ``#name`` text."""
	for tag in soup.find_all(["a", "span"], class_=True):
		classes = _classes(tag)
		if not any(c in ("hashtag", "hashtag-cooked", "hashtag-raw") for c in classes):
			continue
		label = _text(tag)
		if not label:
			ref = tag.get("data-ref") or tag.get("data-slug") or ""
			label = ref.split(":")[-1]
		if label and not label.startswith("#"):
			label = f"#{label}"
		_replace_with_text(tag, label)


def _rewrite_polls(soup: BeautifulSoup) -> None:
	"""Rule 17. ``div.poll`` -> a static list, marked so it can be stripped later."""
	for poll in soup.select("div.poll"):
		options = [_text(li) for li in poll.select("li[data-poll-option-id]")]
		options = [o for o in options if o]

		head = soup.new_tag("p")
		head[_POLL_MARKER] = "1"
		em = soup.new_tag("em")
		em.string = "Poll:"
		head.append(em)

		replacement = [head]
		if options:
			ul = soup.new_tag("ul")
			ul[_POLL_MARKER] = "1"
			for option in options:
				li = soup.new_tag("li")
				li.string = option
				ul.append(li)
			replacement.append(ul)

		poll.replace_with(*replacement)


def _rewrite_videos(soup: BeautifulSoup) -> None:
	"""Rule 18. The Video node reads ``src`` off ``<video>``, never off ``<source>``."""
	for video in soup.find_all("video"):
		src = video.get("src")
		if not src:
			source = video.find("source", src=True)
			src = source.get("src") if source else None
		for child in list(video.contents):  # <source> and the fallback link
			child.extract()
		if not src:
			video.decompose()
			continue
		video["src"] = src


def _rewrite_iframes(soup: BeautifulSoup) -> None:
	"""Rules 19-20. Keep allowlisted embeds, strip everything else."""
	for iframe in soup.find_all("iframe"):
		src = iframe.get("src") or ""
		host = urlsplit(src).netloc.lower()
		if not src or not any(domain in host for domain in ALLOWED_IFRAME_DOMAINS):
			iframe.decompose()


def _flatten_local_dates(soup: BeautifulSoup) -> None:
	"""Rule 23. Keep the rendered date text, drop the plugin span."""
	for span in soup.select("span.discourse-local-date"):
		_replace_with_text(span, _text(span))


def _flatten_footnotes(soup: BeautifulSoup) -> None:
	"""Rule 24. ``sup.footnote-ref`` -> ``[1]`` text; the list at the bottom stays prose."""
	for sup in soup.select("sup.footnote-ref"):
		_replace_with_text(sup, _text(sup))
	for backref in soup.select("a.footnote-backref"):
		backref.decompose()
	for sep in soup.select("hr.footnotes-sep"):
		sep.decompose()
	for block in soup.select("div.footnotes"):
		block.unwrap()


def _strip_chrome(soup: BeautifulSoup) -> None:
	"""Remove Discourse decoration that survived its wrapper."""
	for selector in CHROME_SELECTORS:
		for tag in soup.select(selector):
			tag.decompose()


def _normalize_divs(soup: BeautifulSoup) -> None:
	"""Rule 13 tail. TipTap skips unknown wrappers, so make the stored HTML match.

	A div holding only inline content becomes a paragraph; anything else is
	unwrapped in place.
	"""
	for div in soup.find_all("div"):
		if div.find(_BLOCK_TAGS):
			div.unwrap()
		else:
			div.name = "p"
			div.attrs = {}


def _drop_unknown_tags(soup: BeautifulSoup) -> None:
	for tag in soup.find_all(True):
		if tag.name in ("html", "head", "body"):  # the document frame html5lib adds
			continue
		if tag.name not in ALLOWED_TAGS:
			tag.unwrap()


def _trim_pre_newline(soup: BeautifulSoup) -> None:
	"""A newline right after ``<pre>`` is dropped on parse, so drop it on write.

	Runs last: removing a blank paragraph can expose a newline that was not the
	first child before.
	"""
	for pre in soup.find_all("pre"):
		first = pre.contents[0] if pre.contents else None
		if isinstance(first, NavigableString) and first.startswith("\n"):
			first.replace_with(NavigableString(str(first)[1:]))


def _drop_blank_paragraphs(soup: BeautifulSoup) -> None:
	for para in soup.find_all("p"):
		if _is_blank(para):
			para.decompose()


def _scrub_attrs(soup: BeautifulSoup) -> None:
	"""Final pass: keep only attributes bleach also keeps, so output is stable."""
	for tag in soup.find_all(True):
		allowed = ALLOWED_ATTRS.get(tag.name, set())
		for name in list(tag.attrs):
			if name not in allowed:
				del tag[name]


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


def _parse(html: str) -> BeautifulSoup:
	# html5lib matches what bleach parses with, so the rewritten tree is already
	# in the shape the sanitizer would force it into.
	soup = BeautifulSoup(html or "", "html5lib")
	return soup


def _serialize(soup: BeautifulSoup) -> str:
	body = soup.body
	if body is None:
		return ""
	return body.decode_contents(formatter=_FORMATTER).strip()


def transform_cooked(html: str, ctx: TransformContext) -> str:
	"""Apply every cooked -> Gameplan rule from research/04.

	Internal link rewriting is deliberately absent: it is a second pass that can
	only run once every topic exists (:func:`rewrite_internal_links`).
	"""
	if not html or not html.strip():
		return ""

	soup = _parse(html)

	_strip_svg(soup)
	_flatten_local_dates(soup)
	_unwrap_lightboxes(soup)
	_rewrite_quotes(soup)
	_rewrite_oneboxes(soup)
	_strip_chrome(soup)
	_plain_onebox_links(soup)
	_rewrite_mentions(soup, ctx)
	_rewrite_emojis(soup)
	_rewrite_polls(soup)
	_rewrite_videos(soup)
	_rewrite_iframes(soup)
	_rewrite_upload_links(soup, ctx)
	_rewrite_images(soup, ctx)
	_rewrite_code_blocks(soup)
	_rewrite_details(soup)
	_rewrite_headings(soup)
	_rewrite_hashtags(soup)
	_flatten_footnotes(soup)
	_normalize_divs(soup)
	_drop_unknown_tags(soup)
	_drop_blank_paragraphs(soup)
	_trim_pre_newline(soup)
	_scrub_attrs(soup)

	return _serialize(soup)


def strip_poll_markup(html: str) -> str:
	"""Remove poll markup from a body whose poll became a real GP Poll record.

	Works on raw cooked HTML (``div.poll``) and on the static list
	:func:`transform_cooked` leaves behind, so call order does not matter.
	"""
	if not html or not html.strip():
		return ""

	soup = _parse(html)
	for poll in soup.select("div.poll, div.poll-container, div.poll-info"):
		poll.decompose()
	for marked in soup.select(f"[{_POLL_MARKER}]"):
		marked.decompose()
	return _serialize(soup)


def accepted_answer_badge(html: str) -> str:
	"""Prepend the accepted-answer badge (fidelity cut §3).

	``<p><strong>…</strong></p>`` is the strongest construct both gates keep: the
	sanitizer allows both tags, and StarterKit parses both.
	"""
	return f"<p><strong>✅ Accepted answer</strong></p>{html or ''}"


def synthesized_quote(html: str, parent_author: str, parent_excerpt: str) -> str:
	"""Prepend a quote naming the parent author (fidelity cut §4)."""
	excerpt = " ".join((parent_excerpt or "").split())
	if len(excerpt) > 200:
		cut = excerpt[:200].rsplit(" ", 1)[0] or excerpt[:200]
		excerpt = f"{cut}…"

	parts = [f"<p><strong>@{escape(parent_author or 'unknown')}:</strong></p>"]
	if excerpt:
		parts.append(f"<p>{escape(excerpt)}</p>")
	return f"<blockquote>{''.join(parts)}</blockquote>{html or ''}"


def _internal_target(href: str) -> tuple[str, str] | None:
	"""Classify a Discourse URL as ``('t'|'u'|'c', key)``, else ``None``."""
	parts = urlsplit(href)
	if parts.scheme and parts.scheme not in ("http", "https"):
		return None
	if parts.netloc and not any(parts.netloc.lower().endswith(h) for h in DISCOURSE_HOSTS):
		return None

	path = parts.path
	match = _TOPIC_PATH_RE.match(path)
	if match:
		return "t", match.group(1)

	match = _USER_PATH_RE.match(path)
	if match:
		return "u", match.group(1)

	match = _CATEGORY_PATH_RE.match(path)
	if match:
		segments = [s for s in match.group(1).split("/") if s]
		if not segments:
			return None
		# `/c/erpnext/manufacturing/19` ends in the category id; `/c/slug` ends in
		# its slug. Either way the last segment identifies the category.
		return "c", segments[-1]

	return None


def rewrite_internal_links(html: str, resolve) -> tuple[str, int]:
	"""Second pass over already-transformed HTML. Returns ``(html, rewritten)``.

	``resolve(kind, key) -> str | None`` where ``kind`` is ``'t'``, ``'u'`` or
	``'c'``. ``key`` is the topic id, the Discourse username, or the category id
	(its slug when the URL carries no id).

	Only prose anchors are considered. Mentions are already ``span.mention`` after
	:func:`transform_cooked`, and any anchor still carrying a Discourse class is
	chrome — 61,921 posts match ``href="/u/"`` against 969 real user links, so a
	naive match would resurrect every mention.

	A link the map cannot place is absolutized onto discuss.frappe.io rather than
	left relative, which would 404 on the Gameplan host.
	"""
	if not html or not html.strip():
		return "", 0

	soup = _parse(html)
	rewritten = 0

	for anchor in soup.find_all("a", href=True):
		if anchor.find_parent("span", class_="mention"):
			continue
		if any(c in _CHROME_ANCHOR_CLASSES for c in _classes(anchor)):
			continue

		href = anchor["href"].strip()
		if not href or href.startswith("#") or href.startswith("//"):
			continue
		if href.startswith(_LOCAL_HREF_PREFIXES):
			continue

		target = _internal_target(href)
		if target:
			resolved = resolve(*target)
			if resolved:
				anchor["href"] = resolved
				rewritten += 1
				continue

		if href.startswith("/"):
			parts = urlsplit(href)
			anchor["href"] = urlunsplit(
				("https", DISCOURSE_CANONICAL_HOST, parts.path, parts.query, parts.fragment)
			)

	return _serialize(soup), rewritten
