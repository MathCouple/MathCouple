from __future__ import annotations

import re
import sys
from pathlib import Path


def enhance(path: Path) -> None:
    svg = path.read_text(encoding="utf-8")
    dark = "dark" in path.name

    match = re.search(r"<svg[^>]*>", svg)
    if not match:
        raise RuntimeError(f"No SVG root found in {path}")

    duration_match = re.search(r"animation:none\s+(\d+)ms", svg)
    duration_ms = int(duration_match.group(1)) if duration_match else 18700
    duration_s = duration_ms / 1000

    bg = "#020617" if dark else "#f8fafc"
    grid = "#334155" if dark else "#94a3b8"
    rail = "#22d3ee"
    accent = "#a855f7"
    accent2 = "#f472b6"

    defs = f'''<defs id="profile-telemetry-defs">
  <linearGradient id="snakeRail" x1="0" x2="1">
    <stop offset="0" stop-color="{rail}"/>
    <stop offset=".5" stop-color="{accent}"/>
    <stop offset="1" stop-color="{accent2}"/>
  </linearGradient>
  <radialGradient id="snakeBg" cx="50%" cy="50%" r="75%">
    <stop offset="0" stop-color="{accent}" stop-opacity=".09"/>
    <stop offset=".55" stop-color="{rail}" stop-opacity=".04"/>
    <stop offset="1" stop-color="{bg}" stop-opacity="0"/>
  </radialGradient>
  <filter id="snakeGlow" x="-150%" y="-150%" width="400%" height="400%">
    <feGaussianBlur stdDeviation="2.4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="snakeSoftGlow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="5"/>
  </filter>
  <pattern id="snakeHudGrid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="{grid}" stroke-opacity=".08" stroke-width="1"/>
  </pattern>
  <path id="snakePerimeter" d="M4 -21H844Q855 -21 855 -10V132Q855 143 844 143H4Q-7 143-7 132V-10Q-7 -21 4 -21Z"/>
</defs>
<g id="profile-telemetry-bg" pointer-events="none">
  <rect x="-14" y="-30" width="876" height="188" rx="16" fill="{bg}"/>
  <rect x="-14" y="-30" width="876" height="188" rx="16" fill="url(#snakeBg)"/>
  <rect x="-14" y="-30" width="876" height="188" rx="16" fill="url(#snakeHudGrid)"/>
  <use href="#snakePerimeter" fill="none" stroke="url(#snakeRail)" stroke-width="1.2" stroke-opacity=".45" stroke-dasharray="4 14">
    <animate attributeName="stroke-dashoffset" values="0;-180" dur="6s" repeatCount="indefinite"/>
  </use>
  <path d="M8 -13H840" stroke="url(#snakeRail)" stroke-opacity=".22" stroke-width="1" stroke-dasharray="2 18">
    <animate attributeName="stroke-dashoffset" values="0;-140" dur="4.5s" repeatCount="indefinite"/>
  </path>
  <path d="M8 135H840" stroke="url(#snakeRail)" stroke-opacity=".18" stroke-width="1" stroke-dasharray="2 18">
    <animate attributeName="stroke-dashoffset" values="0;140" dur="4.5s" repeatCount="indefinite"/>
  </path>
  <rect x="-8" y="-16" width="856" height="8" fill="url(#snakeRail)" opacity=".05">
    <animate attributeName="y" values="-16;128;-16" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".03;.15;.03" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
  </rect>
</g>'''

    overlay = f'''<g id="profile-telemetry-overlay" pointer-events="none" filter="url(#snakeGlow)">
  <circle r="2.8" fill="{rail}">
    <animateMotion dur="{duration_s:.2f}s" repeatCount="indefinite"><mpath href="#snakePerimeter"/></animateMotion>
  </circle>
  <circle r="2.2" fill="{accent2}">
    <animateMotion dur="{duration_s * 0.74:.2f}s" begin="-3.2s" repeatCount="indefinite"><mpath href="#snakePerimeter"/></animateMotion>
  </circle>
  <g transform="translate(0 -16)">
    <circle r="4" fill="none" stroke="{rail}" stroke-width="1.2" opacity=".7">
      <animate attributeName="r" values="4;12;4" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values=".9;0;.9" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
  </g>
  <g transform="translate(816 96)">
    <circle r="4" fill="none" stroke="{accent}" stroke-width="1.2" opacity=".7">
      <animate attributeName="r" values="4;4;13;4" keyTimes="0;.42;.48;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values=".3;.3;1;.3" keyTimes="0;.42;.48;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
  </g>
  <g transform="translate(48 -16)">
    <circle r="4" fill="none" stroke="{accent2}" stroke-width="1.2" opacity=".7">
      <animate attributeName="r" values="4;4;14;4" keyTimes="0;.94;.98;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values=".25;.25;1;.25" keyTimes="0;.94;.98;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
  </g>
</g>
<style>
  .s {{ fill:url(#snakeRail) !important; filter:url(#snakeGlow); }}
  .c {{ filter:drop-shadow(0 0 1.2px rgba(34,211,238,.16)); }}
</style>'''

    svg = svg[: match.end()] + defs + svg[match.end() :]
    svg = svg.replace("</svg>", overlay + "</svg>")
    path.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: enhance_snake.py <svg> [<svg> ...]")
    for arg in sys.argv[1:]:
        enhance(Path(arg))
