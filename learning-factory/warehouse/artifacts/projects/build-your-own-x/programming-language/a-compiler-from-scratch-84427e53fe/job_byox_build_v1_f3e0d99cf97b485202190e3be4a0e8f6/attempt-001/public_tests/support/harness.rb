# frozen_string_literal: true

module PublicTest
  class AssertionFailed < StandardError
  end

  class Case
    class << self
      def assertions
        @assertions ||= 0
      end

      def record_assertion
        @assertions = assertions + 1
      end

      def run!
        tests = public_instance_methods(false).grep(/^test_/).sort
        failures = []
        tests.each do |name|
          begin
            new.public_send(name)
            print "."
          rescue Exception => error # Test harness must report implementation stubs too.
            print "F"
            failures << [name, error]
          end
        end
        puts
        failures.each do |name, error|
          location = error.backtrace && error.backtrace.first
          puts "FAIL #{name}: #{error.class}: #{error.message}"
          puts "  #{location}" if location
        end
        puts "#{tests.length} tests, #{assertions} assertions, #{failures.length} failures"
        exit(failures.empty? ? 0 : 1)
      end
    end

    def assert(value, message = "expected a truthy value")
      self.class.record_assertion
      raise AssertionFailed, message unless value
      value
    end

    def assert_equal(expected, actual, message = nil)
      self.class.record_assertion
      return actual if expected == actual

      raise AssertionFailed, (message || "expected #{expected.inspect}, got #{actual.inspect}")
    end

    def assert_nil(actual, message = nil)
      assert_equal(nil, actual, message)
    end

    def assert_match(pattern, actual, message = nil)
      self.class.record_assertion
      return actual if pattern.match?(actual.to_s)

      raise AssertionFailed, (message || "expected #{actual.inspect} to match #{pattern.inspect}")
    end

    def assert_raises(expected_class)
      self.class.record_assertion
      begin
        yield
      rescue Exception => error # Preserve unexpected test and stub failures for the runner.
        return error if error.is_a?(expected_class)

        raise error
      end
      raise AssertionFailed, "expected #{expected_class} to be raised"
    end
  end
end
