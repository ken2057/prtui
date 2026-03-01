"""Data store — bridges the database and the UI layer."""

import prdb


def _pr_state(pr):
    """Determine display state based on read_at vs updated_at."""
    if pr["read_at"] is None:
        return "unread"
    if pr["updated_at"] > pr["read_at"]:
        return "unread"
    return "read"


def get_pull_requests(type):
    """Fetch all PRs from the DB, formatted for presentation."""
    if not prdb.db_exists():
        return []
    conn, cursor = prdb.connect()
    prs = [
        {**pr, "state": _pr_state(pr)} for pr in prdb.pr_get_all(cursor, type)
    ]
    prdb.disconnect(conn)
    return prs


def mark_read(repo, number):
    """Mark a PR as read now."""
    conn, cursor = prdb.connect()
    prdb.pr_mark_read(cursor, repo, number)
    prdb.disconnect(conn)


def get_comments(repo, number):
    """Fetch comments for a PR, formatted for presentation."""
    conn, cursor = prdb.connect()
    comments = prdb.get_comments(cursor, number, repo)
    prdb.disconnect(conn)
    return comments
