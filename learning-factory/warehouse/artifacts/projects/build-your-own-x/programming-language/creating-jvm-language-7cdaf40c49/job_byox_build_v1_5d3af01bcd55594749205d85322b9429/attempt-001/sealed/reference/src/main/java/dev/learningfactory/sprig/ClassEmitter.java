package dev.learningfactory.sprig;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class ClassEmitter {
    private static final int ACC_PUBLIC = 0x0001;
    private static final int ACC_STATIC = 0x0008;
    private static final int ACC_FINAL = 0x0010;
    private static final int ACC_SUPER = 0x0020;
    private static final int MAX_CODE_LENGTH = 65_535;

    private final String className;
    private final Analyzer.Analysis analysis;
    private ConstantPool pool;
    private CodeBuffer code;
    private int systemOut;
    private int printlnInt;

    ClassEmitter(String className, Analyzer.Analysis analysis) {
        this.className = className;
        this.analysis = analysis;
    }

    byte[] emit(Ast.Program program) throws CompileFailure {
        pool = new ConstantPool(program.pos());
        int thisClass = pool.classInfo(className);
        int superClass = pool.classInfo("java/lang/Object");
        int runName = pool.utf8("run");
        int runDescriptor = pool.utf8("()I");
        int codeName = pool.utf8("Code");
        systemOut = pool.fieldRef("java/lang/System", "out", "Ljava/io/PrintStream;");
        printlnInt = pool.methodRef("java/io/PrintStream", "println", "(I)V");

        code = new CodeBuffer(program.pos());
        emitStatements(program.statements());
        byte[] methodCode = code.toByteArray();
        if (methodCode.length > MAX_CODE_LENGTH) {
            throw CompileFailure.at("E_LIMIT", program.pos(),
                    "generated run method exceeds 65535 code bytes");
        }
        int maxStack = Math.max(1, statementStack(program.statements()));
        int maxLocals = analysis.symbols().size();

        try {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            DataOutputStream out = new DataOutputStream(bytes);
            out.writeInt(0xCAFEBABE);
            out.writeShort(0);
            out.writeShort(49);
            pool.write(out);
            out.writeShort(ACC_PUBLIC | ACC_FINAL | ACC_SUPER);
            out.writeShort(thisClass);
            out.writeShort(superClass);
            out.writeShort(0); // interfaces
            out.writeShort(0); // fields
            out.writeShort(1); // methods
            out.writeShort(ACC_PUBLIC | ACC_STATIC);
            out.writeShort(runName);
            out.writeShort(runDescriptor);
            out.writeShort(1); // method attributes
            out.writeShort(codeName);
            out.writeInt(12 + methodCode.length);
            out.writeShort(maxStack);
            out.writeShort(maxLocals);
            out.writeInt(methodCode.length);
            out.write(methodCode);
            out.writeShort(0); // exception table
            out.writeShort(0); // Code attributes
            out.writeShort(0); // class attributes
            out.flush();
            return bytes.toByteArray();
        } catch (IOException impossibleForMemoryStreams) {
            throw new IllegalStateException("in-memory class writing failed",
                    impossibleForMemoryStreams);
        }
    }

    private void emitStatements(List<Ast.Stmt> statements) throws CompileFailure {
        for (Ast.Stmt statement : statements) emitStatement(statement);
    }

    private void emitStatement(Ast.Stmt statement) throws CompileFailure {
        if (statement instanceof Ast.Let let) {
            emitExpression(let.initializer());
            store(let.name());
            return;
        }
        if (statement instanceof Ast.Assign assign) {
            emitExpression(assign.value());
            store(assign.name());
            return;
        }
        if (statement instanceof Ast.Print print) {
            code.u1(0xb2); // getstatic
            code.u2(systemOut);
            emitExpression(print.value());
            code.u1(0xb6); // invokevirtual
            code.u2(printlnInt);
            return;
        }
        if (statement instanceof Ast.Return returnStatement) {
            emitExpression(returnStatement.value());
            code.u1(0xac); // ireturn
            return;
        }
        if (statement instanceof Ast.If conditional) {
            Label elseLabel = new Label();
            emitExpression(conditional.condition());
            code.branch(0x99, elseLabel); // ifeq
            emitStatements(conditional.thenBranch());
            boolean thenTerminates = statementsTerminate(conditional.thenBranch());
            Label endLabel = thenTerminates ? null : new Label();
            if (endLabel != null) code.branch(0xa7, endLabel); // goto
            code.mark(elseLabel);
            emitStatements(conditional.elseBranch());
            if (endLabel != null) code.mark(endLabel);
            return;
        }
        if (statement instanceof Ast.While loop) {
            Label header = new Label();
            Label end = new Label();
            code.mark(header);
            emitExpression(loop.condition());
            code.branch(0x99, end); // ifeq
            emitStatements(loop.body());
            code.branch(0xa7, header); // goto
            code.mark(end);
            return;
        }
        throw new IllegalStateException("unknown statement " + statement.getClass());
    }

    private void emitExpression(Ast.Expr expression) throws CompileFailure {
        if (expression instanceof Ast.Literal literal) {
            emitConstant(literal.value());
            return;
        }
        if (expression instanceof Ast.Variable variable) {
            code.u1(0x15); // iload
            code.u1(symbol(variable.name()).slot());
            return;
        }
        if (expression instanceof Ast.Unary unary) {
            emitExpression(unary.operand());
            if (unary.operator() == TokenType.MINUS) {
                code.u1(0x74); // ineg
            } else if (unary.operator() == TokenType.BANG) {
                emitConstant(1);
                code.u1(0x82); // ixor; booleans are canonical
            } else {
                throw new IllegalStateException("unknown unary operator " + unary.operator());
            }
            return;
        }
        if (expression instanceof Ast.Binary binary) {
            switch (binary.operator()) {
                case PLUS -> emitArithmetic(binary, 0x60);
                case MINUS -> emitArithmetic(binary, 0x64);
                case STAR -> emitArithmetic(binary, 0x68);
                case SLASH -> emitArithmetic(binary, 0x6c);
                case PERCENT -> emitArithmetic(binary, 0x70);
                case EQUAL_EQUAL -> emitComparison(binary, 0x9f);
                case BANG_EQUAL -> emitComparison(binary, 0xa0);
                case LESS -> emitComparison(binary, 0xa1);
                case GREATER_EQUAL -> emitComparison(binary, 0xa2);
                case GREATER -> emitComparison(binary, 0xa3);
                case LESS_EQUAL -> emitComparison(binary, 0xa4);
                case AND_AND -> emitLogical(binary, false);
                case OR_OR -> emitLogical(binary, true);
                default -> throw new IllegalStateException(
                        "unknown binary operator " + binary.operator());
            }
            return;
        }
        throw new IllegalStateException("unknown expression " + expression.getClass());
    }

    private void emitArithmetic(Ast.Binary binary, int opcode) throws CompileFailure {
        emitExpression(binary.left());
        emitExpression(binary.right());
        code.u1(opcode);
    }

    private void emitComparison(Ast.Binary binary, int branchOpcode)
            throws CompileFailure {
        Label trueLabel = new Label();
        Label endLabel = new Label();
        emitExpression(binary.left());
        emitExpression(binary.right());
        code.branch(branchOpcode, trueLabel);
        emitConstant(0);
        code.branch(0xa7, endLabel);
        code.mark(trueLabel);
        emitConstant(1);
        code.mark(endLabel);
    }

    private void emitLogical(Ast.Binary binary, boolean isOr) throws CompileFailure {
        Label decisive = new Label();
        Label end = new Label();
        emitExpression(binary.left());
        code.branch(isOr ? 0x9a : 0x99, decisive); // ifne for OR, ifeq for AND
        emitExpression(binary.right());
        code.branch(isOr ? 0x9a : 0x99, decisive);
        emitConstant(isOr ? 0 : 1);
        code.branch(0xa7, end);
        code.mark(decisive);
        emitConstant(isOr ? 1 : 0);
        code.mark(end);
    }

    private void emitConstant(int value) throws CompileFailure {
        if (value == -1) {
            code.u1(0x02);
        } else if (value >= 0 && value <= 5) {
            code.u1(0x03 + value);
        } else if (value >= Byte.MIN_VALUE && value <= Byte.MAX_VALUE) {
            code.u1(0x10); // bipush
            code.u1(value);
        } else if (value >= Short.MIN_VALUE && value <= Short.MAX_VALUE) {
            code.u1(0x11); // sipush
            code.u2(value);
        } else {
            code.u1(0x13); // ldc_w
            code.u2(pool.integer(value));
        }
    }

    private void store(String name) {
        code.u1(0x36); // istore
        code.u1(symbol(name).slot());
    }

    private Analyzer.Symbol symbol(String name) {
        Analyzer.Symbol result = analysis.symbols().get(name);
        if (result == null) throw new IllegalStateException("missing analyzed symbol " + name);
        return result;
    }

    private static int statementStack(List<Ast.Stmt> statements) {
        int maximum = 0;
        for (Ast.Stmt statement : statements) {
            int needed;
            if (statement instanceof Ast.Let let) {
                needed = expressionStack(let.initializer());
            } else if (statement instanceof Ast.Assign assign) {
                needed = expressionStack(assign.value());
            } else if (statement instanceof Ast.Print print) {
                needed = Math.max(1, 1 + expressionStack(print.value()));
            } else if (statement instanceof Ast.Return returnStatement) {
                needed = expressionStack(returnStatement.value());
            } else if (statement instanceof Ast.If conditional) {
                needed = Math.max(expressionStack(conditional.condition()), Math.max(
                        statementStack(conditional.thenBranch()),
                        statementStack(conditional.elseBranch())));
            } else if (statement instanceof Ast.While loop) {
                needed = Math.max(expressionStack(loop.condition()),
                        statementStack(loop.body()));
            } else {
                throw new IllegalStateException("unknown statement " + statement.getClass());
            }
            maximum = Math.max(maximum, needed);
        }
        return maximum;
    }

    private static boolean statementsTerminate(List<Ast.Stmt> statements) {
        for (Ast.Stmt statement : statements) {
            if (statement instanceof Ast.Return) return true;
            if (statement instanceof Ast.If conditional
                    && statementsTerminate(conditional.thenBranch())
                    && statementsTerminate(conditional.elseBranch())) {
                return true;
            }
        }
        return false;
    }

    private static int expressionStack(Ast.Expr expression) {
        if (expression instanceof Ast.Literal || expression instanceof Ast.Variable) return 1;
        if (expression instanceof Ast.Unary unary) {
            int operand = expressionStack(unary.operand());
            return unary.operator() == TokenType.BANG ? Math.max(operand, 2) : operand;
        }
        if (expression instanceof Ast.Binary binary) {
            if (binary.operator() == TokenType.AND_AND
                    || binary.operator() == TokenType.OR_OR) {
                return Math.max(1, Math.max(expressionStack(binary.left()),
                        expressionStack(binary.right())));
            }
            return Math.max(expressionStack(binary.left()),
                    1 + expressionStack(binary.right()));
        }
        throw new IllegalStateException("unknown expression " + expression.getClass());
    }

    private static final class Label {
        private int position = -1;
        private final List<Integer> fixups = new ArrayList<>();
    }

    private static final class CodeBuffer {
        private final Ast.Pos failurePos;
        private byte[] bytes = new byte[256];
        private int size;

        CodeBuffer(Ast.Pos failurePos) {
            this.failurePos = failurePos;
        }

        void u1(int value) {
            ensure(1);
            bytes[size++] = (byte) value;
        }

        void u2(int value) {
            ensure(2);
            bytes[size++] = (byte) (value >>> 8);
            bytes[size++] = (byte) value;
        }

        void branch(int opcode, Label target) throws CompileFailure {
            int opcodePosition = size;
            u1(opcode);
            u2(0);
            if (target.position >= 0) {
                patch(opcodePosition, target.position);
            } else {
                target.fixups.add(opcodePosition);
            }
        }

        void mark(Label label) throws CompileFailure {
            if (label.position >= 0) throw new IllegalStateException("label marked twice");
            label.position = size;
            for (int opcodePosition : label.fixups) patch(opcodePosition, label.position);
            label.fixups.clear();
        }

        byte[] toByteArray() {
            return Arrays.copyOf(bytes, size);
        }

        private void patch(int opcodePosition, int targetPosition) throws CompileFailure {
            int offset = targetPosition - opcodePosition;
            if (offset < Short.MIN_VALUE || offset > Short.MAX_VALUE) {
                throw CompileFailure.at("E_LIMIT", failurePos,
                        "generated branch exceeds signed 16-bit range");
            }
            bytes[opcodePosition + 1] = (byte) (offset >>> 8);
            bytes[opcodePosition + 2] = (byte) offset;
        }

        private void ensure(int additional) {
            int required = size + additional;
            if (required > bytes.length) {
                bytes = Arrays.copyOf(bytes, Math.max(required, bytes.length * 2));
            }
        }
    }

    private interface PoolEntry {
        void write(DataOutputStream out) throws IOException;
    }

    private record Utf8Entry(String value) implements PoolEntry {
        @Override public void write(DataOutputStream out) throws IOException {
            out.writeByte(1);
            out.writeUTF(value);
        }
    }

    private record IntegerEntry(int value) implements PoolEntry {
        @Override public void write(DataOutputStream out) throws IOException {
            out.writeByte(3);
            out.writeInt(value);
        }
    }

    private record OneIndexEntry(int tag, int index) implements PoolEntry {
        @Override public void write(DataOutputStream out) throws IOException {
            out.writeByte(tag);
            out.writeShort(index);
        }
    }

    private record TwoIndexEntry(int tag, int first, int second) implements PoolEntry {
        @Override public void write(DataOutputStream out) throws IOException {
            out.writeByte(tag);
            out.writeShort(first);
            out.writeShort(second);
        }
    }

    private static final class ConstantPool {
        private static final int MAX_ENTRIES = 65_534;
        private final Ast.Pos failurePos;
        private final List<PoolEntry> entries = new ArrayList<>();
        private final Map<String, Integer> indexes = new LinkedHashMap<>();

        ConstantPool(Ast.Pos failurePos) {
            this.failurePos = failurePos;
        }

        int utf8(String value) throws CompileFailure {
            return intern("U:" + value, new Utf8Entry(value));
        }

        int integer(int value) throws CompileFailure {
            return intern("I:" + value, new IntegerEntry(value));
        }

        int classInfo(String internalName) throws CompileFailure {
            String key = "C:" + internalName;
            Integer found = indexes.get(key);
            if (found != null) return found;
            return intern(key, new OneIndexEntry(7, utf8(internalName)));
        }

        int nameAndType(String name, String descriptor) throws CompileFailure {
            String key = "N:" + name + ":" + descriptor;
            Integer found = indexes.get(key);
            if (found != null) return found;
            return intern(key, new TwoIndexEntry(12, utf8(name), utf8(descriptor)));
        }

        int fieldRef(String owner, String name, String descriptor) throws CompileFailure {
            String key = "F:" + owner + ":" + name + ":" + descriptor;
            Integer found = indexes.get(key);
            if (found != null) return found;
            return intern(key, new TwoIndexEntry(9, classInfo(owner),
                    nameAndType(name, descriptor)));
        }

        int methodRef(String owner, String name, String descriptor) throws CompileFailure {
            String key = "M:" + owner + ":" + name + ":" + descriptor;
            Integer found = indexes.get(key);
            if (found != null) return found;
            return intern(key, new TwoIndexEntry(10, classInfo(owner),
                    nameAndType(name, descriptor)));
        }

        void write(DataOutputStream out) throws IOException {
            out.writeShort(entries.size() + 1);
            for (PoolEntry entry : entries) entry.write(out);
        }

        private int intern(String key, PoolEntry entry) throws CompileFailure {
            Integer found = indexes.get(key);
            if (found != null) return found;
            if (entries.size() >= MAX_ENTRIES) {
                throw CompileFailure.at("E_LIMIT", failurePos,
                        "constant-pool entry limit exceeded");
            }
            int index = entries.size() + 1;
            entries.add(entry);
            indexes.put(key, index);
            return index;
        }
    }
}
