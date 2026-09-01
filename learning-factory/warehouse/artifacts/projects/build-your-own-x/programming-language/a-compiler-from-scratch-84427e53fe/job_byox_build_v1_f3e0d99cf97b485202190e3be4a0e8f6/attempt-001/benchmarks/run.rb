# frozen_string_literal: true

require "json"
require "stringio"

candidate_lib = ENV["PEBBLE_LIB"] || File.expand_path("../starter/lib", __dir__)
$LOAD_PATH.unshift(candidate_lib)
require "pebble"

iterations_text = ENV.fetch("PEBBLE_BENCH_ITERATIONS", "20")
unless iterations_text.match?(/\A[1-9][0-9]*\z/)
  abort "PEBBLE_BENCH_ITERATIONS must be a positive decimal integer"
end
iterations = iterations_text.to_i

source = <<~PEBBLE
  let i = 0;
  let total = 0;
  while (i < 1000) {
    total = total + i;
    i = i + 1;
  }
  print total;
PEBBLE

check = StringIO.new
Pebble.run(source, output: check)
abort "benchmark workload produced unexpected output" unless check.string == "499500\n"

started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
iterations.times do
  Pebble.run(source, output: StringIO.new)
end
elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started

puts JSON.generate(
  project_id: "project_0d336967c5b89e5c4851b06a9e793cae",
  workload: "compile_and_execute_sum_0_to_999",
  iterations: iterations,
  elapsed_seconds: elapsed,
  validation_label: "UNVALIDATED_MEASUREMENT"
)
