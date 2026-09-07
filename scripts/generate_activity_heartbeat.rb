# frozen_string_literal: true

require 'json'

WIDTH = 880
HEIGHT = 176
CELL = 10
GAP = 3
STEP = CELL + GAP
GRID_X = 66
GRID_Y = 33
LEFT_X = 56
RIGHT_X = 824
WORD_START = 310
WORD_END = 568
BASELINE = 104
DURATION = 10.8


def clamp(value, low, high)
  [[value, low].max, high].min
end


def level(count)
  return 0 if count <= 0
  return 1 if count == 1
  return 2 if count <= 3
  return 3 if count <= 6

  4
end


def palette(dark)
  if dark
    {
      bg: '#0d1117',
      border: '#30363d',
      levels: ['#161b22', '#0e7490', '#0891b2', '#06b6d4', '#67e8f9'],
      signal: '#22d3ee',
      accent: '#a855f7'
    }
  else
    {
      bg: '#ffffff',
      border: '#d0d7de',
      levels: ['#ebedf0', '#a5f3fc', '#67e8f9', '#22d3ee', '#0891b2'],
      signal: '#0891b2',
      accent: '#7c3aed'
    }
  end
end


def brainfuck_output(path)
  source = File.read(path, encoding: 'UTF-8').chars.select { |char| '><+-.,[]'.include?(char) }
  tape = Array.new(64, 0)
  pointer = 0
  output = +''
  stack = []
  jumps = {}

  source.each_with_index do |char, index|
    case char
    when '['
      stack << index
    when ']'
      open_index = stack.pop
      raise 'unbalanced brainfuck program' unless open_index

      jumps[open_index] = index
      jumps[index] = open_index
    end
  end
  raise 'unbalanced brainfuck program' unless stack.empty?

  pc = 0
  while pc < source.length
    case source[pc]
    when '>'
      pointer += 1
      tape << 0 if pointer >= tape.length
    when '<'
      pointer = [pointer - 1, 0].max
    when '+'
      tape[pointer] = (tape[pointer] + 1) % 256
    when '-'
      tape[pointer] = (tape[pointer] - 1) % 256
    when '.'
      output << tape[pointer].chr
    when '['
      pc = jumps.fetch(pc) if tape[pointer].zero?
    when ']'
      pc = jumps.fetch(pc) unless tape[pointer].zero?
    end
    pc += 1
  end

  output
end


def lanes
  values = [GRID_Y - 6.0]
  6.times do |row|
    values << GRID_Y + row * STEP + CELL + GAP / 2.0
  end
  values << GRID_Y + 6 * STEP + CELL + 6.0
  values
end


def activity_lanes(weeks)
  lane_values = lanes
  current = 4

  weeks.map do |week|
    weighted = 0.0
    total = 0

    week.fetch('contributionDays').each do |day|
      count = day.fetch('contributionCount').to_i
      next if count <= 0

      weighted += day.fetch('weekday').to_i * count
      total += count
    end

    if total.positive?
      weekday = weighted / total
      current = clamp((weekday + 0.5).round, 0, lane_values.length - 1)
    end

    lane_values[current]
  end
end


def gutter_x(week_index)
  GRID_X + week_index * STEP + CELL + GAP / 2.0
end


def malves_commands(signature)
  raise "unexpected brainfuck signature: #{signature.inspect}" unless signature == 'MALVES'

  [
    # M — two vertical stems with a clear center valley.
    'V60', 'L324 83', 'L338 60', 'V104', 'H350',

    # A — apex, two legs and an explicit crossbar.
    'H354', 'L368 60', 'L382 104', 'L376 86', 'H360', 'L354 104', 'H398',

    # L — retrace the baseline once so the continuous stroke exits at the top.
    'H426', 'H398', 'V60',

    # A small arch is only a connector; it keeps the following V visually separate.
    'Q420 50 442 60',

    # V — exactly two diagonals, with no extra stem that could read as M.
    'L456 104', 'L470 60', 'H486',

    # E — finish at the lower-right so S can begin cleanly from its lower-left.
    'H514', 'H486', 'V82', 'H509', 'H486', 'V104', 'H514', 'H530',

    # S — rounded reverse traversal: bottom bowl -> waist -> top bowl.
    'H552', 'Q568 104 568 94', 'Q568 82 554 82', 'H544',
    'Q530 82 530 70', 'Q530 60 544 60', 'H568'
  ]
end


