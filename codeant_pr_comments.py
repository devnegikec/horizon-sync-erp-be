#!/usr/bin/env python3
"""Collect and resolve CodeAnt inline PR review comments (no codeant-cli needed).

Commands:
  collect PR_URL   Fetch unresolved inline CodeAnt review threads and write
                   them to .codeant-pr-comments.json for an AI agent to read.
  resolve PR_URL   Resolve the threads listed in .codeant-resolutions.json.

Environment:
  GitHub:          GITHUB_TOKEN
                   (fine-grained PAT with Pull requests: read; add write to resolve)
  Bitbucket Cloud: BITBUCKET_USERNAME + BITBUCKET_APP_PASSWORD
                   (App Password with pullrequests:read / pullrequests:write)

Examples:
  GITHUB_TOKEN=ghp_xxx \
    python3 codeant_pr_comments.py collect https://github.com/OWNER/REPO/pull/7

  BITBUCKET_USERNAME=you BITBUCKET_APP_PASSWORD=xxx \
    python3 codeant_pr_comments.py collect https://bitbucket.org/WS/REPO/pull-requests/7
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_OUT = ".codeant-pr-comments.json"
DEFAULT_RESOLUTIONS = ".codeant-resolutions.json"

CODEANT_AUTHORS = {
    "codeant-ai",
    "codeant-ai[bot]",
    "codeant-bot",
    "codeant ai",
}

GITHUB_THREADS_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number title url
      reviewThreads(first: 100, after: $endCursor) {
        nodes {
          id isResolved isOutdated
          comments(first: 100) {
            nodes {
              databaseId
              author { login }
              body path line originalLine createdAt url
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

GITHUB_RESOLVE_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}
"""


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _request_json(
    url: str, *, method: str = "GET", headers=None, data=None
) -> dict | list:
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} from {url}: {detail[:500]}", file=sys.stderr)
        raise


def _is_codeant(author: str | None, body: str | None) -> bool:
    if author and author.strip().lower() in CODEANT_AUTHORS:
        return True
    if body and (
        "https://app.codeant.ai/fix-in-ide" in body
        or "https://app.codeant.ai/feedback" in body
    ):
        return True
    return False


