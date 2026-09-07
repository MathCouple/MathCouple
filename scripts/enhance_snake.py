from __future__ import annotations

import argparse
import re
from pathlib import Path


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def snake_route(svg: str) -> str:
    """Build a continuous SVG path from the generated snake-head keyframes."""
    block = re.search(r"@keyframes s0\{(.*?)\}\.s\.s0", svg, re.DOTALL)
    if not block:
        return "M0 -16 L176 0 L80 32 L80 96 L32 96 L16 64 L752 64 L832 80 L816 16 L784 0 L800 64 L800 112 L768 80 L848 80 L848 0 L816 0 L832 32 L784 96 L816 96 L48 32 L48 -16 L0 -16"

    raw_points = re.findall(
        r"transform:translate\((-?\d+(?:\.\d+)?)px,(-?\d+(?:\.\d+)?)px\)",
        block.group(1),
    )

    points: list[tuple[float, float]] = []
    for x_raw, y_raw in raw_points:
        point = (float(x_raw), float(y_raw))
        if not points or point != points[-1]:
            points.append(point)

    if len(points) < 2:
        return "M0 -16 L816 96 L424 56 L48 -16 L0 -16"

    commands = [f"M{points[0][0]:g} {points[0][1]:g}"]
    commands.extend(f"L{x:g} {y:g}" for x, y in points[1:])
    if points[-1] != points[0]:
        commands.append(f"L{points[0][0]:g} {points[0][1]:g}")
    return " ".join(commands)