def activity_path(weeks, signature)
  week_lanes = activity_lanes(weeks)
  left_indices = weeks.each_index.select { |index| gutter_x(index) <= WORD_START - 16 }
  right_indices = weeks.each_index.select { |index| gutter_x(index) >= WORD_END + 20 }

  start_lane = left_indices.empty? ? BASELINE : week_lanes[left_indices.first]
  commands = ["M#{LEFT_X} #{format('%.1f', start_lane)}"]
  current_y = start_lane

  left_indices.each do |index|
    x = gutter_x(index)
    target_y = week_lanes[index]
    commands << "H#{format('%.1f', x)}"
    if (target_y - current_y).abs > 0.1
      commands << "V#{format('%.1f', target_y)}"
      current_y = target_y
    end
  end

  commands << "H#{WORD_START - 12}"
  commands << "V#{BASELINE}" if (current_y - BASELINE).abs > 0.1
  commands << "H#{WORD_START}"
  commands.concat(malves_commands(signature))

  # Leave the S at its top-right and descend only after the colored word region.
  commands << "H#{WORD_END + 10}"
  commands << "L#{WORD_END + 20} #{BASELINE}"
  current_y = BASELINE

  if right_indices.any?
    first_y = week_lanes[right_indices.first]
    commands << "H#{WORD_END + 24}"
    if (first_y - current_y).abs > 0.1
      commands << "V#{format('%.1f', first_y)}"
      current_y = first_y
    end

    right_indices.each do |index|
      x = gutter_x(index)
      target_y = week_lanes[index]
      commands << "H#{format('%.1f', x)}"
      if (target_y - current_y).abs > 0.1
        commands << "V#{format('%.1f', target_y)}"
        current_y = target_y
      end
    end
  end

  # Keep the route open. A dash cycle whose pattern length equals pathLength loops
  # seamlessly without the old off-screen return diagonals leaking into the frame.
  commands << "H#{RIGHT_X}"
  commands.join(' ')
end


def cell_markup(weeks, colors)
  total_weeks = [weeks.length - 1, 1].max
  cells = []

  weeks.each_with_index do |week, week_index|
    phase = 0.045 + (week_index.to_f / total_weeks) * 0.84
    before = clamp(phase - 0.018, 0.0, 1.0)
    after = clamp(phase + 0.024, 0.0, 1.0)

    week.fetch('contributionDays').each do |day|
      weekday = day.fetch('weekday').to_i
      count = day.fetch('contributionCount').to_i
      x = GRID_X + week_index * STEP
      y = GRID_Y + weekday * STEP
      fill = colors[:levels][level(count)]
      base = count.positive? ? 0.92 : 0.58
      peak = count.positive? ? 1.0 : 0.70
      stroke_peak = count.positive? ? 0.72 : 0.28

      cells << <<~SVG.strip
        <rect x="#{x}" y="#{y}" width="#{CELL}" height="#{CELL}" rx="2" fill="#{fill}" opacity="#{format('%.2f', base)}"
              stroke="#{colors[:signal]}" stroke-width=".65" stroke-opacity="0">
          <animate attributeName="opacity" values="#{format('%.2f', base)};#{format('%.2f', base)};#{format('%.2f', peak)};#{format('%.2f', base)};#{format('%.2f', base)}"
                   keyTimes="0;#{format('%.4f', before)};#{format('%.4f', phase)};#{format('%.4f', after)};1" dur="#{DURATION}s" repeatCount="indefinite"/>
          <animate attributeName="stroke-opacity" values="0;0;#{format('%.2f', stroke_peak)};0;0"
                   keyTimes="0;#{format('%.4f', before)};#{format('%.4f', phase)};#{format('%.4f', after)};1" dur="#{DURATION}s" repeatCount="indefinite"/>
        </rect>
      SVG
    end
  end

  cells.join
end


