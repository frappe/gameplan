# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe, requests
from urllib.parse import urlparse


def validate_url(url):
	result = urlparse(url)
	if not result.scheme:
		url = "https://" + url
		result = urlparse(url)
	return url if (result.scheme and result.netloc) else False