def _detect_provider(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if "github.com" in host:
        return "github"
    if "bitbucket.org" in host:
        return "bitbucket"
    if "gitlab" in host:
        return "gitlab"
    if "dev.azure.com" in host or "visualstudio.com" in host:
        return "azure"
    raise SystemExit(
        f"Cannot detect provider from URL host: {host!r}. "
        "Pass --provider github|bitbucket."
    )


# ────────────────────────────────────────────────────────────────────────────
# GitHub
# ────────────────────────────────────────────────────────────────────────────


def _github_graphql(token: str, query: str, variables: dict) -> dict:
    return _request_json(
        "https://api.github.com/graphql",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
    )


def _parse_github_url(url: str) -> tuple[str, str, int]:
    m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not m:
        raise SystemExit(
            "Expected GitHub PR URL like https://github.com/OWNER/REPO/pull/123"
        )
    return m.group(1), m.group(2), int(m.group(3))


def _collect_github(token: str, url: str) -> dict:
    owner, name, number = _parse_github_url(url)
    threads: list[dict] = []
    end_cursor: str | None = None

    while True:
        result = _github_graphql(
            token,
            GITHUB_THREADS_QUERY,
            {"owner": owner, "name": name, "number": number, "endCursor": end_cursor},
        )
        repo = result.get("data", {}).get("repository")
        if not repo or not repo.get("pullRequest"):
            raise SystemExit(
                "GitHub returned no PR data (check token scope / PR number)."
            )
        pr = repo["pullRequest"]

        for node in pr["reviewThreads"]["nodes"]:
            comments = node.get("comments", {}).get("nodes", [])
            if not comments:
                continue
            root = comments[0]
            if node.get("isResolved"):
                continue
            author = (root.get("author") or {}).get("login")
            if not _is_codeant(author, root.get("body")):
                continue
            path = root.get("path")
            if not path:
                continue
            line = root.get("line")
            if line is None:
                line = root.get("originalLine")
            threads.append(
                {
                    "thread_id": node.get("id"),
                    "comment_id": root.get("databaseId"),
                    "author": author,
                    "body": root.get("body"),
                    "path": path,
                    "line": line,
                    "url": root.get("url"),
                    "resolved": bool(node.get("isResolved")),
                    "outdated": bool(node.get("isOutdated")),
                    "provider": "github",
                    "resolve_hint": {"provider": "github", "thread_id": node.get("id")},
                }
            )

        page_info = pr["reviewThreads"].get("pageInfo", {})
        if page_info.get("hasNextPage"):
            end_cursor = page_info.get("endCursor")
        else:
            break

    return {
        "provider": "github",
        "repo": f"{owner}/{name}",
        "pr_number": number,
        "pr_title": pr.get("title"),
        "pr_url": pr.get("url"),
        "threads": threads,
    }


# ────────────────────────────────────────────────────────────────────────────
# Bitbucket Cloud
# ────────────────────────────────────────────────────────────────────────────


def _parse_bitbucket_url(url: str) -> tuple[str, str, str]:
    m = re.search(r"bitbucket\.org/([^/]+)/([^/]+)/pull-requests/(\d+)", url)
    if not m:
        raise SystemExit(
            "Expected Bitbucket PR URL like https://bitbucket.org/WORKSPACE/REPO/pull-requests/123"
        )
    return m.group(1), m.group(2), m.group(3)


def _collect_bitbucket(username: str, app_password: str, url: str) -> dict:
    workspace, repo_slug, pr_id = _parse_bitbucket_url(url)
    base = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}"
    auth = f"{username}:{app_password}"
    headers = {
        "Authorization": "Basic "
        + __import__("base64").b64encode(auth.encode()).decode(),
        "Accept": "application/json",
    }

    pr = _request_json(base, headers=headers)

    threads: list[dict] = []
    next_url: str | None = f"{base}/comments?pagelen=100"
    while next_url:
        page = _request_json(next_url, headers=headers)
        for comment in page.get("values", []):
            if comment.get("deleted") or comment.get("pending"):
                continue
            if "parent" in comment and comment["parent"]:
                continue  # reply, not a root comment
            inline = comment.get("inline") or {}
            path = inline.get("path")
            if not path:
                continue
            if comment.get("resolution"):
                continue
            author_info = comment.get("user") or {}
            author = (
                author_info.get("nickname")
                or author_info.get("display_name")
                or author_info.get("username")
            )
            raw = (comment.get("content") or {}).get("raw", "")
            if not _is_codeant(author, raw):
                continue
            to = inline.get("to")
            frm = inline.get("from")
            line = (
                (to or {}).get("line")
                if to
                else (frm or {}).get("line")
                if frm
                else None
            )
            threads.append(
                {
                    "thread_id": str(comment.get("id")),
                    "comment_id": str(comment.get("id")),
                    "author": author,
                    "body": raw,
                    "path": path,
                    "line": line,
                    "url": (comment.get("links") or {}).get("html", {}).get("href"),
                    "resolved": False,
                    "outdated": False,
                    "provider": "bitbucket",
                    "resolve_hint": {
                        "provider": "bitbucket",
                        "workspace": workspace,
                        "repo_slug": repo_slug,
                        "pr_id": pr_id,
                        "comment_id": str(comment.get("id")),
                    },
                }
            )
        next_url = page.get("next")

    return {
        "provider": "bitbucket",
        "workspace": workspace,
        "repo_slug": repo_slug,
        "pr_id": pr_id,
        "pr_title": pr.get("title"),
        "pr_url": (pr.get("links") or {}).get("html", {}).get("href"),
        "threads": threads,
    }


