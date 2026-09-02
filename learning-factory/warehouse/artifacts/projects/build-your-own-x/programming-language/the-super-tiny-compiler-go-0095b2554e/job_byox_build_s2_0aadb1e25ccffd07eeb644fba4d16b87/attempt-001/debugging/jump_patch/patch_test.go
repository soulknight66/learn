package jump

import "testing"

func TestFalseJumpTargetsFirstElseInstruction(t *testing.T) {
	code := make([]Instruction, 8)
	PatchIf(code, 1, 4, 5, 7)
	if code[1].Target != 5 {
		t.Fatalf("false target = %d, want first else instruction 5", code[1].Target)
	}
	if code[4].Target != 7 {
		t.Fatalf("end target = %d, want 7", code[4].Target)
	}
}
