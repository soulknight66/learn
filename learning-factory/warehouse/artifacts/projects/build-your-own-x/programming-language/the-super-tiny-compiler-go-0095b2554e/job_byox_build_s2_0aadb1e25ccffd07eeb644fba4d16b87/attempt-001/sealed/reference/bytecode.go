package prefixforge

import (
	"fmt"
	"strings"
)

type OpCode string

const (
	OpPushNumber OpCode = "PUSH_NUMBER"
	OpPushString OpCode = "PUSH_STRING"
	OpPushBool   OpCode = "PUSH_BOOL"
	OpAdd        OpCode = "ADD"
	OpSub        OpCode = "SUB"
	OpMul        OpCode = "MUL"
	OpDiv        OpCode = "DIV"
	OpLT         OpCode = "LT"
	OpEQ         OpCode = "EQ"
	OpNot        OpCode = "NOT"
	OpConcat     OpCode = "CONCAT"
	OpJump       OpCode = "JUMP"
	OpJumpFalse  OpCode = "JUMP_IF_FALSE"
	OpJumpTrue   OpCode = "JUMP_IF_TRUE"
	OpPrint      OpCode = "PRINT"
	OpPop        OpCode = "POP"
	OpHalt       OpCode = "HALT"
)

type Instruction struct {
	Op      OpCode
	Number  int64
	Text    string
	Boolean bool
	Target  int
	At      Span
}

type Bytecode struct {
	Code     []Instruction
	MaxStack int
}

func (b Bytecode) String() string {
	var out strings.Builder
	for i, ins := range b.Code {
		fmt.Fprintf(&out, "%04d %-14s", i, ins.Op)
		switch ins.Op {
		case OpPushNumber:
			fmt.Fprintf(&out, " %d", ins.Number)
		case OpPushString:
			fmt.Fprintf(&out, " %q", ins.Text)
		case OpPushBool:
			fmt.Fprintf(&out, " %t", ins.Boolean)
		case OpJump, OpJumpFalse, OpJumpTrue:
			fmt.Fprintf(&out, " %04d", ins.Target)
		}
		out.WriteByte('\n')
	}
	return out.String()
}
