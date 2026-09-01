# frozen_string_literal: true

require "socket"
require "thread"

module TinyWS
  class Server
    DEFAULTS = {
      host: "127.0.0.1",
      port: 8080,
      max_clients: 32,
      max_header_bytes: 16_384,
      max_frame_bytes: 1_048_576,
      max_message_bytes: 4_194_304,
      handshake_timeout: 5.0,
      read_timeout: 30.0
    }.freeze

    BAD_REQUEST = "HTTP/1.1 400 Bad Request\r\nConnection: close\r\n" \
                  "Content-Length: 0\r\n\r\n".b.freeze

    def initialize(**options, &handler)
      unknown = options.keys - DEFAULTS.keys
      raise ArgumentError, "unknown options: #{unknown.join(', ')}" unless unknown.empty?
      @options = DEFAULTS.merge(options)
      validate_options!
      @handler = handler || proc { |_type, payload| payload }
      @mutex = Mutex.new
      @listener = nil
      @accept_thread = nil
      @clients = {}
      @running = false
    end

    def start
      listener = nil
      @mutex.synchronize do
        return self if @running
        listener = TCPServer.new(@options[:host], @options[:port])
        listener.setsockopt(Socket::SOL_SOCKET, Socket::SO_REUSEADDR, true)
        @listener = listener
        @running = true
        @accept_thread = Thread.new { accept_loop(listener) }
      end
      self
    rescue Exception
      listener.close if listener && !listener.closed?
      raise
    end

    def port
      @mutex.synchronize do
        @listener ? @listener.addr[1] : @options[:port]
      end
    end

    def stop(join_timeout: 2.0)
      listener = nil
      accept_thread = nil
      clients = nil
      @mutex.synchronize do
        return self unless @running || @listener || !@clients.empty?
        @running = false
        listener = @listener
        @listener = nil
        accept_thread = @accept_thread
        @accept_thread = nil
        clients = @clients.dup
      end

      close_quietly(listener)
      clients.each_key { |socket| close_quietly(socket) }
      deadline = monotonic_now + [join_timeout.to_f, 0.0].max
      join_until(accept_thread, deadline)
      clients.each_value { |thread| join_until(thread, deadline) }
      self
    end

    def serve_forever
      start
      thread = @mutex.synchronize { @accept_thread }
      thread.join if thread
    ensure
      stop
    end

    private

    def validate_options!
      raise ArgumentError, "port is out of range" unless (0..65_535).cover?(@options[:port].to_i)
      [:max_clients, :max_header_bytes, :max_frame_bytes,
       :max_message_bytes].each do |name|
        raise ArgumentError, "#{name} must be positive" unless @options[name].to_i > 0
      end
      [:handshake_timeout, :read_timeout].each do |name|
        raise ArgumentError, "#{name} must be positive" unless @options[name].to_f > 0
      end
    end

    def accept_loop(listener)
      loop do
        socket = listener.accept
        admitted = @mutex.synchronize do
          @running && @clients.length < @options[:max_clients]
        end
        unless admitted
          close_quietly(socket)
          next
        end
        launch_client(socket)
      rescue IOError, SystemCallError
        break unless running?
      end
    ensure
      close_quietly(listener)
    end

    def launch_client(socket)
      @mutex.synchronize do
        unless @running && @clients.length < @options[:max_clients]
          close_quietly(socket)
          return
        end
        thread = Thread.new do
          begin
            handle_client(socket)
          rescue StandardError
            # All failures remain scoped to this connection. A production
            # adapter should report unexpected classes through a safe hook.
          ensure
            close_quietly(socket)
            @mutex.synchronize { @clients.delete(socket) }
          end
        end
        @clients[socket] = thread
      end
    end

    def handle_client(socket)
      request = HTTPUpgrade.read(
        socket,
        max_bytes: @options[:max_header_bytes],
        timeout: @options[:handshake_timeout]
      )
      response = Handshake.response_for(request)
      write_all(socket, response)
      Connection.new(
        socket,
        max_frame_bytes: @options[:max_frame_bytes],
        max_message_bytes: @options[:max_message_bytes],
        read_timeout: @options[:read_timeout],
        initial_bytes: request.take_remainder
      ).run(&@handler)
    rescue HandshakeError
      begin
        write_all(socket, BAD_REQUEST)
      rescue IOError, SystemCallError
        nil
      end
    end

    def write_all(io, bytes)
      offset = 0
      while offset < bytes.bytesize
        count = io.write(bytes.byteslice(offset, bytes.bytesize - offset))
        raise IOError, "socket write made no progress" unless count && count > 0
        offset += count
      end
    end

    def join_until(thread, deadline)
      return unless thread && thread != Thread.current
      remaining = deadline - monotonic_now
      thread.join(remaining) if remaining > 0
      return unless thread.alive?
      thread.kill
      thread.join(0.1)
    end

    def running?
      @mutex.synchronize { @running }
    end

    def close_quietly(io)
      io.close if io && !io.closed?
    rescue IOError, SystemCallError
      nil
    end

    def monotonic_now
      Process.clock_gettime(Process::CLOCK_MONOTONIC)
    end
  end
end
