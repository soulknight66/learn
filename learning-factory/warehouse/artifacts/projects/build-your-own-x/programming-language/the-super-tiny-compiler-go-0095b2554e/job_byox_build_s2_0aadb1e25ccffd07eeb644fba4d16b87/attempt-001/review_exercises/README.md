# Code-review exercises

Review the two small snippets as boundary code, not just for whether their happy
paths appear to work.

- `api_contract/` asks whether a convenience pipeline preserves the required
  EOF and error-type contracts.
- `vm_safety/` asks what assumptions an executor makes before indexing its code
  and stack slices.

For each, list concrete triggering inputs, affected requirements, and the tests
you would require before approval. Answers live only in each exercise's
`sealed/` directory.
