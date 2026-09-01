# frozen_string_literal: true

module SealedTest
  class Failure < StandardError
  end

  class Skip < StandardError
  end

  @cases = []

  class << self
    attr_reader :cases

    def test(name, &block)
      @cases << [name, block]
    end

    def assert(value, message = "assertion failed")
      raise Failure, message unless value
    end

    def refute(value, message = "refutation failed")
      raise Failure, message if value
    end

    def assert_equal(expected, actual)
      return if expected == actual
      raise Failure, "expected #{expected.inspect}, got #{actual.inspect}"
    end

    def assert_includes(collection, value)
      return if collection.include?(value)
      raise Failure, "expected #{collection.inspect} to include #{value.inspect}"
    end

    def assert_raises(error_class)
      begin
        yield
      rescue error_class => error
        return error
      rescue StandardError => error
        raise Failure, "expected #{error_class}, got #{error.class}: #{error.message}"
      end
      raise Failure, "expected #{error_class}, but nothing was raised"
    end

    def skip(message)
      raise Skip, message
    end

    def run!
      failures = []
      skips = []
      @cases.each do |name, block|
        begin
          block.call
          puts "PASS #{name}"
        rescue Skip => error
          skips << [name, error]
          puts "SKIP #{name}: #{error.message}"
        rescue Exception => error # rubocop:disable Lint/RescueException
          raise if error.is_a?(SystemExit) || error.is_a?(Interrupt)
          failures << [name, error]
          puts "FAIL #{name}: #{error.class}: #{error.message}"
          Array(error.backtrace).first(2).each { |line| puts "  #{line}" }
        end
      end
      passed = @cases.length - failures.length - skips.length
      puts "#{passed} passed, #{skips.length} skipped, #{failures.length} failed"
      exit(failures.empty? ? 0 : 1)
    end
  end
end
