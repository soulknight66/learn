package cursor

import "testing"

func TestAdvanceAcrossNewline(t *testing.T) {
	got := Advance(Position{Line: 1, Column: 4, Offset: 3}, '\n')
	want := (Position{Line: 2, Column: 1, Offset: 4})
	if got != want {
		t.Fatalf("position = %+v, want %+v", got, want)
	}
}
