"""GitHub API client for fetching pull requests, reviews, and comments."""

import requests
import config
import prdb

_cfg = config.read_config()

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {_cfg['token']}",
    "Accept": "application/vnd.github+json",
}

REPOS = _cfg["repos"]
USER = _cfg["username"]
TEAM = _cfg.get("team", "")


def _search_prs(query, pr_type, repo):
    """Run a GitHub search and return matching PRs."""
    prs = []
    url = f"{API}/search/issues"
    params = {"q": query, "per_page": 100}

    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        for item in resp.json()["items"]:
            print(f"TMP: [{pr_type}] #{item['number']} {item['title'][:60]}")
            prs.append({
                "number": item["number"],
                "repo": repo,
                "author": item["user"]["login"],
                "title": item["title"],
                "url": item["html_url"],
                "updated_at": item["updated_at"],
                "type": pr_type,
            })
        url = resp.links.get("next", {}).get("url")
        params = {}  # params are baked into the next URL

    return prs


def get_my_prs():
    """Fetch open PRs authored by me."""
    prs = []
    for repo in REPOS:
        prs.extend(_search_prs(
            f"repo:{repo} type:pr state:open author:{USER}", "mine", repo
        ))
    return prs


def get_reviewer_prs():
    """Fetch open PRs where I am explicitly a reviewer (any state)."""
    seen = set()
    prs = []
    for repo in REPOS:
        for pr in _search_prs(
            f"repo:{repo} type:pr state:open review-requested:{USER}",
            "reviewer", repo
        ):
            key = (pr["repo"], pr["number"])
            if key not in seen:
                seen.add(key)
                prs.append(pr)
        for pr in _search_prs(
            f"repo:{repo} type:pr state:open reviewed-by:{USER}",
            "reviewer", repo
        ):
            key = (pr["repo"], pr["number"])
            if key not in seen:
                seen.add(key)
                prs.append(pr)
    return prs


def get_team_requested_prs(exclude):
    """Fetch open PRs requested via team, excluding already-known PRs."""
    exclude_keys = {(pr["repo"], pr["number"]) for pr in exclude}
    prs = []
    for repo in REPOS:
        for pr in _search_prs(
            f"repo:{repo} type:pr state:open team-review-requested:{TEAM}",
            "requested", repo
        ):
            key = (pr["repo"], pr["number"])
            if key not in exclude_keys:
                prs.append(pr)
    return prs


def get_approvals(pr_number, repo):
    """Fetch reviews for a PR, returning list of approving usernames."""
    reviews = {}
    url = f"{API}/repos/{repo}/pulls/{pr_number}/reviews"
    params = {"per_page": 100}

    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        for r in resp.json():
            if r["state"] == "COMMENTED":
                continue
            user = r["user"]["login"]
            reviews[user] = {
                "user": user,
                "state": r["state"],
                "submitted_at": r["submitted_at"],
            }
        url = resp.links.get("next", {}).get("url")
        params = {}

    return [
        user for user, review in reviews.items()
        if review["state"] == "APPROVED"
    ]


def get_comments(pr_number, repo):
    """Fetch all comments on a PR (conversation + inline review)."""
    comments = []

    # Conversation comments (no code context)
    url = f"{API}/repos/{repo}/issues/{pr_number}/comments"
    params = {"per_page": 100}
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        for c in resp.json():
            comments.append({
                "id": c["id"],
                "pr_number": pr_number,
                "pr_repo": repo,
                "user": c["user"]["login"],
                "body": c["body"],
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
                "path": "",
                "diff_hunk": "",
            })
        url = resp.links.get("next", {}).get("url")
        params = {}

    # Inline review comments (with code context)
    url = f"{API}/repos/{repo}/pulls/{pr_number}/comments"
    params = {"per_page": 100}
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        for c in resp.json():
            comments.append({
                "id": c["id"],
                "pr_number": pr_number,
                "pr_repo": repo,
                "user": c["user"]["login"],
                "body": c["body"],
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
                "path": c.get("path", ""),
                "diff_hunk": c.get("diff_hunk", ""),
            })
        url = resp.links.get("next", {}).get("url")
        params = {}

    comments.sort(key=lambda c: c["created_at"])
    return comments


def fetch_and_store(on_progress=None):
    """Fetch PRs and comments from GitHub and store in the database."""
    def progress(msg):
        if on_progress:
            on_progress(msg)

    progress("Fetching your PRs...")
    prs = get_my_prs()
    progress("Fetching reviewer PRs...")
    reviewer_prs = get_reviewer_prs()
    prs.extend(reviewer_prs)
    progress("Fetching team-requested PRs...")
    prs.extend(get_team_requested_prs(exclude=reviewer_prs))

    comments = []
    for i, pr in enumerate(prs):
        progress(f"Fetching comments ({i + 1}/{len(prs)})...")
        comments.extend(get_comments(pr["number"], pr["repo"]))

    progress("Storing in database...")
    conn, cursor = prdb.connect()
    prdb.create_pr_table(cursor)
    prdb.create_comments_table(cursor)
    for pr in prs:
        prdb.pr_insert(cursor, pr)
    for comment in comments:
        prdb.comment_insert(cursor, comment)
    prdb.disconnect(conn)

if __name__ == "__main__":
    fetch_and_store()
