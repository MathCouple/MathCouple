from __future__ import annotations

import argparse
import json
from pathlib import Path


WIDTH = 880
HEIGHT = 176
CELL = 10
GAP = 3
STEP = CELL + GAP
GRID_X = 66
GRID_Y = 33
DURATION = 10.5


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
            "levels": ["#161b22", "#0e7490", "#0891b2", "#06b6d4", "#67e8f9"],
            "signal": "#22d3ee",
            "accent": "#8b5cf6",
            "muted": "#8b949e",
        }
    return {
        "bg": "#ffffff",
        "empty": "#ebedf0",
        "border": "#d0d7de",
        "levels": ["#ebedf0", "#a5f3fc", "#67e8f9", "#22d3ee", "#0891b2"],
        "signal": "#0891b2",
        "accent": "#7c3aed",
        "muted": "#57606a",
    }


def activity_points(weeks: list[dict]) -> list[tuple[float, float]]:
    """Build one point per week using the activity center of mass for that week."""
    middle_y = GRID_Y + (3 * STEP) + CELL / 2
    raw: list[tuple[float, float]] = []
    last_y = middle_y

    for week_index, week in enumerate(weeks):
        x = GRID_X + week_index * STEP + CELL / 2
        weighted_sum = 0.0
        total = 0
        for day in week["contributionDays"]:
            count = int(day["contributionCount"])
            if count <= 0:
                continue
            weekday = int(day["weekday"])
            weighted_sum += (GRID_Y + weekday * STEP + CELL / 2) * count
            total += count

        if total:
            last_y = weighted_sum / total
        raw.append((x, last_y))

    # A small smoothing pass keeps the signal organic without detaching it from
    # the contribution data that defines each weekly anchor.
    smooth: list[tuple[float, float]] = []
    for index, (x, y) in enumerate(raw):
        start = max(0, index - 1)
        end = min(len(raw), index + 2)
        avg_y = sum(raw[j][1] for j in range(start, end)) / (end - start)
        smooth.append((x, avg_y))
    return smooth


def smooth_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return f"M{GRID_X} {GRID_Y + 3 * STEP}"
    if len(points) == 1:
        return f"M{points[0][0]:.1f} {points[0][1]:.1f}"

    commands = [f"M{points[0][0]:.1f} {points[0][1]:.1f}"]
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        mid_x = (x0 + x1) / 2
        commands.append(
            f"C{mid_x:.1f} {y0:.1f} {mid_x:.1f} {y1:.1f} {x1:.1f} {y1:.1f}"
        )
    return " ".join(commands)


def render(data: dict, dark: bool) -> str:
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = int(calendar.get("totalContributions", 0))
    p = palette(dark)

    grid_width = max(1, len(weeks) * STEP - GAP)
    grid_height = 7 * STEP - GAP

    activity = min(total / 2500.0, 1.0)
    tail_length = int(130 + activity * 390)
    trail_width = 1.7 + activity * 1.15
    points = activity_points(weeks)
    route = smooth_path(points)

    cells: list[str] = []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            weekday = int(day["weekday"])
            count = int(day["contributionCount"])
            x = GRID_X + week_index * STEP
            y = GRID_Y + weekday * STEP
            fill = p["levels"][level(count)]
            opacity = 0.92 if count else 0.58
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}" opacity="{opacity:.2f}"/>'
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">Animated GitHub contribution heartbeat</title>
<desc id="desc">An ECG-like pulse follows the weekly center of GitHub contribution activity. Its visible wake grows with contribution volume.</desc>
<defs>
  <linearGradient id="current" x1="0" x2="1">
    <stop offset="0" stop-color="{p['signal']}"/>
    <stop offset=".55" stop-color="{p['accent']}"/>
    <stop offset="1" stop-color="{p['signal']}"/>
  </linearGradient>
  <filter id="glow" x="-180%" y="-180%" width="460%" height="460%">
    <feGaussianBlur stdDeviation="2.3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="soft" x="-120%" y="-120%" width="340%" height="340%">
    <feGaussianBlur stdDeviation="5.2"/>
  </filter>
  <path id="activityPath" pathLength="1000" d="{route}"/>
</defs>

<rect width="{WIDTH}" height="{HEIGHT}" rx="14" fill="{p['bg']}"/>
<rect x="{GRID_X - 12}" y="{GRID_Y - 12}" width="{grid_width + 24}" height="{grid_height + 24}" rx="12"
      fill="none" stroke="{p['border']}" stroke-width="1" opacity=".34"/>

<g>{''.join(cells)}</g>

<!-- Only the moving wake reveals the data-derived route. -->
<use href="#activityPath" pathLength="1000" fill="none" stroke="url(#current)"
     stroke-width="{trail_width + 4.8:.2f}" stroke-linecap="round" stroke-opacity=".10"
     stroke-dasharray="{tail_length} {1000 - tail_length}" filter="url(#soft)">
  <animate attributeName="stroke-dashoffset" values="0;-1000" dur="{DURATION}s" repeatCount="indefinite"/>
</use>
<use href="#activityPath" pathLength="1000" fill="none" stroke="url(#current)"
     stroke-width="{trail_width:.2f}" stroke-linecap="round" stroke-opacity=".72"
     stroke-dasharray="{tail_length} {1000 - tail_length}" filter="url(#glow)">
  <animate attributeName="stroke-dashoffset" values="0;-1000" dur="{DURATION}s" repeatCount="indefinite"/>
</use>

<!-- One moving pulse makes direction immediately readable without exposing the full route. -->
<g filter="url(#glow)">
  <circle r="4.1" fill="{p['signal']}">
    <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="auto"><mpath href="#activityPath"/></animateMotion>
    <animate attributeName="r" values="3.5;4.8;3.5" dur="1.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.025;.975;1" dur="{DURATION}s" repeatCount="indefinite"/>
  </circle>
  <circle r="9" fill="none" stroke="{p['accent']}" stroke-width="1" opacity=".32">
    <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="auto"><mpath href="#activityPath"/></animateMotion>
    <animate attributeName="r" values="6;12;6" dur="2.15s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;.34;.34;0" keyTimes="0;.025;.975;1" dur="{DURATION}s" repeatCount="indefinite"/>
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
    (args.output_dir / "activity-current.svg").write_text(render(data, dark=False), encoding="utf-8")
    (args.output_dir / "activity-current-dark.svg").write_text(render(data, dark=True), encoding="utf-8")


if __name__ == "__main__":
    main()
