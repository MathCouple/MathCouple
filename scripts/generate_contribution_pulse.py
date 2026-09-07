from __future__ import annotations

import argparse
import json
from pathlib import Path


WIDTH = 880
HEIGHT = 170
CELL = 11
GAP = 3
STEP = CELL + GAP
GRID_X = 69
GRID_Y = 38
DURATION = 8.8


def level(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def colors(dark: bool) -> dict[str, object]:
    if dark:
        return {
            "bg": "#0d1117",
            "empty": "#161b22",
            "border": "#30363d",
            "levels": ["#161b22", "#0e7490", "#0891b2", "#06b6d4", "#67e8f9"],
            "pulse": "#22d3ee",
            "accent": "#8b5cf6",
        }
    return {
        "bg": "#ffffff",
        "empty": "#ebedf0",
        "border": "#d0d7de",
        "levels": ["#ebedf0", "#a5f3fc", "#67e8f9", "#22d3ee", "#0891b2"],
        "pulse": "#0891b2",
        "accent": "#7c3aed",
    }


def pulse_key_times(week_index: int, total_weeks: int) -> str:
    position = week_index / max(1, total_weeks - 1)
    before = max(0.0, position - 0.022)
    after = min(1.0, position + 0.028)
    return f"0;{before:.4f};{position:.4f};{after:.4f};1"


def render(data: dict, dark: bool) -> str:
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = int(calendar.get("totalContributions", 0))
    palette = colors(dark)

    # One activity-derived visual variable only: more contributions make the
    # packet wake longer. This keeps the signal meaningful without adding noise.
    activity = min(total / 2500.0, 1.0)
    tail_width = 70 + int(activity * 230)
    scan_width = 18 + int(activity * 18)

    grid_width = max(1, len(weeks) * STEP - GAP)
    grid_height = 7 * STEP - GAP
    end_x = GRID_X + grid_width
    track_y = GRID_Y - 17

    cells: list[str] = []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            weekday = int(day["weekday"])
            count = int(day["contributionCount"])
            x = GRID_X + week_index * STEP
            y = GRID_Y + weekday * STEP
            base_opacity = 0.88 if count else 0.72
            fill = palette["levels"][level(count)]
            key_times = pulse_key_times(week_index, len(weeks))
            peak = 1.0 if count else 0.84
            cells.append(
                f'''<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.2" fill="{fill}" opacity="{base_opacity:.2f}" stroke="{palette['border']}" stroke-opacity=".28" stroke-width=".5">
  <animate attributeName="opacity" values="{base_opacity:.2f};{base_opacity:.2f};{peak:.2f};{base_opacity:.2f};{base_opacity:.2f}" keyTimes="{key_times}" dur="{DURATION}s" repeatCount="indefinite"/>
</rect>'''
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">Animated GitHub contribution pulse</title>
<desc id="desc">A minimal data signal scans the GitHub contribution calendar in an infinite loop.</desc>
<defs>
  <linearGradient id="pulseTail" x1="0" x2="1">
    <stop offset="0" stop-color="{palette['pulse']}" stop-opacity="0"/>
    <stop offset=".72" stop-color="{palette['pulse']}" stop-opacity=".16"/>
    <stop offset="1" stop-color="{palette['accent']}" stop-opacity=".70"/>
  </linearGradient>
  <linearGradient id="scanFade" x1="0" x2="1">
    <stop offset="0" stop-color="{palette['pulse']}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{palette['pulse']}" stop-opacity=".12"/>
    <stop offset="1" stop-color="{palette['pulse']}" stop-opacity="0"/>
  </linearGradient>
  <filter id="softGlow" x="-120%" y="-120%" width="340%" height="340%">
    <feGaussianBlur stdDeviation="3.2" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="{WIDTH}" height="{HEIGHT}" rx="16" fill="{palette['bg']}"/>

<g>{''.join(cells)}</g>

<line x1="{GRID_X}" y1="{track_y}" x2="{end_x}" y2="{track_y}" stroke="{palette['border']}" stroke-width="1" opacity=".55"/>

<g pointer-events="none">
  <rect x="{-tail_width}" y="{track_y - 2.2}" width="{tail_width}" height="4.4" rx="2.2" fill="url(#pulseTail)" filter="url(#softGlow)">
    <animate attributeName="x" values="{-tail_width};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
  </rect>

  <rect x="{-scan_width}" y="{GRID_Y - 3}" width="{scan_width}" height="{grid_height + 6}" fill="url(#scanFade)">
    <animate attributeName="x" values="{-scan_width};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
  </rect>

  <line x1="0" y1="{GRID_Y - 5}" x2="0" y2="{GRID_Y + grid_height + 5}" stroke="{palette['pulse']}" stroke-width="1.35" opacity=".72" filter="url(#softGlow)">
    <animate attributeName="x1" values="{GRID_X};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="x2" values="{GRID_X};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;.75;.75;0" keyTimes="0;.035;.965;1" dur="{DURATION}s" repeatCount="indefinite"/>
  </line>

  <circle cx="{GRID_X}" cy="{track_y}" r="3.6" fill="{palette['pulse']}" filter="url(#softGlow)">
    <animate attributeName="cx" values="{GRID_X};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="r" values="3.1;4.8;3.1" dur="1.45s" repeatCount="indefinite"/>
  </circle>

  <circle cx="{GRID_X}" cy="{track_y}" r="7" fill="none" stroke="{palette['accent']}" stroke-width="1" opacity="0">
    <animate attributeName="cx" values="{GRID_X};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="r" values="4;11;4" dur="1.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".42;0;.42" dur="1.8s" repeatCount="indefinite"/>
  </circle>
</g>

</svg>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Keep the existing filenames so README links never break during rollout.
    (args.output_dir / "github-contribution-grid-snake.svg").write_text(
        render(data, dark=False), encoding="utf-8"
    )
    (args.output_dir / "github-contribution-grid-snake-dark.svg").write_text(
        render(data, dark=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
