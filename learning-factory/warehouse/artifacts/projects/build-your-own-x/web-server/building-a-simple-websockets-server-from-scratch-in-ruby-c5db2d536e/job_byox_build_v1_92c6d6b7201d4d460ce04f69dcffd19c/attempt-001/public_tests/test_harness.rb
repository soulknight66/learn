# frozen_string_literal: true

module PublicTest
  class Failure < StandardError
  end

  @cases = []

  class << self
    attr_reader :cases

    def test(name, &block)
      @cases << [name, block]
    end

    def assert(condition, message = "assertion failed")
      raise Failure, message unless condition
    end

    def assert_equal(expected, actual)
      return if expected == actual
      raise Failure, "expected #{expected.inspect}, got #{actual.inspect}"
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

    def run!
      failures = 0
      @cases.each do |name, test_case|
        begin
          test_case.call
          puts "PASS #{name}"
        rescue Exception => error # rubocop:disable Lint/RescueException
          raise if error.is_a?(SystemExit) || error.is_a?(Interrupt)
          failures += 1
          puts "FAIL #{name}: #{error.class}: #{error.message}"
        end
      end
      puts "#{@cases.length - failures}/#{@cases.length} public checks passed"
      exit(failures.zero? ? 0 : 1)
    end
  end
end

