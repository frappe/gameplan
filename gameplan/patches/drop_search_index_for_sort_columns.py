import os

from gameplan.search_sqlite import GameplanSearch


def execute():
	search = GameplanSearch()
	if search.index_exists():
		search.drop_index()
	temp_db_path = search._get_db_path(is_temp=True)
	if os.path.exists(temp_db_path):
		os.unlink(temp_db_path)
