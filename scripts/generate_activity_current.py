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
DURATION = 12.5
SCAN_END = 0.78
HOLD_END = 0.90
RESET_END = 0.99

FONT = {
    "M": [
        "10001",
        "11011",
        "10101",
        "10101",
        "10001",
        "10001",
        "10001",
    ],
    "A": [
        "01110",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ],
    "L": [
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "10000",
        "11111",
    ],
    "V": [
        "10001",
        "10001",
        "10001",
        "10001",
        "10001",
        "01010",
        "00100",
    ],
    "E": [
        "11111",
        "10000",
        "10000",
        "11110",
        "10000",
        "10000",
        "11111",
    ],
    "S": [
        "01111",
        "10000",
        "10000",
        "01110",
        "00001",
        "00001",
        "11110",
    ],
}


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
        }
    return {
        "bg": "#ffffff",
        "empty": "#ebedf0",
        "border": "#d0d7de",
        "levels": ["#ebedf0", "#a5f3fc", "#67e8f9", "#22d3ee", "#0891b2"],
        "signal": "#0891b2",
        "accent": "#7c3aed",
    }


def activity_points(weeks: list[dict]) -> list[tuple[float, float]]:
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

    smooth: list[tuple[float, float]] = []
    for index, (x, _) in enumerate(raw):
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


def malves_targets() -> list[tuple[float, float]]:
    word = "MALVES"
    target_cell = 8
    pitch = 10
    letter_width = (5 * pitch) - (pitch - target_cell)
    letter_gap = 8
    total_width = len(word) * letter_width + (len(word) - 1) * letter_gap
    total_height = (7 * pitch) - (pitch - target_cell)
    start_x = (WIDTH - total_width) / 2
    start_y = (HEIGHT - total_height) / 2

    targets: list[tuple[float, float]] = []
    for letter_index, letter in enumerate(word):
        letter_x = start_x + letter_index * (letter_width + letter_gap)
        for row, pattern in enumerate(FONT[letter]):
            for col, bit in enumerate(pattern):
                if bit == "1":
                    targets.append((letter_x + col * pitch, start_y + row * pitch))

    # Assemble the word from left to right as the heartbeat advances.
    targets.sort(key=lambda point: (point[0], point[1]))
    return targets


