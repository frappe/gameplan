from gameplan.search_sqlite import GameplanSearch


def execute():
	search = GameplanSearch()
	if search.index_exists():
		search.drop_index()
	search.build_index()