# ────────────────────────────────────────────────────────────────────────────
# Resolve
# ────────────────────────────────────────────────────────────────────────────


def _resolve_github(token: str, thread_id: str) -> bool:
    result = _github_graphql(token, GITHUB_RESOLVE_MUTATION, {"threadId": thread_id})
    thread = result.get("data", {}).get("resolveReviewThread", {}).get("thread", {})
    return bool(thread.get("isResolved"))


def _resolve_bitbucket(username: str, app_password: str, hint: dict) -> bool:
    workspace = hint["workspace"]
    repo_slug = hint["repo_slug"]
    pr_id = hint["pr_id"]
    comment_id = hint["comment_id"]
    url = (
        f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
        f"/pullrequests/{pr_id}/comments/{comment_id}/resolve"
    )
    auth = f"{username}:{app_password}"
    import base64

    headers = {
        "Authorization": "Basic " + base64.b64encode(auth.encode()).decode(),
        "Accept": "application/json",
    }
    resp = _request_json(url, method="POST", headers=headers)
    return bool(resp)


def _resolve(provider: str, pr_url: str, resolutions: list[dict]) -> None:
    if provider == "github":
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is not set")
        for item in resolutions:
            if item.get("provider") != "github":
                continue
            tid = item.get("thread_id")
            try:
                ok = _resolve_github(token, tid)
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED thread {tid}: {exc}")
                continue
            print(f"{'RESOLVED' if ok else 'NOT CONFIRMED'} github thread {tid}")
        return

    if provider == "bitbucket":
        username = os.environ.get("BITBUCKET_USERNAME")
        app_password = os.environ.get("BITBUCKET_APP_PASSWORD")
        if not username or not app_password:
            raise SystemExit("BITBUCKET_USERNAME / BITBUCKET_APP_PASSWORD are not set")
        for item in resolutions:
            if item.get("provider") != "bitbucket":
                continue
            try:
                ok = _resolve_bitbucket(username, app_password, item)
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED comment {item.get('comment_id')}: {exc}")
                continue
            print(
                f"{'RESOLVED' if ok else 'NOT CONFIRMED'} bitbucket comment {item.get('comment_id')}"
            )
        return

    raise SystemExit(f"Unsupported provider for resolve: {provider}")


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "resolve"])
    parser.add_argument("pr_url", help="Pull request URL")
    parser.add_argument(
        "--provider",
        choices=["github", "bitbucket"],
        help="Override provider detection",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output path for collect (default {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--resolutions",
        default=DEFAULT_RESOLUTIONS,
        help=f"Input path for resolve (default {DEFAULT_RESOLUTIONS})",
    )
    args = parser.parse_args()

    provider = args.provider or _detect_provider(args.pr_url)

    if args.command == "collect":
        if provider == "github":
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise SystemExit("GITHUB_TOKEN is not set")
            data = _collect_github(token, args.pr_url)
        elif provider == "bitbucket":
            username = os.environ.get("BITBUCKET_USERNAME")
            app_password = os.environ.get("BITBUCKET_APP_PASSWORD")
            if not username or not app_password:
                raise SystemExit(
                    "BITBUCKET_USERNAME / BITBUCKET_APP_PASSWORD are not set"
                )
            data = _collect_bitbucket(username, app_password, args.pr_url)
        else:
            raise SystemExit(f"Provider '{provider}' is not supported by collect yet.")

        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        n = len(data["threads"])
        print(
            f"Wrote {args.out}: {n} unresolved CodeAnt inline thread(s) on {data['pr_url']}"
        )

    else:  # resolve
        with open(args.resolutions, encoding="utf-8") as fh:
            resolutions = json.load(fh)
        if not isinstance(resolutions, list):
            raise SystemExit(f"{args.resolutions} must contain a JSON array")
        _resolve(provider, args.pr_url, resolutions)


if __name__ == "__main__":
    main()
