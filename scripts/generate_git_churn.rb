# frozen_string_literal: true

require 'json'
require 'open3'
require 'fileutils'

LOGIN = ARGV[0] || 'MathCouple'
OUTPUT_DIR = ARGV[1] || 'assets/generated'


def graphql(query, variables = {})
  command = ['gh', 'api', 'graphql', '-f', "query=#{query}"]
  variables.each do |key, value|
    next if value.nil?

    command.concat(['-F', "#{key}=#{value}"])
  end

  stdout, stderr, status = Open3.capture3(*command)
  raise "GitHub GraphQL request failed: #{stderr.strip}" unless status.success?

  payload = JSON.parse(stdout)
  errors = payload['errors']
  raise "GitHub GraphQL returned errors: #{errors.to_json}" if errors && !errors.empty?

  payload
end


def user_and_owned_repositories(login)
  query = <<~GRAPHQL
    query($login: String!, $cursor: String) {
      user(login: $login) {
        id
        repositories(
          first: 100
          after: $cursor
          ownerAffiliations: OWNER
          privacy: PUBLIC
          orderBy: {field: NAME, direction: ASC}
        ) {
          nodes {
            nameWithOwner
            isFork
            isPrivate
            defaultBranchRef { name }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  GRAPHQL

  repositories = []
  cursor = nil
  user_id = nil

  loop do
    payload = graphql(query, login: login, cursor: cursor)
    user = payload.dig('data', 'user') || raise("GitHub user #{login.inspect} not found")
    user_id ||= user.fetch('id')
    connection = user.fetch('repositories')
    repositories.concat(connection.fetch('nodes').compact)
    page = connection.fetch('pageInfo')
    break unless page.fetch('hasNextPage')

    cursor = page.fetch('endCursor')
  end

  [user_id, repositories]
end


def contributed_repositories(login)
  query = <<~GRAPHQL
    query($login: String!, $cursor: String) {
      user(login: $login) {
        repositoriesContributedTo(
          first: 100
          after: $cursor
          contributionTypes: [COMMIT]
          includeUserRepositories: true
          orderBy: {field: NAME, direction: ASC}
        ) {
          nodes {
            nameWithOwner
            isFork
            isPrivate
            defaultBranchRef { name }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  GRAPHQL

  repositories = []
  cursor = nil

  loop do
    payload = graphql(query, login: login, cursor: cursor)
    connection = payload.dig('data', 'user', 'repositoriesContributedTo')
    break unless connection

    repositories.concat(connection.fetch('nodes').compact)
    page = connection.fetch('pageInfo')
    break unless page.fetch('hasNextPage')

    cursor = page.fetch('endCursor')
  end

  repositories
end


def repository_churn(name_with_owner, author_id)
  owner, name = name_with_owner.split('/', 2)
  return { additions: 0, deletions: 0, commits: 0 } unless owner && name

  query = <<~GRAPHQL
    query($owner: String!, $name: String!, $cursor: String, $authorId: ID!) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, after: $cursor, author: {id: $authorId}) {
                nodes { additions deletions }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
      }
    }
  GRAPHQL

  additions = 0
  deletions = 0
  commits = 0
  cursor = nil

  loop do
    payload = graphql(query, owner: owner, name: name, cursor: cursor, authorId: author_id)
    history = payload.dig('data', 'repository', 'defaultBranchRef', 'target', 'history')
    break unless history

    history.fetch('nodes').compact.each do |commit|
      additions += commit.fetch('additions', 0).to_i
      deletions += commit.fetch('deletions', 0).to_i
      commits += 1
    end

    page = history.fetch('pageInfo')
    break unless page.fetch('hasNextPage')

    cursor = page.fetch('endCursor')
  end

  { additions: additions, deletions: deletions, commits: commits }
rescue StandardError => e
  warn "Skipping #{name_with_owner}: #{e.message}"
  { additions: 0, deletions: 0, commits: 0 }
end


def compact_number(value)
  number = value.to_i
  return number.to_s if number < 1_000
  return format('%.1fK', number / 1_000.0).sub('.0K', 'K') if number < 1_000_000
  return format('%.2fM', number / 1_000_000.0).sub(/\.00M$/, 'M').sub(/0M$/, 'M') if number < 1_000_000_000

  format('%.2fB', number / 1_000_000_000.0).sub(/\.00B$/, 'B').sub(/0B$/, 'B')
end


def exact_number(value)
  value.to_i.to_s.reverse.scan(/.{1,3}/).join(',').reverse
end


def render_svg(stats, dark:)
  bg = dark ? '#0d1117' : '#ffffff'
  border = dark ? '#30363d' : '#d0d7de'
  text = dark ? '#f0f6fc' : '#24292f'
  muted = dark ? '#8b949e' : '#57606a'
  added = dark ? '#22d3ee' : '#0891b2'
  removed = dark ? '#c084fc' : '#7c3aed'

  added_compact = compact_number(stats.fetch(:additions))
  removed_compact = compact_number(stats.fetch(:deletions))
  added_exact = exact_number(stats.fetch(:additions))
  removed_exact = exact_number(stats.fetch(:deletions))
  repositories = stats.fetch(:repositories)
  commits = stats.fetch(:commits)

  <<~SVG
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 86" width="760" height="86" role="img" aria-labelledby="title desc">
      <title id="title">Public GitHub lifetime line churn</title>
      <desc id="desc">#{added_exact} lines added and #{removed_exact} lines removed across #{repositories} public repositories and #{commits} authored commits reachable from their default branches.</desc>
      <rect x="0.5" y="0.5" width="759" height="85" rx="14" fill="#{bg}" stroke="#{border}" stroke-opacity=".55"/>
      <line x1="380" y1="17" x2="380" y2="69" stroke="#{border}" stroke-opacity=".55"/>

      <g font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace">
        <text x="190" y="27" text-anchor="middle" font-size="11" letter-spacing="1.8" fill="#{muted}">LINES ADDED</text>
        <text x="190" y="58" text-anchor="middle" font-size="26" font-weight="700" fill="#{added}">+#{added_compact}</text>

        <text x="570" y="27" text-anchor="middle" font-size="11" letter-spacing="1.8" fill="#{muted}">LINES REMOVED</text>
        <text x="570" y="58" text-anchor="middle" font-size="26" font-weight="700" fill="#{removed}">−#{removed_compact}</text>

        <text x="380" y="78" text-anchor="middle" font-size="8.5" fill="#{muted}">PUBLIC GITHUB HISTORY · #{repositories} REPOS · #{commits} AUTHORED COMMITS</text>
      </g>

      <g opacity="0">
        <title>Exact totals: +#{added_exact} / -#{removed_exact}</title>
      </g>
    </svg>
  SVG
end

user_id, owned = user_and_owned_repositories(LOGIN)
contributed = contributed_repositories(LOGIN)
repositories = (owned + contributed)
               .select { |repo| !repo['isPrivate'] && !repo['isFork'] && repo['defaultBranchRef'] }
               .uniq { |repo| repo.fetch('nameWithOwner') }
               .sort_by { |repo| repo.fetch('nameWithOwner').downcase }

stats = { additions: 0, deletions: 0, commits: 0, repositories: repositories.length }

repositories.each do |repository|
  name = repository.fetch('nameWithOwner')
  churn = repository_churn(name, user_id)
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
    scope: 'public non-fork repositories contributed to by the user; commits reachable from default branches',
    additions: stats[:additions],
    deletions: stats[:deletions],
    commits: stats[:commits],
    repositories: stats[:repositories]
  ) + "\n",
  mode: 'w',
  encoding: 'UTF-8'
)
