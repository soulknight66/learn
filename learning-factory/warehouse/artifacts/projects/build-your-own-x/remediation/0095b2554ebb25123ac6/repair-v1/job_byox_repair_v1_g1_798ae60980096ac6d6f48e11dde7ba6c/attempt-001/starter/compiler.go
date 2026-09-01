package pebble

// Scan converts source bytes into positioned tokens, including one final EOF.
func Scan(source string) ([]Token, error) {
	return nil, notImplemented(StageScan)
}

// Parse builds an AST from a complete token stream.
func Parse(tokens []Token) (Program, error) {
	return Program{}, notImplemented(StageParse)
}

// Analyze resolves names and assigns dense local slots.
func Analyze(program Program) (*Analysis, error) {
	return nil, notImplemented(StageAnalyze)
}

// Compile lowers an analyzed program to stack-machine bytecode.
func Compile(program Program, analysis *Analysis) (Bytecode, error) {
	return Bytecode{}, notImplemented(StageCompile)
}

// ValidateBytecode checks structural safety without executing instructions.
func ValidateBytecode(code Bytecode) error {
	return notImplemented(StageValidate)
}

// Run validates and executes bytecode with fresh VM state.
func Run(code Bytecode) ([]int64, error) {
	return nil, notImplemented(StageRun)
}

// Build runs the source-to-bytecode pipeline.
func Build(source string) (Bytecode, error) {
	tokens, err := Scan(source)
	if err != nil {
		return Bytecode{}, err
	}
	program, err := Parse(tokens)
	if err != nil {
		return Bytecode{}, err
	}
	analysis, err := Analyze(program)
	if err != nil {
		return Bytecode{}, err
	}
	return Compile(program, analysis)
}

// Execute builds, validates, and runs a Pebble source program.
func Execute(source string) ([]int64, error) {
	code, err := Build(source)
	if err != nil {
		return nil, err
	}
	return Run(code)
}
