# Comprehension Check

Validation label: LEARNER_SAFE · QUESTIONS_ONLY · NO_ANSWERS_OR_SCORING

Answer all five prompts in COMPREHENSION_RESPONSES.md. Show intermediate reasoning where requested. Use the fact encoding and semantics from STUDY_TASK.md.

## Assessment graph

Use this graph for Questions 1 and 2:

    {
      "entry": "A",
      "blocks": [
        {
          "id": "A",
          "statements": [
            {"id": "a1", "defines": "x", "uses": []},
            {"id": "a2", "defines": "y", "uses": ["x"]}
          ],
          "successors": ["B", "C"]
        },
        {
          "id": "B",
          "statements": [
            {"id": "b1", "defines": "x", "uses": ["y"]}
          ],
          "successors": ["D"]
        },
        {
          "id": "C",
          "statements": [
            {"id": "c1", "defines": "z", "uses": ["x"]}
          ],
          "successors": ["D"]
        },
        {
          "id": "D",
          "statements": [
            {"id": "d1", "defines": "y", "uses": ["x"]}
          ],
          "successors": ["B", "E"]
        },
        {
          "id": "E",
          "statements": [
            {"id": "e1", "defines": null, "uses": ["x", "y", "z"]}
          ],
          "successors": []
        }
      ]
    }

## Questions

### 1. Fixed point through a loop

Compute the least fixed point. Give the sorted IN and OUT fact sets for D and E. Show at least two worklist moments that demonstrate why one pass over block order is insufficient.

### 2. May is not must

At the point immediately before e1, group the reaching definitions by the variables x, y, and z. Is a nonempty reaching-definition set for z proof that z was initialized on every path to e1? Justify your answer with a concrete path in the graph, then name the join operation and boundary idea you would investigate for a definite-initialization analysis.

### 3. Termination argument

Give a short termination proof for this implementation on any valid finite input. Identify the finite domain, the direction in which states move, and a valid upper bound in terms of R reachable blocks and D definition facts on the number of successful fact insertions into all IN states. Explain why that bound does not by itself bound careless queue operations.

### 4. Scheduling and determinism

Suppose one correct implementation uses a FIFO worklist and another uses a deterministic reverse-postorder priority. Under what conditions must they compute the same result? State one likely performance difference and one source of accidental nondeterminism that an engineer must remove.

### 5. Failure as an interface property

An input names successor Missing, and OUTPUT.json already contains a sentinel result from a prior successful run. Specify the observable exit status, diagnostic behavior, and file-state behavior required by the task. Then outline one automated test that establishes all three without depending on the machine's working directory.

## Provenance

These questions were authored for this kickoff and contain no extracted lecture or textbook content. Catalog basis: CSDIY snapshot commit adce8e13789dc16aa6d1fbe163e9541736defae4, content SHA-256 5c26f67523735d0b6f94bd684d945d637207e18ad98e7ca8268df6c70bc434fd.