def render(data, dark, signature)
  calendar = data.fetch('data').fetch('user').fetch('contributionsCollection').fetch('contributionCalendar')
  weeks = calendar.fetch('weeks')
  total = calendar.fetch('totalContributions', 0).to_i
  colors = palette(dark)

  activity = [total / 2500.0, 1.0].min
  trail_length = (190 + activity * 320).round
  trail_gap = 1000 - trail_length
  core_width = 2.15 + activity * 0.75
  glow_width = core_width + 4.4
  route = activity_path(weeks, signature)
  cells = cell_markup(weeks, colors)
  grid_width = [weeks.length * STEP - GAP, 1].max
  grid_height = 7 * STEP - GAP

  word_start_offset = ((WORD_START - LEFT_X).to_f / (RIGHT_X - LEFT_X) * 100).round(2)
  word_end_offset = ((WORD_END - LEFT_X).to_f / (RIGHT_X - LEFT_X) * 100).round(2)

  <<~SVG
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 #{WIDTH} #{HEIGHT}" width="#{WIDTH}" height="#{HEIGHT}" role="img" aria-labelledby="title desc">
    <title id="title">GitHub contribution heartbeat writing #{signature}</title>
    <desc id="desc">One continuous activity signal moves through the GitHub contribution grid, writes #{signature} in the center with distinct lettering, and loops without off-screen return strokes.</desc>
    <defs>
      <linearGradient id="signalGradient" gradientUnits="userSpaceOnUse" x1="#{LEFT_X}" x2="#{RIGHT_X}" y1="0" y2="0">
        <stop offset="0%" stop-color="#{colors[:signal]}"/>
        <stop offset="#{format('%.2f', word_start_offset - 1.0)}%" stop-color="#{colors[:signal]}"/>
        <stop offset="#{format('%.2f', word_start_offset)}%" stop-color="#{colors[:accent]}"/>
        <stop offset="#{format('%.2f', word_end_offset)}%" stop-color="#{colors[:accent]}"/>
        <stop offset="#{format('%.2f', word_end_offset + 1.0)}%" stop-color="#{colors[:signal]}"/>
        <stop offset="100%" stop-color="#{colors[:signal]}"/>
      </linearGradient>
      <linearGradient id="edgeFade" gradientUnits="userSpaceOnUse" x1="0" x2="#{WIDTH}" y1="0" y2="0">
        <stop offset="0%" stop-color="black"/>
        <stop offset="5%" stop-color="white"/>
        <stop offset="95%" stop-color="white"/>
        <stop offset="100%" stop-color="black"/>
      </linearGradient>
      <filter id="glow" x="-160%" y="-160%" width="420%" height="420%">
        <feGaussianBlur stdDeviation="2.35" result="blur"/>
        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <filter id="soft" x="-140%" y="-140%" width="380%" height="380%">
        <feGaussianBlur stdDeviation="5.0"/>
      </filter>
      <clipPath id="viewportClip"><rect width="#{WIDTH}" height="#{HEIGHT}" rx="14"/></clipPath>
      <clipPath id="wordClip"><rect x="#{WORD_START - 5}" y="48" width="#{WORD_END - WORD_START + 10}" height="72"/></clipPath>
      <mask id="edgeSignalMask"><rect width="#{WIDTH}" height="#{HEIGHT}" fill="url(#edgeFade)"/></mask>
      <path id="activityPath" pathLength="1000" d="#{route}"/>
    </defs>

    <rect width="#{WIDTH}" height="#{HEIGHT}" rx="14" fill="#{colors[:bg]}"/>
    <rect x="#{GRID_X - 12}" y="#{GRID_Y - 12}" width="#{grid_width + 24}" height="#{grid_height + 24}" rx="12"
          fill="none" stroke="#{colors[:border]}" stroke-width="1" opacity=".34"/>

    <!-- The live signal stays behind the contribution cells and uses their gutters. -->
    <g clip-path="url(#viewportClip)" mask="url(#edgeSignalMask)">
      <use href="#activityPath" fill="none" stroke="url(#signalGradient)" stroke-width="#{format('%.2f', glow_width)}"
           stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".11"
           stroke-dasharray="#{trail_length} #{trail_gap}" filter="url(#soft)">
        <animate attributeName="stroke-dashoffset" values="0;-1000" dur="#{DURATION}s" repeatCount="indefinite"/>
      </use>
      <use href="#activityPath" fill="none" stroke="url(#signalGradient)" stroke-width="#{format('%.2f', core_width)}"
           stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".98"
           stroke-dasharray="#{trail_length} #{trail_gap}" filter="url(#glow)">
        <animate attributeName="stroke-dashoffset" values="0;-1000" dur="#{DURATION}s" repeatCount="indefinite"/>
      </use>
    </g>

    <g>#{cells}</g>

    <!-- Same continuous path and timing; only the #{signature} portion is promoted above the cells. -->
    <g clip-path="url(#wordClip)" pointer-events="none">
      <use href="#activityPath" fill="none" stroke="url(#signalGradient)" stroke-width="#{format('%.2f', core_width + 0.45)}"
           stroke-linecap="round" stroke-linejoin="round" stroke-opacity="1"
           stroke-dasharray="#{trail_length} #{trail_gap}" filter="url(#glow)">
        <animate attributeName="stroke-dashoffset" values="0;-1000" dur="#{DURATION}s" repeatCount="indefinite"/>
      </use>
    </g>
    </svg>
  SVG
end

input_path = ARGV[0] || abort('usage: ruby generate_activity_heartbeat.rb <calendar.json> <output_dir> [signature.bf]')
output_dir = ARGV[1] || abort('missing output directory')
signature_path = ARGV[2] || File.join(__dir__, 'malves.bf')

signature = brainfuck_output(signature_path)
data = JSON.parse(File.read(input_path, encoding: 'UTF-8'))
Dir.mkdir(output_dir) unless Dir.exist?(output_dir)

File.write(File.join(output_dir, 'activity-heartbeat.svg'), render(data, false, signature), mode: 'w', encoding: 'UTF-8')
File.write(File.join(output_dir, 'activity-heartbeat-dark.svg'), render(data, true, signature), mode: 'w', encoding: 'UTF-8')
