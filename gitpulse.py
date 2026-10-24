#!/usr/bin/env python3
"""gitPulse - one-screen health dashboard for all your git repos.

Scans a directory for git repositories and shows branch, dirty state,
ahead/behind, last commit age, and stale branches. Standard library only.
"""

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GREEN, YELLOW, CYAN = "\033[31m", "\033[32m", "\033[33m", "\033[36m"


def git(repo, *args):
    """Run a git command in repo; return stdout or '' on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def find_repos(root, depth):
    """Find git repos under root, up to depth levels, without descending into repos."""
    repos = []

    def walk(path, level):
        if os.path.exists(os.path.join(path, ".git")):
            repos.append(path)
            return
        if level >= depth:
            return
        try:
            entries = sorted(os.scandir(path), key=lambda e: e.name.lower())
        except OSError:
            return
        for e in entries:
            if e.is_dir(follow_symlinks=False) and not e.name.startswith("."):
                walk(e.path, level + 1)

    walk(root, 0)
    return repos


def age(seconds):
    """Format an age in seconds as a short human string."""
    if seconds < 3600:
        return f"{max(seconds // 60, 0)}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    if seconds < 86400 * 60:
        return f"{seconds // 86400}d"
    if seconds < 86400 * 730:
        return f"{seconds // (86400 * 30)}mo"
    return f"{seconds // (86400 * 365)}y"


def inspect(repo, stale_days, fetch):
    """Collect the health info for one repo."""
    if fetch:
        git(repo, "fetch", "--quiet")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    if branch == "HEAD":
        branch = "(detached)"

    staged = modified = untracked = 0
    for line in git(repo, "status", "--porcelain").splitlines():
        if line.startswith("??"):
            untracked += 1
        else:
            if line[0] not in " ?":
                staged += 1
            if line[1] not in " ?":
                modified += 1

    ahead = behind = None
    counts = git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}").split()
    if len(counts) == 2:
        ahead, behind = int(counts[0]), int(counts[1])

    last = git(repo, "log", "-1", "--format=%ct")
    last_age = int(time.time()) - int(last) if last else None

    now = int(time.time())
    stale = []
    for line in git(repo, "for-each-ref", "refs/heads",
                    "--format=%(refname:short) %(committerdate:unix)").splitlines():
        name, _, ts = line.rpartition(" ")
        if name != branch and ts.isdigit() and now - int(ts) > stale_days * 86400:
            stale.append(name)

    return {
        "name": os.path.basename(repo), "branch": branch, "staged": staged,
        "modified": modified, "untracked": untracked, "ahead": ahead,
        "behind": behind, "last_age": last_age, "stale": stale,
        "has_remote": bool(git(repo, "remote")),
    }


def color(text, code, enabled):
    return f"{code}{text}{RESET}" if enabled else text


def render(rows, use_color, only_attention):
    def clean(r):
        return not (r["staged"] or r["modified"] or r["untracked"]
                    or r["ahead"] or r["behind"])

    shown = [r for r in rows if not (only_attention and clean(r))]
    if not shown:
        print(color("All repos clean and in sync.", GREEN, use_color))
        return

    w_name = max(len(r["name"]) for r in shown + [{"name": "REPO"}])
    w_br = max(len(r["branch"]) for r in shown + [{"branch": "BRANCH"}])
    header = f"{'REPO':<{w_name}}  {'BRANCH':<{w_br}}  {'DIRTY':<12} {'SYNC':<11} {'LAST':>5}  STALE"
    print(color(header, BOLD, use_color))

    for r in shown:
        dirty = []
        if r["staged"]:
            dirty.append(f"+{r['staged']}")
        if r["modified"]:
            dirty.append(f"~{r['modified']}")
        if r["untracked"]:
            dirty.append(f"?{r['untracked']}")
        dirty_s = " ".join(dirty) or "clean"
        dirty_c = GREEN if dirty_s == "clean" else YELLOW

        if r["ahead"] is None:
            sync_s, sync_c = ("no remote" if not r["has_remote"] else "no upstream"), DIM
        elif r["ahead"] == r["behind"] == 0:
            sync_s, sync_c = "synced", GREEN
        else:
            sync_s = f"↑{r['ahead']} ↓{r['behind']}"
            sync_c = RED if r["behind"] else YELLOW

        last_s = age(r["last_age"]) if r["last_age"] is not None else "-"
        stale_s = ", ".join(r["stale"][:3]) + (f" +{len(r['stale']) - 3}" if len(r["stale"]) > 3 else "")

        # Pad before colouring so ANSI codes don't break alignment.
        print(
            f"{color(r['name'].ljust(w_name), CYAN, use_color)}  "
            f"{r['branch']:<{w_br}}  "
            f"{color(dirty_s.ljust(12), dirty_c, use_color)} "
            f"{color(sync_s.ljust(11), sync_c, use_color)} "
            f"{last_s:>5}  "
            f"{color(stale_s, DIM, use_color)}"
        )

    dirty_n = sum(1 for r in rows if r["staged"] or r["modified"] or r["untracked"])
    ahead_n = sum(1 for r in rows if r["ahead"])
    behind_n = sum(1 for r in rows if r["behind"])
    stale_n = sum(len(r["stale"]) for r in rows)
    print(f"\n{len(rows)} repos | {dirty_n} dirty | {ahead_n} ahead | {behind_n} behind | {stale_n} stale branches")


def main():
    p = argparse.ArgumentParser(description="Git health dashboard across many repos.")
    p.add_argument("-r", "--repos", nargs="+", metavar="DIR", default=["."],
                   help="one or more directories containing your repos (default: .)")
    p.add_argument("-d", "--depth", type=int, default=2, help="max scan depth (default: 2)")
    p.add_argument("-s", "--stale-days", type=int, default=90, help="days before a branch is stale (default: 90)")
    p.add_argument("-f", "--fetch", action="store_true", help="git fetch each repo first (slower, needs network)")
    p.add_argument("-a", "--attention", action="store_true", help="only show repos needing attention")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    args = p.parse_args()

    repos = []
    for d in args.repos:
        root = os.path.abspath(os.path.expanduser(d))
        if not os.path.isdir(root):
            sys.exit(f"gitpulse: not a directory: {root}")
        repos += [r for r in find_repos(root, args.depth) if r not in repos]
    if not repos:
        sys.exit("gitpulse: no git repositories found in: " + ", ".join(args.repos))

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda r: inspect(r, args.stale_days, args.fetch), repos))

    use_color = sys.stdout.isatty() and not args.no_color
    render(rows, use_color, args.attention)


if __name__ == "__main__":
    main()
