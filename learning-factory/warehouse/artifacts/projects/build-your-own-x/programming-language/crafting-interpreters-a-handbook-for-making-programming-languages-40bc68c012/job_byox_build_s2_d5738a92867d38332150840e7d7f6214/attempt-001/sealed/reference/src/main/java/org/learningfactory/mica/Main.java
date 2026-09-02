package org.learningfactory.mica;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class Main {
    private Main() { }

    public static void main(String[] args) {
        try {
            Options options = Options.parse(args);
            for (String line : Mica.run(options.source(), options.engine())) System.out.println(line);
        } catch (MicaException exception) {
            System.err.println(exception.getMessage());
            System.exit(exception.kind() == MicaException.Kind.RUNTIME
                    || exception.kind() == MicaException.Kind.LIMIT ? 70 : 65);
        } catch (UsageException exception) {
            System.err.println(exception.getMessage());
            System.err.println("usage: mica [--engine=tree|vm] (-e SOURCE | FILE)");
            System.exit(64);
        }
    }

    private record Options(Engine engine, String source) {
        static Options parse(String[] args) {
            Engine engine = Engine.TREE;
            List<String> positional = new ArrayList<>();
            for (int i = 0; i < args.length; i++) {
                String argument = args[i];
                if (argument.equals("--engine=tree")) engine = Engine.TREE;
                else if (argument.equals("--engine=vm")) engine = Engine.VM;
                else if (argument.equals("-e")) {
                    if (i + 1 >= args.length) throw new UsageException("-e requires source text");
                    positional.add("\0" + args[++i]);
                } else if (argument.startsWith("--")) {
                    throw new UsageException("unknown option: " + argument);
                } else {
                    positional.add(argument);
                }
            }
            if (positional.size() != 1) throw new UsageException("provide exactly one source argument or file");
            String input = positional.get(0);
            if (input.startsWith("\0")) return new Options(engine, input.substring(1));
            try {
                return new Options(engine, Files.readString(Path.of(input), StandardCharsets.UTF_8));
            } catch (IOException exception) {
                throw new UsageException("cannot read source file: " + exception.getMessage());
            }
        }
    }

    private static final class UsageException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        UsageException(String message) { super(message); }
    }
}
