package reference_tests

import (
	"bytes"
	"fmt"
	"math/rand"
	"testing"

	pf "example.com/prefixforge"
)

func TestDeterministicDifferentialCorpus(t *testing.T) {
	sources := []string{
		"0", "-1", "true", `"hello"`,
		"(or true (eq (div 1 0) 0))",
		`(if (eq "x" "x") (concat "a" "b") "c")`,
		`(print "a") (print 2) (add 3 4)`,
	}
	rng := rand.New(rand.NewSource(20260902))
	for i := 0; i < 100; i++ {
		sources = append(sources, generatedNumberExpr(rng, 4))
		sources = append(sources, generatedBoolExpr(rng, 4))
	}
	for _, source := range sources {
		t.Run(source, func(t *testing.T) { assertAgreement(t, source) })
	}
}

func assertAgreement(t testing.TB, source string) {
	t.Helper()
	program := parseSource(t, source)
	code, err := pf.Compile(program)
	if err != nil {
		t.Fatal(err)
	}
	var evalOut, vmOut bytes.Buffer
	evalValue, evalErr := pf.Evaluate(program, &evalOut)
	vmValue, vmErr := pf.Run(code, &vmOut)
	if (evalErr == nil) != (vmErr == nil) {
		t.Fatalf("error disagreement: eval=%v vm=%v", evalErr, vmErr)
	}
	if evalErr == nil && evalValue != vmValue {
		t.Fatalf("value disagreement: eval=%#v vm=%#v", evalValue, vmValue)
	}
	if evalOut.String() != vmOut.String() {
		t.Fatalf("output disagreement: eval=%q vm=%q", evalOut.String(), vmOut.String())
	}
}

func generatedNumberExpr(rng *rand.Rand, depth int) string {
	if depth == 0 || rng.Intn(4) == 0 {
		return fmt.Sprintf("%d", rng.Intn(21)-10)
	}
	left := generatedNumberExpr(rng, depth-1)
	right := generatedNumberExpr(rng, depth-1)
	op := []string{"add", "sub", "mul"}[rng.Intn(3)]
	return fmt.Sprintf("(%s %s %s)", op, left, right)
}

func generatedBoolExpr(rng *rand.Rand, depth int) string {
	if depth == 0 || rng.Intn(3) == 0 {
		if rng.Intn(2) == 0 {
			return "true"
		}
		return "false"
	}
	switch rng.Intn(4) {
	case 0:
		return fmt.Sprintf("(lt %s %s)", generatedNumberExpr(rng, depth-1), generatedNumberExpr(rng, depth-1))
	case 1:
		return fmt.Sprintf("(not %s)", generatedBoolExpr(rng, depth-1))
	case 2:
		return fmt.Sprintf("(and %s %s)", generatedBoolExpr(rng, depth-1), generatedBoolExpr(rng, depth-1))
	default:
		return fmt.Sprintf("(or %s %s)", generatedBoolExpr(rng, depth-1), generatedBoolExpr(rng, depth-1))
	}
}