def enhance(path: Path, contributions: int) -> None:
    svg = path.read_text(encoding="utf-8")
    dark = "dark" in path.name

    match = re.search(r"<svg[^>]*>", svg)
    if not match:
        raise RuntimeError(f"No SVG root found in {path}")

    duration_match = re.search(r"animation:none\s+(\d+)ms", svg)
    duration_ms = int(duration_match.group(1)) if duration_match else 18700
    duration_s = duration_ms / 1000

    # GitHub's rolling contribution total drives the visual mass of the snake.
    # More contributions means a longer physical wake, more orbiting particles,
    # a larger charged arc and a stronger reactor response.
    visual_cap = 2500
    energy = clamp(contributions / visual_cap, 0.0, 1.0)
    tail_segments = 5 + int(round(energy * 31))
    tail_span = 0.055 + (energy * 0.235)  # fraction of one complete snake cycle
    tail_delay = (duration_s * tail_span) / max(1, tail_segments - 1)
    charged_arc = int(105 + (energy * 795))
    particle_count = 4 + int(round(energy * 10))
    meter_steps = 12
    lit_steps = max(1, int(round(energy * meter_steps))) if contributions else 0
    route = snake_route(svg)

    bg = "#020617" if dark else "#f8fafc"
    grid = "#334155" if dark else "#64748b"
    rail = "#22d3ee"
    accent = "#8b5cf6"
    accent2 = "#f472b6"
    hot = "#f59e0b"
    core_fill = "#0f172a" if dark else "#ffffff"

    tail: list[str] = []
    for index in range(tail_segments):
        depth = index / max(1, tail_segments - 1)
        size = 7.8 - (depth * 4.5)
        opacity = 0.92 - (depth * 0.72)
        color = [rail, rail, accent, accent2, hot][min(4, int(depth * 5))]
        begin = -(index * tail_delay)
        pulse = 1.7 + ((index % 5) * 0.19)
        tail.append(
            f'''<rect x="{-size / 2:.2f}" y="{-size / 2:.2f}" width="{size:.2f}" height="{size:.2f}" rx="{max(1.2, size * .34):.2f}" fill="{color}" opacity="{opacity:.3f}" filter="url(#snakeGlow)">
    <animateMotion dur="{duration_s:.2f}s" begin="{begin:.3f}s" repeatCount="indefinite" rotate="auto"><mpath href="#snakeEnergyRoute"/></animateMotion>
    <animate attributeName="opacity" values="{opacity * .48:.3f};{opacity:.3f};{opacity * .48:.3f}" dur="{pulse:.2f}s" begin="{begin:.3f}s" repeatCount="indefinite"/>
  </rect>'''
        )

    orbit_particles: list[str] = []
    for index in range(particle_count):
        orbit = ["reactorOrbitA", "reactorOrbitB", "reactorOrbitC"][index % 3]
        color = [rail, accent, accent2, hot][index % 4]
        radius = 2.0 + ((index % 4) * 0.42)
        speed = duration_s * (0.31 + ((index % 6) * 0.052))
        begin = -(duration_s * index / max(1, particle_count))
        orbit_particles.append(
            f'''<circle r="{radius:.2f}" fill="{color}" opacity=".9" filter="url(#snakeGlow)">
    <animateMotion dur="{speed:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"><mpath href="#{orbit}"/></animateMotion>
    <animate attributeName="r" values="{radius * .72:.2f};{radius * 1.32:.2f};{radius * .72:.2f}" dur="{2.1 + (index % 5) * .43:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/>
  </circle>'''
        )

    meter: list[str] = []
    for index in range(meter_steps):
        y = 108 - (index * 8.0)
        active = index < lit_steps
        opacity = 0.88 if active else 0.10
        fill = [rail, accent, accent2, hot][min(3, index // 3)] if active else grid
        delay = index * .09
        meter.append(
            f'''<rect x="838" y="{y:.1f}" width="4" height="5" rx="2" fill="{fill}" opacity="{opacity}">
    <animate attributeName="opacity" values="{opacity * .45:.3f};{opacity:.3f};{opacity * .45:.3f}" dur="2.4s" begin="-{delay:.2f}s" repeatCount="indefinite"/>
  </rect>'''
        )

    defs = f'''<defs id="commit-reactor-defs">
  <linearGradient id="snakeRail" x1="0" x2="1">
    <stop offset="0" stop-color="{rail}"/>
    <stop offset=".46" stop-color="{accent}"/>
    <stop offset=".78" stop-color="{accent2}"/>
    <stop offset="1" stop-color="{hot}"/>
  </linearGradient>
  <radialGradient id="snakeBg" cx="50%" cy="48%" r="74%">
    <stop offset="0" stop-color="{accent}" stop-opacity=".14"/>
    <stop offset=".42" stop-color="{rail}" stop-opacity=".06"/>
    <stop offset="1" stop-color="{bg}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="reactorCore" cx="50%" cy="45%" r="62%">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".98"/>
    <stop offset=".15" stop-color="{rail}" stop-opacity=".98"/>
    <stop offset=".48" stop-color="{accent}" stop-opacity=".76"/>
    <stop offset=".78" stop-color="{accent2}" stop-opacity=".36"/>
    <stop offset="1" stop-color="{accent2}" stop-opacity="0"/>
  </radialGradient>
  <filter id="snakeGlow" x="-180%" y="-180%" width="460%" height="460%">
    <feGaussianBlur stdDeviation="2.8" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="reactorGlow" x="-220%" y="-220%" width="540%" height="540%">
    <feGaussianBlur stdDeviation="7.2" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="snakeHudGrid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="{grid}" stroke-opacity=".07" stroke-width="1"/>
  </pattern>
  <path id="snakePerimeter" d="M4 -21H844Q855 -21 855 -10V132Q855 143 844 143H4Q-7 143-7 132V-10Q-7 -21 4 -21Z"/>
  <path id="snakeEnergyRoute" d="{route}"/>
  <path id="reactorOrbitA" pathLength="1000" d="M424 56m-206 0a206 61 0 1 0 412 0a206 61 0 1 0-412 0"/>
  <path id="reactorOrbitB" pathLength="1000" d="M424 56m-288 0a288 92 0 1 1 576 0a288 92 0 1 1-576 0" transform="rotate(-8 424 56)"/>
  <path id="reactorOrbitC" pathLength="1000" d="M424 56m-112 0a112 38 0 1 0 224 0a112 38 0 1 0-224 0" transform="rotate(31 424 56)"/>
  <path id="handoffIn" d="M816 96C690 132 574 118 424 56"/>
  <path id="handoffOut" d="M424 56C276 2 154 -18 48 -16"/>
</defs>
<g id="commit-reactor-bg" pointer-events="none">
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="{bg}"/>
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="url(#snakeBg)"/>
  <rect x="-14" y="-30" width="876" height="188" rx="18" fill="url(#snakeHudGrid)"/>

  <g fill="none" stroke-linecap="round">
    <use href="#reactorOrbitA" stroke="url(#snakeRail)" stroke-width="1.25" stroke-opacity=".27" stroke-dasharray="3 13">
      <animate attributeName="stroke-dashoffset" values="0;-210" dur="5.7s" repeatCount="indefinite"/>
    </use>
    <use href="#reactorOrbitB" stroke="url(#snakeRail)" stroke-width="1" stroke-opacity=".18" stroke-dasharray="2 18">
      <animate attributeName="stroke-dashoffset" values="0;250" dur="8.8s" repeatCount="indefinite"/>
    </use>
    <use href="#reactorOrbitC" stroke="url(#snakeRail)" stroke-width="1.2" stroke-opacity=".24" stroke-dasharray="5 11">
      <animate attributeName="stroke-dashoffset" values="0;-160" dur="4.2s" repeatCount="indefinite"/>
    </use>

    <!-- Contribution-driven charged arc: its physical length grows with activity. -->
    <use href="#reactorOrbitB" pathLength="1000" stroke="url(#snakeRail)" stroke-width="3.5" stroke-opacity=".82"
         stroke-dasharray="{charged_arc} {1000 - charged_arc}" filter="url(#snakeGlow)">
      <animate attributeName="stroke-dashoffset" values="0;-1000" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="stroke-width" values="2.6;4.3;2.6" dur="3.6s" repeatCount="indefinite"/>
    </use>

    <use href="#snakePerimeter" stroke="url(#snakeRail)" stroke-width="1" stroke-opacity=".30" stroke-dasharray="4 14">
      <animate attributeName="stroke-dashoffset" values="0;-180" dur="6s" repeatCount="indefinite"/>
    </use>
  </g>

  <!-- This is the real contribution tail. It follows the generated snake route
       and becomes both longer and denser as contribution count increases. -->
  <g id="contribution-tail">{''.join(tail)}</g>

  <g transform="translate(424 56)" filter="url(#reactorGlow)">
    <circle r="18" fill="url(#reactorCore)" opacity=".30">
      <animate attributeName="r" values="16;19;31;20;16" keyTimes="0;.40;.50;.68;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values=".18;.25;.72;.34;.18" keyTimes="0;.40;.50;.68;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
    <circle r="5" fill="{core_fill}" stroke="{rail}" stroke-width="1.2">
      <animate attributeName="stroke-width" values="1.1;2.8;1.1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
    <circle r="2.4" fill="{rail}">
      <animate attributeName="r" values="2.2;4.8;2.2" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
  </g>

  <rect x="-8" y="-16" width="856" height="7" fill="url(#snakeRail)" opacity=".05">
    <animate attributeName="y" values="-16;128;-16" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".02;.13;.02" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
  </rect>

  <g>{''.join(meter)}</g>
</g>'''

    overlay = f'''<g id="commit-reactor-overlay" pointer-events="none">
  <g>{''.join(orbit_particles)}</g>

  <!-- Three continuously precessing electron shells make the reactor feel alive
       even while the generated snake is between dense contribution clusters. -->
  <g transform="translate(424 56)" fill="none" filter="url(#snakeGlow)">
    <g>
      <ellipse rx="49" ry="15" stroke="{rail}" stroke-width="1" opacity=".34"/>
      <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="7.1s" repeatCount="indefinite"/>
    </g>
    <g>
      <ellipse rx="61" ry="19" stroke="{accent}" stroke-width="1" opacity=".26" transform="rotate(58)"/>
      <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="10.4s" repeatCount="indefinite"/>
    </g>
    <g>
      <ellipse rx="38" ry="11" stroke="{accent2}" stroke-width="1" opacity=".30" transform="rotate(-42)"/>
      <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="5.3s" repeatCount="indefinite"/>
    </g>
  </g>

  <!-- Snake -> reactor energy injection. -->
  <path d="M816 96C690 132 574 118 424 56" fill="none" stroke="url(#snakeRail)" stroke-width="1.7"
        stroke-dasharray="6 10" opacity="0">
    <animate attributeName="opacity" values="0;0;.95;.22;0" keyTimes="0;.39;.46;.58;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="stroke-dashoffset" values="110;0;-110" dur="2.1s" repeatCount="indefinite"/>
  </path>
  <circle r="3.5" fill="{hot}" opacity="0" filter="url(#snakeGlow)">
    <animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;.42;.46;.55;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="r" values="2.4;2.4;6;2.4" keyTimes="0;.42;.48;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animateMotion dur="{duration_s:.2f}s" repeatCount="indefinite" keyPoints="0;0;1;1" keyTimes="0;.42;.52;1"><mpath href="#handoffIn"/></animateMotion>
  </circle>

  <!-- Reactor discharge returns energy to the snake start, closing the loop. -->
  <path d="M424 56C276 2 154 -18 48 -16" fill="none" stroke="url(#snakeRail)" stroke-width="1.5"
        stroke-dasharray="5 11" opacity="0">
    <animate attributeName="opacity" values="0;0;.86;.18;0" keyTimes="0;.88;.945;.985;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animate attributeName="stroke-dashoffset" values="90;-90" dur="1.7s" repeatCount="indefinite"/>
  </path>
  <circle r="3.1" fill="{rail}" opacity="0" filter="url(#snakeGlow)">
    <animate attributeName="opacity" values="0;0;1;0" keyTimes="0;.90;.965;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    <animateMotion dur="{duration_s:.2f}s" repeatCount="indefinite" keyPoints="0;0;1;1" keyTimes="0;.90;.975;1"><mpath href="#handoffOut"/></animateMotion>
  </circle>

  <!-- Periodic reactor shockwaves. -->
  <g transform="translate(424 56)" fill="none" stroke="url(#snakeRail)" filter="url(#snakeGlow)">
    <circle r="9" opacity="0">
      <animate attributeName="r" values="9;9;86;86" keyTimes="0;.45;.58;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0;0;.62;0" keyTimes="0;.45;.49;.64" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
    </circle>
    <circle r="7" opacity="0">
      <animate attributeName="r" values="7;7;58;58" keyTimes="0;.91;.98;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0;0;.45;0" keyTimes="0;.91;.95;1" dur="{duration_s:.2f}s" repeatCount="indefinite"/>
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contributions", type=int, default=0)
    parser.add_argument("paths", nargs="+")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for arg in args.paths:
        enhance(Path(arg), max(0, args.contributions))
