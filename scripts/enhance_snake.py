from __future__ import annotations

import argparse
import math
import re
from pathlib import Path


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def enhance(path: Path, contributions: int) -> None:
    svg = path.read_text(encoding="utf-8")
    dark = "dark" in path.name

    match = re.search(r"<svg[^>]*>", svg)
    if not match:
        raise RuntimeError(f"No SVG root found in {path}")

    duration_match = re.search(r"animation:none\s+(\d+)ms", svg)
    duration_ms = int(duration_match.group(1)) if duration_match else 18700
    duration_s = duration_ms / 1000

    # Contribution-driven visual state. The tail grows linearly until the
    # contribution calendar reaches the visual cap, while the particle field
    # becomes denser with the same signal.
    visual_cap = 2500
    energy = clamp(contributions / visual_cap, 0.0, 1.0)
    trail_units = int(120 + (energy * 760))
    particle_count = 3 + int(round(energy * 9))
    meter_steps = 12
    lit_steps = max(1, int(round(energy * meter_steps))) if contributions else 0

    bg = "#020617" if dark else "#f8fafc"
    grid = "#334155" if dark else "#64748b"
    rail = "#22d3ee"
    accent = "#8b5cf6"
    accent2 = "#f472b6"
    hot = "#f59e0b"
    core_fill = "#0f172a" if dark else "#ffffff"

    orbit_particles: list[str] = []
    for index in range(particle_count):
        orbit = "reactorOrbitA" if index % 2 == 0 else "reactorOrbitB"
        color = [rail, accent, accent2, hot][index % 4]
        radius = 2.2 + ((index % 3) * 0.45)
        speed = duration_s * (0.44 + ((index % 5) * 0.055))
        begin = -(duration_s * index / max(1, particle_count))
        orbit_particles.append(
            f'''<circle r="{radius:.2f}" fill="{color}" opacity=".88">
    <animateMotion dur="{speed:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"><mpath href="#{orbit}"/></animateMotion>
    <animate attributeName="opacity" values=".45;1;.45" dur="{2.4 + (index % 4) * .55:.2f}s" repeatCount="indefinite"/>
  </circle>'''
        )

    meter: list[str] = []
    for index in range(meter_steps):
        y = 108 - (index * 8.0)
        active = index < lit_steps
        opacity = 0.85 if active else 0.12
        fill = [rail, accent, accent2, hot][min(3, index // 3)] if active else grid
        meter.append(
            f'<rect x="838" y="{y:.1f}" width="4" height="5" rx="2" fill="{fill}" opacity="{opacity}"/>'
        )

    defs = f'''<defs id="commit-reactor-defs">
  <linearGradient id="snakeRail" x1="0" x2="1">
    <stop offset="0" stop-color="{rail}"/>
    <stop offset=".48" stop-color="{accent}"/>
    <stop offset=".78" stop-color="{accent2}"/>
    <stop offset="1" stop-color="{hot}"/>
  </linearGradient>
  <radialGradient id="snakeBg" cx="50%" cy="48%" r="74%">
    <stop offset="0" stop-color="{accent}" stop-opacity=".13"/>
    <stop offset=".42" stop-color="{rail}" stop-opacity=".055"/>
    <stop offset="1" stop-color="{bg}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="reactorCore" cx="50%" cy="45%" r="62%">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".98"/>
    <stop offset=".16" stop-color="{rail}" stop-opacity=".95"/>
    <stop offset=".48" stop-color="{accent}" stop-opacity=".72"/>
    <stop offset="1" stop-color="{accent2}" stop-opacity="0"/>
  </radialGradient>
  <filter id="snakeGlow" x="-160%" y="-160%" width="420%" height="420%">
    <feGaussianBlur stdDeviation="2.6" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="reactorGlow" x="-180%" y="-180%" width="460%" height="460%">
    <feGaussianBlur stdDeviation="6.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="snakeHudGrid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="{grid}" stroke-opacity=".07" stroke-width="1"/>
  </pattern>
  <path id="snakePerimeter" d="M4 -21H844Q855 -21 855 -10V132Q855 143 844 143H4Q-7 143-7 132V-10Q-7 -21 4 -21Z"/>
  <path id="reactorOrbitA" pathLength="1000" d="M424 56m-206 0a206 61 0 1 0 412 0a206 61 0 1 0-412 0"/>
  <path id="reactorOrbitB" pathLength="1000" d="M424 56m-288 0a288 92 0 1 1 576 0a288 92 0 1 1-576 0" transform="rotate(-8 424 56)"/>
  <path id="handoffIn" d="M816 96C690 132 574 118 424 56"/>
  <path id="handoffOut" d="M424 56C276 2 154 -18 48 -16"/>
</defs>
<g id="commit-reactor-bg" pointer-events="none">
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="{bg}"/>
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="url(#snakeBg)"/>
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="url(#snakeHudGrid)"/>

  <g fill="none" stroke-linecap="round">
    <use href="#reactorOrbitA" stroke="url(#snakeRail)" stroke-width="1.2" stroke-opacity=".24" stroke-dasharray="3 13">
      <animate attributeName="stroke-dashoffset" values="0;-210" dur="5.7s" repeatCount="indefinite"/>
    </use>
    <use href="#reactorOrbitB" stroke="url(#snakeRail)" stroke-width="1" stroke-opacity=".17" stroke-dasharray="2 18">
      <animate attributeName="stroke-dashoffset" values="0;250" dur="8.8s" repeatCount="indefinite"/>
    </use>

    <!-- The luminous trail length is driven by total GitHub contributions. -->
    <use href="#reactorOrbitB" pathLength="1000" stroke="url(#snakeRail)" stroke-width="3.2" stroke-opacity=".78"
         stroke-dasharray="{trail_units} {1000 - trail_units}" filter="url(#snakeGlow)">
      <animate attributeName="stroke-dashoffset" values="0;-1000" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </use>

    <use href="#snakePerimeter" stroke="url(#snakeRail)" stroke-width="1" stroke-opacity=".30" stroke-dasharray="4 14">
      <animate attributeName="stroke-dashoffset" values="0;-180" dur="6s" repeatCount="indefinite"/>
    </use>
  </g>

  <g transform="translate(424 56)" filter="url(#reactorGlow)">
    <circle r="18" fill="url(#reactorCore)" opacity=".28">
      <animate attributeName="r" values="16;24;16" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values=".18;.45;.18" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
    <circle r="5" fill="{core_fill}" stroke="{rail}" stroke-width="1.2"/>
    <circle r="2.4" fill="{rail}"/>
  </g>

  <rect x="-8" y="-16" width="856" height="7" fill="url(#snakeRail)" opacity=".05">
    <animate attributeName="y" values="-16;128;-16" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".02;.13;.02" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
  </rect>

  <g>{''.join(meter)}</g>
</g>'''

    overlay = f'''<g id="commit-reactor-overlay" pointer-events="none">
  <g filter="url(#snakeGlow)">
    {''.join(orbit_particles)}
  </g>

  <!-- Snake -> reactor handoff near the dense end of the generated route. -->
  <path d="M816 96C690 132 574 118 424 56" fill="none" stroke="url(#snakeRail)" stroke-width="1.5"
        stroke-dasharray="6 10" opacity="0">
    <animate attributeName="opacity" values="0;0;.9;.18;0" keyTimes="0;.39;.46;.56;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="stroke-dashoffset" values="90;0;-90" dur="2.2s" repeatCount="indefinite"/>
  </path>
  <circle r="3.2" fill="{hot}" opacity="0" filter="url(#snakeGlow)">
    <animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;.42;.46;.54;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animateMotion dur="{duration_s:.2f}s" repeatCount="indefinite" keyPoints="0;0;1;1" keyTimes="0;.42;.52;1"><mpath href="#handoffIn"/></animateMotion>
  </circle>

  <!-- Reactor -> snake reseed at the end of each cycle. -->
  <path d="M424 56C276 2 154 -18 48 -16" fill="none" stroke="url(#snakeRail)" stroke-width="1.3"
        stroke-dasharray="5 11" opacity="0">
    <animate attributeName="opacity" values="0;0;.75;0" keyTimes="0;.90;.965;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="stroke-dashoffset" values="70;-70" dur="1.8s" repeatCount="indefinite"/>
  </path>
  <circle r="2.8" fill="{rail}" opacity="0" filter="url(#snakeGlow)">
    <animate attributeName="opacity" values="0;0;1;0" keyTimes="0;.91;.965;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animateMotion dur="{duration_s:.2f}s" repeatCount="indefinite" keyPoints="0;0;1;1" keyTimes="0;.91;.975;1"><mpath href="#handoffOut"/></animateMotion>
  </circle>

  <g transform="translate(424 56)" fill="none" filter="url(#snakeGlow)">
    <ellipse rx="42" ry="14" stroke="{rail}" stroke-width="1" opacity=".20" transform="rotate(18)">
      <animate attributeName="rx" values="38;54;38" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </ellipse>
    <ellipse rx="42" ry="14" stroke="{accent2}" stroke-width="1" opacity=".18" transform="rotate(-22)">
      <animate attributeName="ry" values="12;19;12" dur="{duration_s * .82:.2f}s" repeatCount="indefinite"/>
    </ellipse>
  </g>
</g>
<style>
  .s {{ fill:url(#snakeRail) !important; filter:url(#snakeGlow); }}
  .c {{ filter:drop-shadow(0 0 1.2px rgba(34,211,238,.16)); }}
</style>'''

    svg = svg[: match.end()] + defs + svg[match.end() :]
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