def render(data: dict, dark: bool) -> str:
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = int(calendar.get("totalContributions", 0))
    p = palette(dark)

    grid_width = max(1, len(weeks) * STEP - GAP)
    grid_height = 7 * STEP - GAP

    activity = min(total / 2500.0, 1.0)
    tail_length = int(120 + activity * 330)
    trail_width = 1.6 + activity * 1.0
    route = smooth_path(activity_points(weeks))

    source_cells: list[dict[str, object]] = []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            weekday = int(day["weekday"])
            count = int(day["contributionCount"])
            source_cells.append(
                {
                    "week": week_index,
                    "weekday": weekday,
                    "count": count,
                    "x": GRID_X + week_index * STEP,
                    "y": GRID_Y + weekday * STEP,
                }
            )

    targets = malves_targets()
    selected: dict[int, tuple[float, float]] = {}
    if targets and source_cells:
        for target_index, target in enumerate(targets):
            source_index = round(
                target_index * (len(source_cells) - 1) / max(1, len(targets) - 1)
            )
            selected[source_index] = target

    cells: list[str] = []
    total_weeks = max(1, len(weeks) - 1)

    for source_index, cell in enumerate(source_cells):
        week_index = int(cell["week"])
        count = int(cell["count"])
        x = float(cell["x"])
        y = float(cell["y"])
        fill = str(p["levels"][level(count)])
        base_opacity = 0.92 if count else 0.58

        pass_time = 0.02 + (week_index / total_weeks) * (SCAN_END - 0.08)
        settle_time = min(pass_time + 0.055, SCAN_END)

        if source_index in selected:
            target_x, target_y = selected[source_index]
            target_fill = str(p["accent"] if level(count) >= 4 else p["signal"])
            cells.append(
                f'''<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}" opacity="{base_opacity:.2f}">
  <animate attributeName="x" values="{x:.1f};{x:.1f};{target_x:.1f};{target_x:.1f};{x:.1f};{x:.1f}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="y" values="{y:.1f};{y:.1f};{target_y:.1f};{target_y:.1f};{y:.1f};{y:.1f}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="width" values="{CELL};{CELL};8;8;{CELL};{CELL}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="height" values="{CELL};{CELL};8;8;{CELL};{CELL}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="fill" values="{fill};{fill};{target_fill};{target_fill};{fill};{fill}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="{base_opacity:.2f};{base_opacity:.2f};1;1;{base_opacity:.2f};{base_opacity:.2f}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
</rect>'''
            )
        else:
            cells.append(
                f'''<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}" opacity="{base_opacity:.2f}">
  <animate attributeName="opacity" values="{base_opacity:.2f};{base_opacity:.2f};.10;.10;{base_opacity:.2f};{base_opacity:.2f}" keyTimes="0;{pass_time:.4f};{settle_time:.4f};{HOLD_END:.4f};{RESET_END:.4f};1" dur="{DURATION}s" repeatCount="indefinite"/>
</rect>'''
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity heartbeat assembling MALVES</title>
<desc id="desc">A heartbeat follows GitHub contribution activity. As it passes, contribution cells reorganize into MALVES at the center before returning to the calendar for the next cycle.</desc>
<defs>
  <linearGradient id="current" x1="0" x2="1">
    <stop offset="0" stop-color="{p['signal']}"/>
    <stop offset=".55" stop-color="{p['accent']}"/>
    <stop offset="1" stop-color="{p['signal']}"/>
  </linearGradient>
  <linearGradient id="assemblySweep" x1="0" x2="1">
    <stop offset="0" stop-color="{p['signal']}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{p['signal']}" stop-opacity=".18"/>
    <stop offset="1" stop-color="{p['accent']}" stop-opacity="0"/>
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

<!-- The heartbeat is the only thing that reveals the otherwise hidden route. -->
<use href="#activityPath" pathLength="1000" fill="none" stroke="url(#current)"
     stroke-width="{trail_width + 4.8:.2f}" stroke-linecap="round" stroke-opacity=".10"
     stroke-dasharray="{tail_length} {1000 - tail_length}" filter="url(#soft)">
  <animate attributeName="stroke-dashoffset" values="0;-1000;-1000;0" keyTimes="0;{SCAN_END:.2f};{HOLD_END:.2f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values=".10;.10;0;0;.10" keyTimes="0;{SCAN_END - .02:.2f};{SCAN_END + .03:.2f};{RESET_END:.2f};1" dur="{DURATION}s" repeatCount="indefinite"/>
</use>
<use href="#activityPath" pathLength="1000" fill="none" stroke="url(#current)"
     stroke-width="{trail_width:.2f}" stroke-linecap="round" stroke-opacity=".72"
     stroke-dasharray="{tail_length} {1000 - tail_length}" filter="url(#glow)">
  <animate attributeName="stroke-dashoffset" values="0;-1000;-1000;0" keyTimes="0;{SCAN_END:.2f};{HOLD_END:.2f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values=".72;.72;0;0;.72" keyTimes="0;{SCAN_END - .02:.2f};{SCAN_END + .03:.2f};{RESET_END:.2f};1" dur="{DURATION}s" repeatCount="indefinite"/>
</use>

<g filter="url(#glow)">
  <circle r="4.1" fill="{p['signal']}">
    <animateMotion dur="{DURATION}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1;0" keyTimes="0;{SCAN_END:.2f};{SCAN_END + .03:.2f};1"><mpath href="#activityPath"/></animateMotion>
    <animate attributeName="r" values="3.5;4.8;3.5" dur="1.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.025;{SCAN_END - .01:.2f};{SCAN_END + .03:.2f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  </circle>
  <circle r="9" fill="none" stroke="{p['accent']}" stroke-width="1" opacity=".32">
    <animateMotion dur="{DURATION}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1;0" keyTimes="0;{SCAN_END:.2f};{SCAN_END + .03:.2f};1"><mpath href="#activityPath"/></animateMotion>
    <animate attributeName="r" values="6;12;6" dur="2.15s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;.34;.34;0;0" keyTimes="0;.025;{SCAN_END - .01:.2f};{SCAN_END + .03:.2f};1" dur="{DURATION}s" repeatCount="indefinite"/>
  </circle>
</g>

<!-- A single completion sweep crosses the assembled word before the grid resets. -->
<rect x="250" y="48" width="70" height="82" rx="20" fill="url(#assemblySweep)" opacity="0" pointer-events="none">
  <animate attributeName="x" values="250;560" keyTimes="0;1" dur="1.1s" begin="{DURATION * (SCAN_END + .035):.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;.34;0" dur="1.1s" begin="{DURATION * (SCAN_END + .035):.2f}s" repeatCount="indefinite"/>
</rect>

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
