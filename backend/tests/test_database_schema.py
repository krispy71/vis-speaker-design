def test_drivers_table_exists(db):
    import database
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='drivers'"
        ).fetchall()
    assert len(rows) == 1

def test_sessions_table_exists(db):
    import database
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchall()
    assert len(rows) == 1

def test_driver_search_cache_table_exists(db):
    import database
    with database.get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='driver_search_cache'"
        ).fetchall()
    assert len(rows) == 1
