#!/usr/bin/env python3
"""
neural_map.py — an animated "signal map" of your skills, as an SVG.

Concept: instead of a spider/radar chart, your skills are drawn as a small
signal-processing network — a core node, a handful of category nodes, and the
individual tools branching off each one. Thin pulses travel outward from the
core along the connections on a loop, like a live system sending signals to
its subsystems. It's built to fit an embedded/AI/ML identity far better than
a generic radar chart, and it's different enough to stand out.

Data comes from a JSON file you control:
    {
      "core": "Tehzeb",
      "categories": [
        {"label": "Embedded Systems", "tools": ["ESP32", "PIC18F452", "Proteus", "MikroC PRO"]},
        {"label": "AI / ML / CV",     "tools": ["OpenCV", "NumPy", "YOLOv8", "PyWavelets"]},
        {"label": "Full-Stack",       "tools": ["React Native", "Node.js", "Firebase", "PostgreSQL"]},
        {"label": "Languages",        "tools": ["Python", "C", "C++", "JavaScript", "SQL"]}
      ]
    }

Usage:
    python neural_map.py --data skills_map.json -o assets/neural-map
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

PALETTE = {
    "dark":  {"bg": "none", "line": "#334155", "core": "#00F2FE", "core_text": "#0B0F19",
              "cat": "#6366F1", "cat_text": "#F8FAFC", "tool": "#1E293B", "tool_text": "#CBD5E1",
              "tool_border": "#334155", "pulse": "#00F2FE"},
    "light": {"bg": "none", "line": "#CBD5E1", "core": "#0284C7", "core_text": "#FFFFFF",
              "cat": "#4F46E5", "cat_text": "#FFFFFF", "tool": "#F1F5F9", "tool_text": "#334155",
              "tool_border": "#CBD5E1", "pulse": "#0284C7"},
}
FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_w(s: str, size: float) -> float:
    return len(s) * size * 0.58


def render(data: dict, theme: str, size: int = 640) -> str:
    p = PALETTE[theme]
    core_label = data.get("core", "Me")
    categories = data["categories"]
    n_cat = len(categories)
    margin = 150
    canvas = size + margin * 2
    cx, cy = canvas / 2, canvas / 2
    cat_radius = size * 0.30

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas} {canvas}" '
        f'width="{canvas}" height="{canvas}" role="img" aria-label="Skill signal map" '
        f'font-family="{FONT}">',
        "<defs>",
        f'<radialGradient id="coreGlow"><stop offset="0%" stop-color="{p["core"]}" stop-opacity=".55"/>'
        f'<stop offset="100%" stop-color="{p["core"]}" stop-opacity="0"/></radialGradient>',
        "</defs>",
    ]
    if p["bg"] != "none":
        parts.append(f'<rect width="100%" height="100%" fill="{p["bg"]}"/>')

    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{cat_radius*1.5:.0f}" fill="url(#coreGlow)"/>')

    cat_positions = []
    for i, cat in enumerate(categories):
        angle = -math.pi / 2 + i * 2 * math.pi / n_cat
        catx = cx + cat_radius * math.cos(angle)
        caty = cy + cat_radius * math.sin(angle)
        cat_positions.append((catx, caty, angle))

    # Connections: core -> category, with a traveling pulse dot per connection
    for i, (catx, caty, _) in enumerate(cat_positions):
        delay = i * 0.35
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{catx:.1f}" y2="{caty:.1f}" '
            f'stroke="{p["line"]}" stroke-width="1.5"/>'
        )
        parts.append(
            f'<circle r="3.2" fill="{p["pulse"]}">'
            f'<animateMotion dur="2.6s" begin="{delay:.2f}s" repeatCount="indefinite" '
            f'path="M{cx:.1f} {cy:.1f} L{catx:.1f} {caty:.1f}"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.15;.85;1" '
            f'dur="2.6s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
            "</circle>"
        )

    # Category -> tool leaves. Each leaf sits at a slightly larger radius than
    # the last (a fan, not a flat arc) specifically so labels on near-vertical
    # branches (top/bottom categories) don't collide with their neighbors.
    base_leaf_radius = size * 0.16
    radius_step = size * 0.05
    for i, (catx, caty, angle) in enumerate(cat_positions):
        tools = categories[i]["tools"]
        spread = math.radians(105)
        n_tools = len(tools)
        for j, tool in enumerate(tools):
            t = (j - (n_tools - 1) / 2) / max(n_tools - 1, 1) if n_tools > 1 else 0
            leaf_angle = angle + t * spread
            leaf_r = base_leaf_radius + abs(j - (n_tools - 1) / 2) * radius_step
            zigzag = 9 if j % 2 == 0 else -9
            lx = catx + leaf_r * math.cos(leaf_angle)
            ly = caty + leaf_r * math.sin(leaf_angle) + zigzag
            delay = 0.9 + i * 0.35 + j * 0.12
            parts.append(
                f'<line x1="{catx:.1f}" y1="{caty:.1f}" x2="{lx:.1f}" y2="{ly:.1f}" '
                f'stroke="{p["line"]}" stroke-width="1"/>'
            )
            parts.append(
                f'<circle r="2" fill="{p["pulse"]}" opacity="0">'
                f'<animateMotion dur="2.6s" begin="{delay:.2f}s" repeatCount="indefinite" '
                f'path="M{catx:.1f} {caty:.1f} L{lx:.1f} {ly:.1f}"/>'
                f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.15;.85;1" '
                f'dur="2.6s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
                "</circle>"
            )
            tw = text_w(tool, 10.5) + 16
            cos_a = math.cos(leaf_angle)
            if cos_a > 0.25:
                anchor_dx = 8
            elif cos_a < -0.25:
                anchor_dx = -tw - 8
            else:
                anchor_dx = -tw / 2
            parts.append(
                f'<g transform="translate({lx+anchor_dx:.1f} {ly-9:.1f})">'
                f'<rect width="{tw:.0f}" height="18" rx="9" fill="{p["tool"]}" stroke="{p["tool_border"]}"/>'
                f'<text x="{tw/2:.0f}" y="12.5" text-anchor="middle" font-size="10.5" '
                f'fill="{p["tool_text"]}">{esc(tool)}</text></g>'
            )

    # Category nodes (drawn after leaves so they sit on top)
    for i, (catx, caty, _) in enumerate(cat_positions):
        label = categories[i]["label"]
        r = 30
        parts.append(f'<circle cx="{catx:.1f}" cy="{caty:.1f}" r="{r}" fill="{p["cat"]}"/>')
        lines = label.split(" / ") if " / " in label else [label]
        for k, line in enumerate(lines):
            parts.append(
                f'<text x="{catx:.1f}" y="{caty + (k - (len(lines)-1)/2) * 12 + 4:.1f}" '
                f'text-anchor="middle" font-size="10.5" font-weight="700" '
                f'fill="{p["cat_text"]}">{esc(line)}</text>'
            )

    # Core node on top of everything
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="38" fill="{p["core"]}"/>')
    parts.append(
        f'<text x="{cx:.1f}" y="{cy+5:.1f}" text-anchor="middle" font-size="14" '
        f'font-weight="800" fill="{p["core_text"]}">{esc(core_label)}</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--out", type=Path, default=Path("assets/neural-map"))
    ap.add_argument("--size", type=int, default=640)
    args = ap.parse_args(argv)

    data = json.loads(args.data.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        svg = render(data, theme, args.size)
        dest = args.out.with_name(f"{args.out.name}-{theme}.svg")
        dest.write_text(svg, encoding="utf-8")
        print(f"wrote {dest}")


if __name__ == "__main__":
    main()
