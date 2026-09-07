from __future__ import annotations

import argparse
import json
from pathlib import Path


WIDTH = 880
HEIGHT = 160
BASELINE = 104


def palette(dark: bool) -> dict[str, str]:
    if dark:
        return {
            "signal": "#22d3ee",
            "accent": "#a78bfa",
        }
    return {
        "signal": "#0891b2",
        "accent": "#7c3aed",
    }


def heartbeat_path(x0: float, x1: float, y: float, beats: int, amplitude: float) -> str:
    """Create a clean ECG-like path between two x coordinates."""
    beats = max(1, beats)
    span = (x1 - x0) / beats
    commands = [f"M{x0:.1f} {y:.1f}"]

    for index in range(beats):
        start = x0 + index * span
        points = [
            (start + span * 0.16, y),
            (start + span * 0.26, y),
            (start + span * 0.33, y - amplitude * 0.16),
            (start + span * 0.39, y + amplitude * 0.10),
            (start + span * 0.47, y - amplitude),
            (start + span * 0.55, y + amplitude * 0.50),
            (start + span * 0.64, y),
            (start + span * 0.82, y),
            (start + span, y),
        ]
        commands.extend(f"L{x:.1f} {py:.1f}" for x, py in points)

    return " ".join(commands)


def word_segments() -> list[tuple[str, str, float, float]]:
    """Return MALVES as six monoline letter paths and their draw windows."""
    return [
        (
            "M",
            "M310 104 L310 60 L324 84 L338 60 L338 104",
            0.22,
            0.33,
        ),
        (
            "A",
            "M354 104 L368 60 L382 104 M359 86 H377",
            0.31,
            0.42,
        ),
        (
            "L",
            "M398 60 V104 H426",
            0.40,
            0.51,
        ),
        (
            "V",
            "M442 60 L456 104 L470 60",
            0.49,
            0.60,
        ),
        (
            "E",
            "M514 60 H486 V104 H514 M486 82 H509",
            0.58,
            0.69,
        ),
        (
            "S",
            "M530 60 H568 V82 H530 V104 H568",
            0.67,
            0.78,
        ),
    ]


def render(data: dict, dark: bool) -> str:
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar.get("weeks", [])
    total = int(calendar.get("totalContributions", 0))

    recent_total = 0
    for week in weeks[-8:]:
        recent_total += sum(int(day.get("contributionCount", 0)) for day in week.get("contributionDays", []))

    yearly_activity = min(total / 2500.0, 1.0)
    recent_activity = min(recent_total / 160.0, 1.0)

    # Activity keeps the old data-driven behavior, but only changes the signal:
    # more recent activity -> faster heartbeat and stronger peaks;
    # more yearly activity -> slightly thicker luminous trail.
    duration = 12.0 - recent_activity * 3.2
    beats = 2 + int(round(recent_activity * 3))
    amplitude = 14.0 + recent_activity * 20.0
    stroke_width = 1.9 + yearly_activity * 0.9
    glow_width = stroke_width + 4.2
    trail = 118 + int(yearly_activity * 170)

    pre = heartbeat_path(40, 310, BASELINE, beats, amplitude)
    post = heartbeat_path(568, 840, BASELINE, beats, amplitude * 0.92)
    p = palette(dark)

    letters: list[str] = []
    for _, path, start, end in word_segments():
        fade = min(0.88, end + 0.11)
        letters.append(
            f'''<path d="{path}" pathLength="1" fill="none" stroke="{p['accent']}" stroke-width="{stroke_width + .35:.2f}"
      stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1" stroke-dashoffset="1" filter="url(#glow)">
  <animate attributeName="stroke-dashoffset" values="1;1;0;0;1" keyTimes="0;{start:.3f};{end:.3f};{fade:.3f};1" dur="{duration:.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;{start:.3f};{end:.3f};{fade:.3f};1" dur="{duration:.2f}s" repeatCount="indefinite"/>
</path>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity heartbeat writing MALVES</title>
<desc id="desc">A contribution-driven heartbeat crosses the profile, changes color while writing MALVES in the center, then continues and repeats forever.</desc>
<defs>
  <filter id="glow" x="-160%" y="-160%" width="420%" height="420%">
    <feGaussianBlur stdDeviation="2.4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="soft" x="-140%" y="-140%" width="380%" height="380%">
    <feGaussianBlur stdDeviation="5.2"/>
  </filter>
</defs>

<!-- No static guide, calendar or hidden route: only the live signal is visible. -->
<path d="{pre}" pathLength="1000" fill="none" stroke="{p['signal']}" stroke-width="{glow_width:.2f}"
      stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".10" stroke-dasharray="{trail} {1000 - trail}" filter="url(#soft)">
  <animate attributeName="stroke-dashoffset" values="1000;0;0;1000" keyTimes="0;.25;.29;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;.13;.13;0;0" keyTimes="0;.03;.24;.29;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
</path>
<path d="{pre}" pathLength="1000" fill="none" stroke="{p['signal']}" stroke-width="{stroke_width:.2f}"
      stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".92" stroke-dasharray="{trail} {1000 - trail}" filter="url(#glow)">
  <animate attributeName="stroke-dashoffset" values="1000;0;0;1000" keyTimes="0;.25;.29;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.03;.24;.29;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
</path>

<!-- The same signal changes color and writes MALVES, letter by letter, in the center. -->
<g>{''.join(letters)}</g>

<path d="{post}" pathLength="1000" fill="none" stroke="{p['signal']}" stroke-width="{glow_width:.2f}"
      stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".10" stroke-dasharray="{trail} {1000 - trail}" filter="url(#soft)">
  <animate attributeName="stroke-dashoffset" values="1000;1000;0;0;1000" keyTimes="0;.74;.96;.985;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;0;.13;.13;0" keyTimes="0;.72;.78;.96;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
</path>
<path d="{post}" pathLength="1000" fill="none" stroke="{p['signal']}" stroke-width="{stroke_width:.2f}"
      stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".92" stroke-dasharray="{trail} {1000 - trail}" filter="url(#glow)">
  <animate attributeName="stroke-dashoffset" values="1000;1000;0;0;1000" keyTimes="0;.74;.96;.985;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.72;.78;.96;1" dur="{duration:.2f}s" repeatCount="indefinite"/>
</path>
</svg>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "activity-heartbeat.svg").write_text(render(data, dark=False), encoding="utf-8")
    (args.output_dir / "activity-heartbeat-dark.svg").write_text(render(data, dark=True), encoding="utf-8")


if __name__ == "__main__":
    main()
