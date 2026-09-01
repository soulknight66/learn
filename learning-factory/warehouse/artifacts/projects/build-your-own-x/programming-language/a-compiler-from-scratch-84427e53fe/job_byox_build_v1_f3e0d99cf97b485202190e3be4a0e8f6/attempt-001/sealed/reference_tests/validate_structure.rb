# frozen_string_literal: true

require "json"
require "find"

REQUIRED = [
  "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
  "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
  "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter/README.md",
  "public_tests/README.md", "environment/README.md",
  "sealed/reference/README.md", "sealed/reference_tests/README.md",
  "sealed/DESIGN.md", "sealed/TRADEOFFS.md", "sealed/REVIEW.md",
  "sealed/alternatives/README.md",
  "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md",
  "debugging/README.md", "review_exercises/README.md",
  "benchmarks/README.md"
].freeze

FORBIDDEN = [
  ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
  "reference_tests", "hidden_tests", "solution", "solutions", "answers",
  "starter/sealed", "starter/reference", "starter/reference_tests",
  "starter/solution", "starter/solutions", "starter/answers",
  "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
  "environment/sealed"
].freeze

GENERATED_ROOTS = [
  "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
  "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
  "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter", "public_tests",
  "environment", "sealed", "adversarial", "debugging", "review_exercises",
  "benchmarks"
].freeze

MANIFEST = {
  "independent_validation" => "REQUIRED",
  "productionized" => false,
  "project_id" => "project_0d336967c5b89e5c4851b06a9e793cae",
  "provenance_sha256" => "e534f25088ceaa9ff361d1831402338ec743bc666427d4b05cb4f56be11ea594",
  "schema_version" => 1,
  "source_commit" => "aa17439b62f384511a5561ce308e9598b94d8989",
  "source_id" => "source_eac489a34bed5db9a1f2a580b457bcef",
  "status" => "GENERATED",
  "validation_labels" => ["GENERATED", "PARTIAL"]
}.freeze

missing = REQUIRED.reject { |path| File.file?(path) }
present_forbidden = FORBIDDEN.select { |path| File.exist?(path) || File.symlink?(path) }
raise "missing required: #{missing.inspect}" unless missing.empty?
raise "forbidden paths: #{present_forbidden.inspect}" unless present_forbidden.empty?

manifest = JSON.parse(File.read("MANIFEST.yaml"))
raise "manifest mismatch" unless manifest == MANIFEST

provenance = JSON.parse(File.read("PROVENANCE.json"))
expected_top = %w[classification license_boundary project schema_version snapshot_sha256 source]
raise "provenance top-level mismatch" unless provenance.keys.sort == expected_top.sort
raise "provenance snapshot mismatch" unless provenance["snapshot_sha256"] == manifest["provenance_sha256"]
raise "provenance project mismatch" unless provenance["project"]["project_id"] == manifest["project_id"]
raise "provenance source mismatch" unless provenance["source"]["source_id"] == manifest["source_id"]
unless provenance["license_boundary"]["linked_content_copied"] == false &&
       provenance["license_boundary"]["linked_resource_license"] == "NOASSERTION"
  raise "linked-content license boundary mismatch"
end

special = []
files = []
GENERATED_ROOTS.each do |root|
  Find.find(root) do |path|
    stat = File.lstat(path)
    if stat.symlink?
      special << path
      Find.prune if File.directory?(path)
    elsif stat.directory?
      next
    elsif stat.file?
      files << path
    else
      special << path
    end
  end
end
raise "non-regular generated entries: #{special.inspect}" unless special.empty?

credential_patterns = [
  /-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----/,
  /\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)\s*[:=]\s*["'][^"'\r\n]+/i,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/
]
credential_hits = []
files.each do |path|
  content = File.binread(path)
  credential_patterns.each do |pattern|
    credential_hits << [path, pattern.source] if content.match?(pattern)
  end
end
raise "credential-like content: #{credential_hits.inspect}" unless credential_hits.empty?

answer_leaks = files.select do |path|
  File.basename(path).match?(/ANSWER|SOLUTION/i) && !path.start_with?("sealed/")
end
raise "solution-bearing filename outside sealed: #{answer_leaks.inspect}" unless answer_leaks.empty?

puts "required files: #{REQUIRED.length}/#{REQUIRED.length}"
puts "forbidden paths present: #{present_forbidden.length}"
puts "non-regular generated entries: #{special.length}"
puts "credential-pattern matches: #{credential_hits.length}"
puts "solution-bearing filenames outside sealed: #{answer_leaks.length}"
puts "manifest strict object: OK"
puts "provenance strict JSON and identifiers: OK"
puts "generated regular files scanned: #{files.length}"
