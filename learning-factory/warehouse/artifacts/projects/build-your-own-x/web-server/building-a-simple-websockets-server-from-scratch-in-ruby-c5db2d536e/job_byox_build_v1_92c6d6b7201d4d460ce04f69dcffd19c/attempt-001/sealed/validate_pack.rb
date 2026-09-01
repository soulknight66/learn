# frozen_string_literal: true

require "digest"
require "json"

ROOT = File.expand_path("..", __dir__)

REQUIRED = %w[
  README.md
  AGENTS.md
  MANIFEST.yaml
  PROVENANCE.json
  LICENSE_BOUNDARY.md
  REQUIREMENTS.md
  CONCEPTS.md
  DESIGN_QUESTIONS.md
  VALIDATION.md
  starter/README.md
  public_tests/README.md
  environment/README.md
  sealed/reference/README.md
  sealed/reference_tests/README.md
  sealed/DESIGN.md
  sealed/TRADEOFFS.md
  sealed/REVIEW.md
  sealed/alternatives/README.md
  sealed/production/PRODUCTIONIZATION.md
  adversarial/README.md
  debugging/README.md
  review_exercises/README.md
  benchmarks/README.md
].freeze

FORBIDDEN = %w[
  .git
  .env
  .venv
  credentials.json
  secrets
  reference
  reference_tests
  hidden_tests
  solution
  solutions
  answers
  starter/sealed
  starter/reference
  starter/reference_tests
  starter/solution
  starter/solutions
  starter/answers
  public_tests/sealed
  public_tests/reference
  public_tests/hidden_tests
  environment/sealed
].freeze

EXPECTED_MANIFEST = {
  "independent_validation" => "REQUIRED",
  "productionized" => false,
  "project_id" => "project_0481ac5d3348b421d2f9d5d0c6d52ecb",
  "provenance_sha256" => "aa3c412b3df6335355c1c77e7d9226a99d11df1604e54a4369e515acd2b99773",
  "schema_version" => 1,
  "source_commit" => "aa17439b62f384511a5561ce308e9598b94d8989",
  "source_id" => "source_eac489a34bed5db9a1f2a580b457bcef",
  "status" => "GENERATED",
  "validation_labels" => ["GENERATED", "PARTIAL"]
}.freeze

failures = []

REQUIRED.each do |relative|
  path = File.join(ROOT, relative)
  failures << "missing regular file: #{relative}" unless File.file?(path) && !File.symlink?(path)
end

FORBIDDEN.each do |relative|
  path = File.join(ROOT, relative)
  failures << "forbidden path exists: #{relative}" if File.exist?(path) || File.symlink?(path)
end

Dir.glob(File.join(ROOT, "**", "*"), File::FNM_DOTMATCH).each do |path|
  next if [".", ".."].include?(File.basename(path))
  stat = File.lstat(path)
  relative = path.sub(%r{\A#{Regexp.escape(ROOT)}/?}, "")
  failures << "symlink is not archivable: #{relative}" if stat.symlink?
  unless stat.file? || stat.directory?
    failures << "special file is not archivable: #{relative}"
  end
end

begin
  manifest = JSON.parse(File.binread(File.join(ROOT, "MANIFEST.yaml")))
  failures << "MANIFEST.yaml object differs" unless manifest == EXPECTED_MANIFEST
rescue JSON::ParserError => error
  failures << "MANIFEST.yaml is not strict JSON: #{error.message}"
end

begin
  provenance = JSON.parse(File.binread(File.join(ROOT, "PROVENANCE.json")))
  linked = provenance.dig("license_boundary", "linked_content_copied")
  snapshot = provenance["snapshot_sha256"]
  project_id = provenance.dig("project", "project_id")
  failures << "provenance copied-content flag differs" unless linked == false
  failures << "provenance snapshot differs" unless snapshot == EXPECTED_MANIFEST["provenance_sha256"]
  failures << "provenance project differs" unless project_id == EXPECTED_MANIFEST["project_id"]
rescue JSON::ParserError => error
  failures << "PROVENANCE.json is not strict JSON: #{error.message}"
end

secret_patterns = {
  "PEM private key" => /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  "AWS access key" => /AKIA[0-9A-Z]{16}/,
  "GitHub token" => /gh[pousr]_[A-Za-z0-9]{20,}/,
  "Slack token" => /xox[baprs]-[A-Za-z0-9-]{10,}/,
  "assigned credential" => /(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*["'][^"'\r\n]+["']/i
}.freeze

Dir.glob(File.join(ROOT, "**", "*"), File::FNM_DOTMATCH).each do |path|
  next unless File.file?(path)
  content = File.binread(path)
  secret_patterns.each do |label, pattern|
    failures << "possible #{label}: #{path.sub(ROOT + '/', '')}" if content.match?(pattern)
  end
end

if failures.empty?
  puts "PASS structure, forbidden paths, metadata status, regular-file policy, and credential scan"
else
  failures.each { |failure| warn "FAIL #{failure}" }
  exit 1
end

