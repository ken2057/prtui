import sqlite3
from pathlib import Path

DB_PATH = Path('/tmp/prtui.db')

pr_table_creation_query = """
    CREATE TABLE IF NOT EXISTS PRS (
		number INT,
        repo CHAR(25),
		type CHAR(25),
        author CHAR(25),
        title CHAR(100),
        updated_at CHAR(30),
		read_at CHAR(30),
		PRIMARY KEY(repo, number)
    );
"""

comments_table_creation_query = """
	CREATE TABLE IF NOT EXISTS COMMENTS (
		id INT PRIMARY KEY,
		pr_number INT,
		pr_repo CHAR(25),
		user CHAR(25),
		path CHAR(100),
		diff_hunk TEXT,
		updated_at CHAR(30),
		comment TEXT,
		FOREIGN KEY (pr_repo, pr_number) REFERENCES PRS(repo, number) ON DELETE CASCADE
	)
"""

def db_exists():
	return DB_PATH.exists()

def connect():
	connection_obj = sqlite3.connect(DB_PATH)
	cursor_obj = connection_obj.cursor()
	return connection_obj, cursor_obj

def create_pr_table(cursor_obj):
	cursor_obj.execute(pr_table_creation_query)

def disconnect(connection_obj):
	connection_obj.commit()
	connection_obj.close()

def pr_insert(cursor_obj, pr):
	cursor_obj.execute(
		"INSERT INTO PRS (number, repo, type, author, title, updated_at)"
		" VALUES (?, ?, ?, ?, ?, ?)"
		" ON CONFLICT(repo, number) DO UPDATE SET"
		" type=excluded.type, author=excluded.author,"
		" title=excluded.title, updated_at=excluded.updated_at",
		(pr["number"], pr["repo"], pr["type"], pr["author"],
		 pr["title"], pr["updated_at"])
	)

def pr_get_all(cursor_obj, type):
	cursor_obj.execute(
		"SELECT number, repo, type, author, title, updated_at, read_at FROM PRS"
		" WHERE type=?", (type,)
	)
	rows = cursor_obj.fetchall()
	return [
		{"number": r[0], "repo": r[1], "type": r[2], "author": r[3],
		 "title": r[4], "updated_at": r[5], "read_at": r[6]}
		for r in rows
	]

def pr_mark_read(cursor_obj, repo, number):
	cursor_obj.execute(
		"UPDATE PRS SET read_at = datetime('now') WHERE repo = ? AND number = ?",
		(repo, number)
	)

def create_comments_table(cursor_obj):
	cursor_obj.execute(comments_table_creation_query)

def comment_insert(cursor_obj, comment):
	cursor_obj.execute(
		"REPLACE INTO COMMENTS VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
		(comment["id"], comment["pr_number"], comment["pr_repo"],
		 comment["user"], comment["path"], comment["diff_hunk"],
		 comment["updated_at"], comment["body"])
	)

def get_comments(cursor_obj, pr_number, pr_repo):
	cursor_obj.execute(
		"SELECT id, pr_number, pr_repo, user, path, diff_hunk, updated_at, comment"
		" FROM COMMENTS WHERE pr_number = ? AND pr_repo = ?"
		" ORDER BY updated_at DESC",
		(pr_number, pr_repo)
	)
	return [
		{"id": r[0], "pr_number": r[1], "pr_repo": r[2],
		 "user": r[3], "path": r[4], "diff_hunk": r[5],
		 "updated_at": r[6], "comment": r[7]}
		for r in cursor_obj.fetchall()
	]
