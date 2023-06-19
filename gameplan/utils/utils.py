# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import inspect
import re
from functools import wraps
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def validate_url(url):
	result = urlparse(url)
	if not result.scheme:
		url = "https://" + url
		result = urlparse(url)
	return url if (result.scheme and result.netloc) else False


def extract_mentions(html):
	if not html:
		return []
	soup = BeautifulSoup(html, 'html.parser')
	mentions = []
	for d in soup.find_all('span', attrs={'data-type': 'mention'}):
		mentions.append(frappe._dict(full_name=d.get('data-label'), email=d.get('data-id')))
	return mentions


def remove_empty_trailing_paragraphs(html):
	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, 'html.parser')
	# remove p, br tags that are at the end with no content
	all_tags = soup.find_all(True)
	all_tags.reverse()
	for tag in all_tags:
		if tag.name in ['br', 'p'] and not tag.contents:
			tag.extract()
		else:
			# break on first non-empty tag
			break
	return str(soup)


def validate_type(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		sig = inspect.signature(func)
		annotated_types = {k: v.annotation for k, v in sig.parameters.items() if v.annotation != inspect._empty}
		bound_args = sig.bind(*args, **kwargs)
		bound_args.apply_defaults()
		for arg_name, arg_value in bound_args.arguments.items():
			if arg_name in annotated_types:
				if arg_value is not None and not isinstance(arg_value, annotated_types[arg_name]):
					raise TypeError(f"{func.__name__}: Argument {arg_name} must be of type {annotated_types[arg_name]}")
		return func(*args, **kwargs)
	return wrapper

def url_safe_slug(text):
	if not text:
		return text
	slug = re.sub(r'[^A-Za-z0-9\s-]+', '', text.lower())
	slug = slug.replace('\n', ' ')
	slug = slug.split(' ')
	slug = [part for part in slug if part]
	slug = '-'.join(slug)
	slug = re.sub('[-]+', '-', slug)
	return slug
