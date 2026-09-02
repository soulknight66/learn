package jump

type Instruction struct {
	Operation string
	Target    int
}

// PatchIf fills targets after both branch bodies have been emitted.
func PatchIf(code []Instruction, jumpFalse, jumpEnd, elseStart, end int) {
	code[jumpFalse].Target = elseStart + 1 // BUG: skips the else branch's first instruction.
	code[jumpEnd].Target = end
}
