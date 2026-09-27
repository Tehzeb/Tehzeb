#!/usr/bin/env python3
"""
stat_cards.py — self-hosted GitHub stat + repo cards, rendered as SVG.

Why this exists: shared public card generators (the ones everyone points their
README at) get rate-limited under load and occasionally go down entirely, and
when they do, that whole section of your profile goes with them. This script
draws the same kind of card, but from your own repo, using the plain GitHub
REST API — so it renders exactly as often as GitHub itself renders.

Usage:
    python stat_cards.py --user Tehzeb --out assets

Writes:
    assets/stat-card-dark.svg   / stat-card-light.svg
    assets/repo-card-<name>-dark.svg / -light.svg   (top starred, non-fork repos)

A token in $GITHUB_TOKEN raises the rate limit and is required for anything
beyond public REST data (this script does not need GraphQL / contribution
streaks — see the note in build_tiles()).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

UA = {"User-Agent": "stat-cards-script"}

PALETTE = {
    "dark":  {"bg": "#0B0F19", "card": "#111827", "border": "#1F2937",
              "title": "#00F2FE", "text": "#E5E7EB", "muted": "#94A3B8", "accent": "#6366F1"},
    "light": {"bg": "#F8FAFC", "card": "#FFFFFF", "border": "#E2E8F0",
              "title": "#0284C7", "text": "#0F172A", "muted": "#64748B", "accent": "#4F46E5"},
}

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"


def api(path: str, token: str | None):
    req = urllib.request.Request("https://api.github.com" + path, headers=dict(UA))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def card_shell(w: int, h: int, theme: str, body: str, label: str) -> str:
    p = PALETTE[theme]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{esc(label)}" font-family="{FONT}">'
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="{p["card"]}" '
        f'stroke="{p["border"]}"/>{body}</svg>'
    )


def build_tiles(user: str, token: str | None) -> list[tuple[str, str]]:
    profile = api(f"/users/{user}", token)
    repos, page = [], 1
    while True:
        batch = api(f"/users/{user}/repos?per_page=100&page={page}&type=owner", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    owned = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in owned)
    langs = {}
    for r in owned:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1

    # Contribution streak/total needs the GraphQL API (a token with no extra
    # scope works fine for that too) — kept out of this script on purpose so it
    # works with zero setup; add it later the same way the profile repo's
    # Action already authenticates if you want those tiles back.
    return [
        ("Public repos", f"{profile['public_repos']:,}"),
        ("Total stars", f"{stars:,}"),
        ("Followers", f"{profile['followers']:,}"),
        ("Languages used", f"{len(langs):,}"),
    ], owned


def render_stats(user: str, tiles: list[tuple[str, str]], theme: str) -> str:
    p = PALETTE[theme]
    pad, cols, tile_w, tile_h = 22, 2, 210, 60
    rows = (len(tiles) + cols - 1) // cols
    W = pad * 2 + cols * tile_w
    H = pad * 2 + 34 + rows * tile_h
    out = [
        f'<text x="{pad}" y="{pad+16}" font-size="15" font-weight="700" fill="{p["title"]}">'
        f'{esc(user)} · GitHub Stats</text>',
        f'<line x1="{pad}" y1="{pad+28}" x2="{W-pad}" y2="{pad+28}" stroke="{p["border"]}"/>',
    ]
    top = pad + 50
    for i, (label, value) in enumerate(tiles):
        cx = pad + (i % cols) * tile_w
        cy = top + (i // cols) * tile_h
        out.append(f'<text x="{cx}" y="{cy}" font-size="24" font-weight="700" '
                    f'fill="{p["text"]}">{esc(value)}</text>')
        out.append(f'<text x="{cx}" y="{cy+18}" font-size="11" fill="{p["muted"]}">'
                    f'{esc(label)}</text>')
    return card_shell(W, H, theme, "".join(out), f"{user} GitHub statistics")


def render_repo(repo: dict, theme: str) -> str:
    p = PALETTE[theme]
    W, H, pad = 380, 120, 18
    name = repo["name"]
    desc = (repo.get("description") or "No description yet.")[:90]
    out = [
        f'<text x="{pad}" y="{pad+14}" font-size="14" font-weight="700" fill="{p["title"]}">'
        f'{esc(name)}</text>',
        f'<text x="{pad}" y="{pad+36}" font-size="11.5" fill="{p["text"]}">{esc(desc)}</text>',
        f'<text x="{pad}" y="{H-pad}" font-size="11" fill="{p["muted"]}">'
        f'★ {repo["stargazers_count"]}&#160;&#160;⑂ {repo["forks_count"]}'
        + (f'&#160;&#160;{esc(repo["language"])}' if repo.get("language") else "")
        + "</text>",
    ]
    return card_shell(W, H, theme, "".join(out), f"{name} repository card")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", type=Path, default=Path("assets"))
    ap.add_argument("--top-repos", type=int, default=3)
    args = ap.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    args.out.mkdir(parents=True, exist_ok=True)

    tiles, owned = build_tiles(args.user, token)
    for theme in ("dark", "light"):
        dest = args.out / f"stat-card-{theme}.svg"
        dest.write_text(render_stats(args.user, tiles, theme), encoding="utf-8")
        print(f"wrote {dest}")

    top = sorted(owned, key=lambda r: -r["stargazers_count"])[: args.top_repos]
    for repo in top:
        for theme in ("dark", "light"):
            dest = args.out / f"repo-card-{repo['name']}-{theme}.svg"
            dest.write_text(render_repo(repo, theme), encoding="utf-8")
        print(f"wrote repo-card-{repo['name']}-*.svg")

    if not top:
        print("note: no public repos found to make repo cards for yet — "
              "stat card was still generated", file=sys.stderr)


if __name__ == "__main__":
    main()
