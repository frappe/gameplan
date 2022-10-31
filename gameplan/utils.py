# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import inspect
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


def validate_type(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		sig = inspect.signature(func)
		annotated_types = {k: v.annotation for k, v in sig.parameters.items() if v.annotation != inspect._empty}
		bound_args = sig.bind(*args, **kwargs)
		bound_args.apply_defaults()
		for arg_name, arg_value in bound_args.arguments.items():
			if arg_name in annotated_types:
				if not isinstance(arg_value, annotated_types[arg_name]):
					raise TypeError(f"{func.__name__}: Argument {arg_name} must be of type {annotated_types[arg_name]}")
		return func(*args, **kwargs)
	return wrapper
