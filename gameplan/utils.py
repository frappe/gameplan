# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
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
