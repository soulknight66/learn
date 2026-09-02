package reference_tests

import (
	"strings"
	"testing"

	pf "example.com/prefixforge"
)

func BenchmarkTokenize(b *testing.B) {
	source := strings.Repeat("(add 1 (mul 2 3))\n", 500)
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if _, err := pf.Tokenize(source); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkCompileAndRun(b *testing.B) {
	source := strings.Repeat("(print 1) ", 50) + "(add 20 22)"
	program := parseSource(b, source)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		code, err := pf.Compile(program)
		if err != nil {
			b.Fatal(err)
		}
		if _, err := pf.Run(code, nil); err != nil {
			b.Fatal(err)
		}
	}
}
