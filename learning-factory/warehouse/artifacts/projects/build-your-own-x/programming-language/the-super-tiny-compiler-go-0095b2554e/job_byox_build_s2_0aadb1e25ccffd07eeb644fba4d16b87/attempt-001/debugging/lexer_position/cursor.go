package cursor

type Position struct {
	Offset int
	Line   int
	Column int
}

func Advance(position Position, consumed byte) Position {
	position.Offset++
	position.Column++
	if consumed == '\n' {
		position.Line++
		position.Column = 0 // BUG: the next byte should be at one-based column 1.
	}
	return position
}
