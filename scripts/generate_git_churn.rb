# frozen_string_literal: true

require 'json'
require 'open3'
require 'fileutils'

LOGIN = ARGV[0] || 'MathCouple'
OUTPUT_DIR = ARGV[1] || 'assets/generated'
PROFILE_TOKEN = ENV.fetch('PROFILE_STATS_TOKEN', '').strip
ACTION_TOKEN = ENV.fetch('GH_TOKEN', '').strip
TOKEN = PROFILE_TOKEN.empty? ? ACTION_TOKEN : PROFILE_TOKEN

abort('missing GitHub token') if TOKEN.empty?


def graphql(query, variables = {})
  command = ['gh', 'api', 'graphql', '-f', "query=#{query}"]
  variables.each do |key, value|
    next if value.nil?

    command.concat(['-F', "#{key}=#{value}"])
  end

  stdout, stderr, status = Open3.capture3({ 'GH_TOKEN' => TOKEN }, *command)
  raise "GitHub GraphQL request failed: #{stderr.strip}" unless status.success?

  payload = JSON.parse(stdout)
  errors = payload['errors']
  raise "GitHub GraphQL returned errors: #{errors.to_json}" if errors && !errors.empty?

  payload
end


def user_id(login)
  query = 'query($login:String!){user(login:$login){id}}'
  graphql(query, login: login).dig('data', 'user', 'id') || raise("GitHub user #{login.inspect} not found")
end


def visible_repositories(login)
  if PROFILE_TOKEN.empty?
    # GITHUB_TOKEN is deliberately repository-scoped. Keep the fallback honest:
    # it measures authored history in the profile repository only. Supplying a
    # PROFILE_STATS_TOKEN expands this to every authorized non-fork repository.
    full_name = ENV.fetch('GITHUB_REPOSITORY', "#{login}/#{login}")
    return [{ 'nameWithOwner' => full_name, 'isFork' => false, 'isPrivate' => false }]
  end

  owned_query = <<~GRAPHQL
    query($login:String!, $cursor:String) {
      user(login:$login) {
        repositories(first:100, after:$cursor, ownerAffiliations:OWNER, orderBy:{field:NAME,direction:ASC}) {
          nodes { nameWithOwner isFork isPrivate defaultBranchRef { name } }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  GRAPHQL

  contributed_query = <<~GRAPHQL
    query($login:String!, $cursor:String) {
      user(login:$login) {
        repositoriesContributedTo(first:100, after:$cursor, contributionTypes:[COMMIT], includeUserRepositories:true, orderBy:{field:NAME,direction:ASC}) {
          nodes { nameWithOwner isFork isPrivate defaultBranchRef { name } }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  GRAPHQL

  repositories = []

  [[owned_query, 'repositories'], [contributed_query, 'repositoriesContributedTo']].each do |query, key|
    cursor = nil
    loop do
      payload = graphql(query, login: login, cursor: cursor)
      connection = payload.dig('data', 'user', key)
      break unless connection

      repositories.concat(connection.fetch('nodes').compact)
      page = connection.fetch('pageInfo')
      break unless page.fetch('hasNextPage')

      cursor = page.fetch('endCursor')
    end
  end

  repositories
    .reject { |repo| repo['isFork'] }
    .select { |repo| repo['defaultBranchRef'] }
    .uniq { |repo| repo.fetch('nameWithOwner') }
    .sort_by { |repo| repo.fetch('nameWithOwner').downcase }
end


def repository_churn(name_with_owner, author_id)
  owner, name = name_with_owner.split('/', 2)
  return { additions: 0, deletions: 0, commits: 0 } unless owner && name

  query = <<~GRAPHQL
    query($owner:String!, $name:String!, $cursor:String, $authorId:ID!) {
      repository(owner:$owner, name:$name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first:100, after:$cursor, author:{id:$authorId}) {
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

author_id = user_id(LOGIN)
repositories = visible_repositories(LOGIN)
stats = {
  additions: 0,
  deletions: 0,
  commits: 0,
  repositories: repositories.length,
  scope: PROFILE_TOKEN.empty? ? 'profile-repository-default-branch-history' : 'authorized-non-fork-default-branch-history',
  scope_label: PROFILE_TOKEN.empty? ? 'PUBLIC PROFILE REPOSITORY HISTORY' : 'AUTHORIZED GITHUB HISTORY'
}

repositories.each do |repository|
  name = repository.fetch('nameWithOwner')
  churn = repository_churn(name, author_id)
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
