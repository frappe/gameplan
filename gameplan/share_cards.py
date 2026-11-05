"""Generate public discussion previews after checking anonymous access."""

import hashlib
import io
import json
import subprocess
from functools import lru_cache

import frappe
from PIL import Image, ImageDraw, ImageFont
from werkzeug.wrappers import Response

from gameplan.public_access import public_access_enabled
from gameplan.public_payload import handles_for
from gameplan.public_seo import public_viewer, read_public_doc, text_preview


@frappe.whitelist(allow_guest=True, methods=["GET"])
def image(discussion: str, v: str = ""):
	if not public_access_enabled():
		frappe.throw("Page not found", frappe.DoesNotExistError)
	with public_viewer():
		post = read_public_doc("GP Discussion", discussion)
		space = read_public_doc("GP Project", post.project)
		read_public_doc("GP Team", space.team)
		data = {
			"title": text_preview(post.title),
			"description": text_preview(post.content),
			"space": space.title or "Discussion",
			"author": handles_for({post.owner}).get(post.owner) or "",
			"replies": post.comments_count or 0,
		}
	key = (
		"gameplan:share-card:v2:"
		+ hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
	)
	content = frappe.cache.get_value(key)
	if content is None:
		content = render_card(**data)
		frappe.cache.set_value(key, content, expires_in_sec=3600)
	return Response(content, mimetype="image/png", headers={"Cache-Control": "private, no-store"})


@lru_cache(maxsize=8)
def font(weight, size):
	return ImageFont.truetype(
		frappe.get_app_path("frappe", "public", "css", "fonts", "inter", f"Inter-{weight}.woff2"), size
	)


@lru_cache(maxsize=4096)
def supports(face, character):
	if character.isspace():
		return True
	missing = face.getmask(chr(0x10FFFF))
	glyph = face.getmask(character)
	return glyph.size != missing.size or bytes(glyph) != bytes(missing)


@lru_cache(maxsize=128)
def fallback_font(codepoints, size):
	try:
		match = subprocess.run(
			["fc-match", "-f", "%{file}", ":charset=" + " ".join(f"{code:x}" for code in codepoints)],
			capture_output=True,
			text=True,
			timeout=2,
			check=True,
		)
		return load_fallback_font(match.stdout.strip(), size)
	except (OSError, ValueError, subprocess.SubprocessError):
		return None


@lru_cache(maxsize=16)
def load_fallback_font(path, size):
	return ImageFont.truetype(path, size)


def text_font(text, weight, size):
	face = font(weight, size)
	missing = tuple(sorted({ord(char) for char in text if not supports(face, char)}))
	if missing:
		fallback = fallback_font(missing, size)
		if fallback and all(supports(fallback, char) for char in text):
			face = fallback
	return "".join(char if supports(face, char) else "?" for char in text), face


def lines(draw, text, face, width, limit):
	"""Fit plain text into a bounded number of lines, including long unbroken words."""
	words = " ".join((text or "").split())[:500].split(" ")
	result, line = [], ""
	for word in words:
		while word and draw.textlength(word, font=face) > width:
			if line:
				result.append(line)
				line = ""
			cut = 1
			while cut < len(word) and draw.textlength(word[: cut + 1], font=face) <= width:
				cut += 1
			result.append(word[:cut])
			word = word[cut:]
			if len(result) >= limit:
				break
		if len(result) >= limit:
			break
		candidate = f"{line} {word}".strip()
		if line and draw.textlength(candidate, font=face) > width:
			result.append(line)
			line = word
		else:
			line = candidate
		if len(result) >= limit:
			break
	if line and len(result) < limit:
		result.append(line)
	if len(result) >= limit and " ".join(result) != " ".join(words):
		last = result[-1]
		while last and draw.textlength(last + "…", font=face) > width:
			last = last[:-1]
		result[-1] = last.rstrip() + "…"
	return result


def render_card(title, description, space, author, replies):
	image = Image.new("RGB", (1200, 630), "#faf9f6")
	draw = ImageDraw.Draw(image)
	logo = Image.open(frappe.get_app_path("gameplan", "public", "gameplan_logo_256.png")).convert("RGBA")
	logo = logo.resize((52, 52), Image.Resampling.LANCZOS)
	image.paste(logo, (72, 57), logo)
	draw.text((140, 61), "Gameplan", font=font("SemiBold", 35), fill="#242424")
	draw.text((72, 165), "COMMUNITY DISCUSSION", font=font("SemiBold", 20), fill="#a75c00")
	y = 215
	title, title_font = text_font(title, "SemiBold", 62)
	for line in lines(draw, title, title_font, 1040, 3):
		draw.text((72, y), line, font=title_font, fill="#171717")
		y += 76
	description, description_font = text_font(description, "Regular", 27)
	for line in lines(draw, description, description_font, 1030, 1 if y >= 430 else 2):
		draw.text((74, y + 18), line, font=description_font, fill="#646464")
		y += 37
	draw.line((72, 516, 1128, 516), fill="#e6e3dd", width=2)
	footer = [space, *([f"@{author}"] if author else [])]
	footer.append(f"{replies} {'response' if replies == 1 else 'responses'}")
	footer, footer_font = text_font("  ·  ".join(footer), "Medium", 25)
	footer_text = lines(draw, footer, footer_font, 1056, 1)
	if footer_text:
		draw.text((72, 548), footer_text[0], font=footer_font, fill="#616161")
	output = io.BytesIO()
	image.save(output, format="PNG", optimize=True)
	return output.getvalue()
