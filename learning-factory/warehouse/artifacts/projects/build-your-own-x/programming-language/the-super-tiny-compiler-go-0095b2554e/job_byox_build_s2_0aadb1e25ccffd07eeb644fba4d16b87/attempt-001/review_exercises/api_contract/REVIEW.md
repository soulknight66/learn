# Review: pipeline convenience function

```go
func Execute(source string, out io.Writer) (Value, error) {
    tokens, err := Tokenize(source)
    if err != nil { return Value{}, fmt.Errorf("bad input: %s", err) }
    tokens = tokens[:len(tokens)-1]
    program, err := Parse(tokens)
    if err != nil { return Value{}, err }
    code, err := Compile(program)
    if err != nil { return Value{}, err }
    return Run(code, out)
}
```

Questions: Which public invariants are broken? Which inputs panic? What error
introspection is lost? Propose focused tests and a minimal safe rewrite.
