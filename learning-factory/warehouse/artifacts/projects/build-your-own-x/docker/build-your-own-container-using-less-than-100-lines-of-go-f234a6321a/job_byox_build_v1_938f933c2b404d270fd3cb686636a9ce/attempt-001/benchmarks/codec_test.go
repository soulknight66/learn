package benchmarks_test

import (
	"os"
	"path/filepath"
	"testing"

	container "example.com/tinycontainer"
)

func benchmarkConfig(b *testing.B) container.Config {
	b.Helper()
	root := b.TempDir()
	if err := os.Mkdir(filepath.Join(root, "proc"), 0o755); err != nil {
		b.Fatal(err)
	}
	cfg := container.DefaultConfig()
	cfg.RootFS = root
	cfg.Command = []string{"/bin/probe", "one", "two"}
	cfg.Environment = []string{"PATH=/bin", "A=1", "B=two words"}
	return cfg
}

func BenchmarkValidateConfig(b *testing.B) {
	cfg := benchmarkConfig(b)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := container.ValidateConfig(cfg); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkParseChildArgs(b *testing.B) {
	args := container.EncodeChildArgs(benchmarkConfig(b))
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := container.ParseChildArgs(args); err != nil {
			b.Fatal(err)
		}
	}
}
