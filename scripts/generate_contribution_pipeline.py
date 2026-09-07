from __future__ import annotations

import argparse
import json
from pathlib import Path


WIDTH = 880
HEIGHT = 188
CELL = 10
GAP = 3
STEP = CELL + GAP
GRID_X = 66
GRID_Y = 24
BUS_Y = 151
DURATION = 9.6


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


def palette(dark: bool) -> dict[str, object]:
    if dark:
        return {
            "bg": "#0d1117",
            "empty": "#161b22",
            "border": "#30363d",
            "muted": "#8b949e",
            "levels": ["#161b22", "#0e7490", "#0891b2", "#06b6d4", "#67e8f9"],
            "signal": "#22d3ee",
            "accent": "#8b5cf6",
        }
    return {
        "bg": "#ffffff",
        "empty": "#ebedf0",
        "border": "#d0d7de",
        "muted": "#57606a",
        "levels": ["#ebedf0", "#a5f3fc", "#67e8f9", "#22d3ee", "#0891b2"],
        "signal": "#0891b2",
        "accent": "#7c3aed",
    }


def scan_key_times(week_index: int, total_weeks: int) -> str:
    position = week_index / max(1, total_weeks - 1)
    before = max(0.0, position - 0.018)
    after = min(1.0, position + 0.026)
    return f"0;{before:.4f};{position:.4f};{after:.4f};1"


