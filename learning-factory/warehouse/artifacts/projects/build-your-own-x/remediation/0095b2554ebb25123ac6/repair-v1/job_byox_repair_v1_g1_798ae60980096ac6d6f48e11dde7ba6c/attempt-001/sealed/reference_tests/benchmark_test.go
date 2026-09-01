package referencetests_test

import (
	"strings"
	"testing"

	pebble "example.com/pebble-reference"
)

func benchmarkSource(statementCount int) string {
	var builder strings.Builder
	for i := 0; i < statementCount; i++ {
		builder.WriteString("(+ 123 (* 45 67))\n")
	}
	return builder.String()
}

func BenchmarkScanMediumProgram(b *testing.B) {
	source := benchmarkSource(500)
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if _, err := pebble.Scan(source); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkBuildMediumProgram(b *testing.B) {
	source := benchmarkSource(500)
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if _, err := pebble.Build(source); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkRunMediumProgram(b *testing.B) {
	code, err := pebble.Build(benchmarkSource(500))
	if err != nil {
		b.Fatal(err)
	}
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := pebble.Run(code); err != nil {
			b.Fatal(err)
		}
	}
}
