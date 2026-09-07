from __future__ import annotations

import argparse
import re
from pathlib import Path


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def snake_route(svg: str) -> str:
    """Extract the generated snake-head route and expose it as one SVG path."""
    block = re.search(r"@keyframes s0\{(.*?)\}\.s\.s0", svg, re.DOTALL)
    if not block:
        return (
            "M0 -16 L176 0 L176 32 L80 32 L80 96 L32 96 L32 80 "
            "L16 80 L16 64 L752 64 L752 80 L832 80 L832 48 L816 48 "
            "L816 16 L800 16 L800 0 L784 0 L784 16 L800 48 L784 48 "
            "L784 64 L800 64 L800 112 L768 112 L768 80 L848 80 L848 0 "
            "L816 0 L832 16 L832 32 L816 32 L816 64 L784 96 L816 96 "
            "L48 32 L48 -16 L0 -16"
        )

    points: list[tuple[float, float]] = []
    for x_raw, y_raw in re.findall(
        r"transform:translate\((-?\d+(?:\.\d+)?)px,(-?\d+(?:\.\d+)?)px\)",
        block.group(1),
    ):
        point = (float(x_raw), float(y_raw))
        if not points or point != points[-1]:
            points.append(point)

    if len(points) < 2:
        return "M0 -16 L816 96 L48 -16 L0 -16"

    commands = [f"M{points[0][0]:g} {points[0][1]:g}"]
    commands.extend(f"L{x:g} {y:g}" for x, y in points[1:])
    if points[-1] != points[0]:
        commands.append(f"L{points[0][0]:g} {points[0][1]:g}")
    return " ".join(commands)


def enhance(path: Path, contributions: int) -> None:
    svg = path.read_text(encoding="utf-8")
    dark = "dark" in path.name

    root = re.search(r"<svg[^>]*>", svg)
    if not root:
        raise RuntimeError(f"No SVG root found in {path}")

    duration_match = re.search(r"animation:none\s+(\d+)ms", svg)
    duration_ms = int(duration_match.group(1)) if duration_match else 18700
    duration_s = duration_ms / 1000

    # A single visual variable is derived from GitHub activity: the moving wake.
    # More contributions produce a longer trail, but the composition stays sparse.
    visual_cap = 2500
    energy = clamp(contributions / visual_cap, 0.0, 1.0)
    tail_length = int(110 + (energy * 690))
    tail_gap = 1000 - tail_length
    tail_width = 1.7 + (energy * 1.1)
    route = snake_route(svg)

    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    muted = "#8b949e" if dark else "#57606a"
    rail = "#22d3ee"
    accent = "#8b5cf6"

    defs_and_background = f'''<defs id="signal-trail-defs">
  <linearGradient id="signalGradient" x1="0" x2="1">
    <stop offset="0" stop-color="{rail}"/>
    <stop offset=".55" stop-color="{accent}"/>
    <stop offset="1" stop-color="{rail}"/>
  </linearGradient>
  <filter id="signalGlow" x="-180%" y="-180%" width="460%" height="460%">
    <feGaussianBlur stdDeviation="2.4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="signalSoft" x="-120%" y="-120%" width="340%" height="340%">
    <feGaussianBlur stdDeviation="5"/>
  </filter>
  <path id="snakeSignalRoute" pathLength="1000" d="{route}"/>
  <path id="topRail" pathLength="1000" d="M10 -20 H838"/>
  <path id="bottomRail" pathLength="1000" d="M10 138 H838"/>
</defs>
<g id="signal-trail-background" pointer-events="none">
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="{bg}"/>
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="none" stroke="{border}" stroke-width="1" opacity=".72"/>

  <use href="#snakeSignalRoute" fill="none" stroke="{muted}" stroke-width="1" stroke-opacity=".075"/>

  <use href="#snakeSignalRoute" pathLength="1000" fill="none" stroke="url(#signalGradient)"
       stroke-width="{tail_width + 4:.2f}" stroke-opacity=".10" stroke-linecap="round"
       stroke-dasharray="{tail_length} {tail_gap}" filter="url(#signalSoft)">
    <animate attributeName="stroke-dashoffset" values="1000;0" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".02;.12;.12;.02" keyTimes="0;.06;.94;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
  </use>

  <use href="#snakeSignalRoute" pathLength="1000" fill="none" stroke="url(#signalGradient)"
       stroke-width="{tail_width:.2f}" stroke-opacity=".52" stroke-linecap="round"
       stroke-dasharray="{tail_length} {tail_gap}" filter="url(#signalGlow)">
    <animate attributeName="stroke-dashoffset" values="1000;0" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".08;.62;.62;.08" keyTimes="0;.06;.94;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
  </use>

  <g fill="none" stroke="{muted}" stroke-width="1" opacity=".18">
    <use href="#topRail" stroke-dasharray="2 24">
      <animate attributeName="stroke-dashoffset" values="0;-104" dur="6.5s" repeatCount="indefinite"/>
    </use>
    <use href="#bottomRail" stroke-dasharray="2 24">
      <animate attributeName="stroke-dashoffset" values="0;104" dur="6.5s" repeatCount="indefinite"/>
    </use>
  </g>

  <rect x="-10" y="-18" width="868" height="2" fill="url(#signalGradient)" opacity=".03">
    <animate attributeName="y" values="-18;136;-18" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".02;.11;.02" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
  </rect>
</g>'''

    overlay = f'''<g id="signal-trail-overlay" pointer-events="none">
  <circle r="3.2" fill="{rail}" filter="url(#signalGlow)">
    <animateMotion dur="{duration_s:.2f}s" repeatCount="indefinite"><mpath href="#snakeSignalRoute"/></animateMotion>
    <animate attributeName="r" values="2.4;4.2;2.4" dur="2.2s" repeatCount="indefinite"/>
  </circle>

  <circle r="2.4" fill="{accent}" opacity=".72" filter="url(#signalGlow)">
    <animateMotion dur="7.4s" repeatCount="indefinite"><mpath href="#topRail"/></animateMotion>
  </circle>
  <circle r="2.4" fill="{rail}" opacity=".72" filter="url(#signalGlow)">
    <animateMotion dur="8.1s" begin="-3.2s" repeatCount="indefinite"><mpath href="#bottomRail"/></animateMotion>
  </circle>
</g>
<style>
  .s {{ fill:url(#signalGradient) !important; filter:url(#signalGlow); }}
  .c {{ filter:drop-shadow(0 0 1px rgba(34,211,238,.12)); }}
</style>'''

    svg = svg[: root.end()] + defs_and_background + svg[root.end() :]
    svg = svg.replace("</svg>", overlay + "</svg>")
    path.write_text(svg, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contributions", type=int, default=0)
    parser.add_argument("paths", nargs="+")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for arg in args.paths:
        enhance(Path(arg), max(0, args.contributions))