def render(data: dict, dark: bool) -> str:
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = int(calendar.get("totalContributions", 0))
    p = palette(dark)

    grid_width = max(1, len(weeks) * STEP - GAP)
    grid_height = 7 * STEP - GAP
    end_x = GRID_X + grid_width

    # Activity only changes the amount of material moving through the pipeline.
    # The geometry remains stable, so the animation stays readable at any volume.
    activity = min(total / 2500.0, 1.0)
    cars = 4 + int(round(activity * 12))
    car_spacing_s = 0.085 + activity * 0.035

    cells: list[str] = []
    feeders: list[str] = []
    for week_index, week in enumerate(weeks):
        week_total = sum(int(day["contributionCount"]) for day in week["contributionDays"])
        x = GRID_X + week_index * STEP
        center_x = x + CELL / 2
        intensity = min(1.0, week_total / 20.0)

        if week_total:
            key_times = scan_key_times(week_index, len(weeks))
            feeders.append(
                f'''<line x1="{center_x:.1f}" y1="{GRID_Y + grid_height + 5}" x2="{center_x:.1f}" y2="{BUS_Y - 6}"
  stroke="{p['signal']}" stroke-width="{0.45 + intensity * 0.8:.2f}" opacity="{0.10 + intensity * 0.20:.3f}">
  <animate attributeName="opacity" values=".08;.08;.72;.08;.08" keyTimes="{key_times}" dur="{DURATION}s" repeatCount="indefinite"/>
</line>'''
            )

        for day in week["contributionDays"]:
            weekday = int(day["weekday"])
            count = int(day["contributionCount"])
            y = GRID_Y + weekday * STEP
            fill = p["levels"][level(count)]
            base = 0.80 if count else 0.56
            peak = 1.0 if count else 0.66
            key_times = scan_key_times(week_index, len(weeks))
            cells.append(
                f'''<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}" opacity="{base:.2f}">
  <animate attributeName="opacity" values="{base:.2f};{base:.2f};{peak:.2f};{base:.2f};{base:.2f}" keyTimes="{key_times}" dur="{DURATION}s" repeatCount="indefinite"/>
</rect>'''
            )

    packets: list[str] = []
    travel_start = GRID_X - 22
    travel_end = end_x + 22
    for index in range(cars):
        delay = index * car_spacing_s
        opacity = max(0.28, 0.92 - index * 0.045)
        width = 10.5 - min(index, 7) * 0.25
        color = p["signal"] if index % 4 else p["accent"]
        packets.append(
            f'''<rect x="{travel_start}" y="{BUS_Y - 4}" width="{width:.2f}" height="8" rx="3" fill="{color}" opacity="{opacity:.3f}" filter="url(#glow)">
  <animate attributeName="x" values="{travel_start};{travel_end}" dur="{DURATION}s" begin="-{delay:.3f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;{opacity:.3f};{opacity:.3f};0" keyTimes="0;.04;.96;1" dur="{DURATION}s" begin="-{delay:.3f}s" repeatCount="indefinite"/>
</rect>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">Animated GitHub contribution pipeline</title>
<desc id="desc">A data packet train scans and carries GitHub contribution activity through an infinite pipeline.</desc>
<defs>
  <linearGradient id="bus" x1="0" x2="1">
    <stop offset="0" stop-color="{p['signal']}" stop-opacity=".18"/>
    <stop offset=".48" stop-color="{p['signal']}" stop-opacity=".72"/>
    <stop offset="1" stop-color="{p['accent']}" stop-opacity=".42"/>
  </linearGradient>
  <linearGradient id="scanner" x1="0" x2="1">
    <stop offset="0" stop-color="{p['signal']}" stop-opacity="0"/>
    <stop offset=".55" stop-color="{p['signal']}" stop-opacity=".10"/>
    <stop offset="1" stop-color="{p['signal']}" stop-opacity=".38"/>
  </linearGradient>
  <filter id="glow" x="-120%" y="-120%" width="340%" height="340%">
    <feGaussianBlur stdDeviation="2.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

<rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="{p['bg']}"/>

<!-- Contribution calendar remains the source of truth. -->
<g>{''.join(cells)}</g>

<!-- Active weeks feed the lower transport bus as the scan passes. -->
<g>{''.join(feeders)}</g>

<!-- The scan makes the relationship between calendar activity and packet flow obvious. -->
<g pointer-events="none">
  <rect x="{GRID_X - 24}" y="{GRID_Y - 4}" width="24" height="{grid_height + 8}" fill="url(#scanner)">
    <animate attributeName="x" values="{GRID_X - 24};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
  </rect>
  <line x1="{GRID_X}" y1="{GRID_Y - 6}" x2="{GRID_X}" y2="{GRID_Y + grid_height + 6}"
        stroke="{p['signal']}" stroke-width="1.25" opacity=".72" filter="url(#glow)">
    <animate attributeName="x1" values="{GRID_X};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="x2" values="{GRID_X};{end_x}" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;.78;.78;0" keyTimes="0;.03;.97;1" dur="{DURATION}s" repeatCount="indefinite"/>
  </line>
</g>

<!-- One clean transport rail. Packet count scales with contribution activity. -->
<line x1="{GRID_X - 12}" y1="{BUS_Y}" x2="{end_x + 12}" y2="{BUS_Y}" stroke="{p['border']}" stroke-width="1.1" opacity=".75"/>
<line x1="{GRID_X - 12}" y1="{BUS_Y}" x2="{end_x + 12}" y2="{BUS_Y}" stroke="url(#bus)" stroke-width="1.8" stroke-dasharray="3 15" opacity=".62">
  <animate attributeName="stroke-dashoffset" values="0;-144" dur="3.8s" repeatCount="indefinite"/>
</line>

<g pointer-events="none">{''.join(packets)}</g>

<!-- Output pulse closes the visual cycle before packets wrap to the left. -->
<g transform="translate({end_x + 24} {BUS_Y})" fill="none" stroke="{p['accent']}" filter="url(#glow)">
  <circle r="4" stroke-width="1.2" opacity=".65">
    <animate attributeName="r" values="3;3;13;3" keyTimes="0;.86;.98;1" dur="{DURATION}s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".12;.12;.8;.12" keyTimes="0;.86;.98;1" dur="{DURATION}s" repeatCount="indefinite"/>
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

    (args.output_dir / "contribution-pipeline.svg").write_text(render(data, dark=False), encoding="utf-8")
    (args.output_dir / "contribution-pipeline-dark.svg").write_text(render(data, dark=True), encoding="utf-8")


if __name__ == "__main__":
    main()
