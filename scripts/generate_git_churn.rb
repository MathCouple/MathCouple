# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'
require 'fileutils'

LOGIN = ARGV[0] || 'MathCouple'
OUTPUT_DIR = ARGV[1] || 'assets/generated'
TOKEN = ENV.fetch('PROFILE_STATS_TOKEN', '').strip
API_VERSION = '2026-03-10'


def github_get(path, token: nil, attempts: 5)
  uri = URI("https://api.github.com#{path}")
  request = Net::HTTP::Get.new(uri)
  request['Accept'] = 'application/vnd.github+json'
  request['X-GitHub-Api-Version'] = API_VERSION
  request['User-Agent'] = 'MathCouple-profile-stats'
  request['Authorization'] = "Bearer #{token}" unless token.to_s.empty?

  attempts.times do |attempt|
    response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) { |http| http.request(request) }

    case response.code.to_i
    when 200
      return JSON.parse(response.body)
    when 202
      sleep([2 + attempt * 2, 10].min)
      next
    when 204
      return []
    else
      raise "GET #{path} failed with HTTP #{response.code}: #{response.body.to_s[0, 300]}"
    end
  end

  raise "GET #{path} did not become ready after #{attempts} attempts"
end


def public_owned_repositories(login)
  repositories = []
  page = 1

  loop do
    batch = github_get("/users/#{login}/repos?type=owner&sort=full_name&direction=asc&per_page=100&page=#{page}")
    repositories.concat(batch)
    break if batch.length < 100

    page += 1
  end

  repositories
end


def authorized_repositories(token)
  repositories = []
  page = 1

  loop do
    batch = github_get(
      "/user/repos?affiliation=owner,collaborator,organization_member&visibility=all&sort=full_name&direction=asc&per_page=100&page=#{page}",
      token: token
    )
    repositories.concat(batch)
    break if batch.length < 100

    page += 1
  end

  repositories
end


def contributor_churn(full_name, login, token: nil)
  contributors = github_get("/repos/#{full_name}/stats/contributors", token: token)
  contributor = contributors.find { |item| item.dig('author', 'login').to_s.casecmp(login).zero? }
  return { additions: 0, deletions: 0, commits: 0 } unless contributor

  weeks = contributor.fetch('weeks', [])
  {
    additions: weeks.sum { |week| week.fetch('a', 0).to_i },
    deletions: weeks.sum { |week| week.fetch('d', 0).to_i },
    commits: contributor.fetch('total', 0).to_i
  }
rescue StandardError => e
  warn "Skipping #{full_name}: #{e.message}"
  { additions: 0, deletions: 0, commits: 0 }
end


def exact_number(value)
  value.to_i.to_s.reverse.scan(/.{1,3}/).join(',').reverse
end


def number_font_size(value)
  length = exact_number(value).length
  return 27 if length <= 9
  return 24 if length <= 12

  21
end


def render_svg(stats, dark:)
  bg = dark ? '#0d1117' : '#ffffff'
  border = dark ? '#30363d' : '#d0d7de'
  muted = dark ? '#8b949e' : '#57606a'
  added = dark ? '#22d3ee' : '#0891b2'
  removed = dark ? '#c084fc' : '#7c3aed'

  added_exact = exact_number(stats.fetch(:additions))
  removed_exact = exact_number(stats.fetch(:deletions))
  repositories = stats.fetch(:repositories)
  commits = stats.fetch(:commits)
  scope_label = stats.fetch(:scope_label)

  <<~SVG
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 88" width="760" height="88" role="img" aria-labelledby="title desc">
      <title id="title">GitHub authored line churn</title>
      <desc id="desc">#{added_exact} lines added and #{removed_exact} lines removed across #{repositories} repositories and #{commits} commits attributed to #{LOGIN}.</desc>
      <rect x="0.5" y="0.5" width="759" height="87" rx="14" fill="#{bg}" stroke="#{border}" stroke-opacity=".55"/>
      <line x1="380" y1="15" x2="380" y2="70" stroke="#{border}" stroke-opacity=".55"/>

      <g font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace">
        <text x="190" y="25" text-anchor="middle" font-size="10.5" letter-spacing="1.7" fill="#{muted}">LINES ADDED</text>
        <text x="190" y="58" text-anchor="middle" font-size="#{number_font_size(stats.fetch(:additions))}" font-weight="700" fill="#{added}">+#{added_exact}</text>

        <text x="570" y="25" text-anchor="middle" font-size="10.5" letter-spacing="1.7" fill="#{muted}">LINES REMOVED</text>
        <text x="570" y="58" text-anchor="middle" font-size="#{number_font_size(stats.fetch(:deletions))}" font-weight="700" fill="#{removed}">−#{removed_exact}</text>

        <text x="380" y="79" text-anchor="middle" font-size="8.2" letter-spacing=".45" fill="#{muted}">#{scope_label} · #{repositories} REPOS · #{commits} AUTHORED COMMITS</text>
      </g>
    </svg>
  SVG
end

if TOKEN.empty?
  repositories = public_owned_repositories(LOGIN)
  scope = 'public-owned-default-branch-history'
  scope_label = 'PUBLIC OWNED GITHUB HISTORY'
  api_token = nil
else
  repositories = authorized_repositories(TOKEN)
  scope = 'authorized-non-fork-default-branch-history'
  scope_label = 'AUTHORIZED GITHUB HISTORY'
  api_token = TOKEN
end

repositories = repositories
               .reject { |repo| repo.fetch('fork', false) }
               .select { |repo| repo['default_branch'] }
               .uniq { |repo| repo.fetch('full_name') }
               .sort_by { |repo| repo.fetch('full_name').downcase }

stats = {
  additions: 0,
  deletions: 0,
  commits: 0,
  repositories: repositories.length,
  scope: scope,
  scope_label: scope_label
}

repositories.each do |repository|
  name = repository.fetch('full_name')
  churn = contributor_churn(name, LOGIN, token: api_token)
  stats[:additions] += churn[:additions]
  stats[:deletions] += churn[:deletions]
  stats[:commits] += churn[:commits]
  warn "#{name}: +#{churn[:additions]} -#{churn[:deletions]} (#{churn[:commits]} commits)"
end

FileUtils.mkdir_p(OUTPUT_DIR)
File.write(File.join(OUTPUT_DIR, 'git-churn.svg'), render_svg(stats, dark: false), mode: 'w', encoding: 'UTF-8')
File.write(File.join(OUTPUT_DIR, 'git-churn-dark.svg'), render_svg(stats, dark: true), mode: 'w', encoding: 'UTF-8')
File.write(
  File.join(OUTPUT_DIR, 'git-churn.json'),
  JSON.pretty_generate(
    login: LOGIN,
    scope: stats[:scope],
    additions: stats[:additions],
    deletions: stats[:deletions],
    commits: stats[:commits],
    repositories: stats[:repositories]
  ) + "\n",
  mode: 'w',
  encoding: 'UTF-8'
)
