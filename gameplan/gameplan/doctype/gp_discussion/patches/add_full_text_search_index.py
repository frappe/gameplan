# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from ..gp_discussion import make_full_text_search_index


def execute():
    make_full_text_search_index()
