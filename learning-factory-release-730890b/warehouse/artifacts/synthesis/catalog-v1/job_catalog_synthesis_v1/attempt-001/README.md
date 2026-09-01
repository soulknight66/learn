# Catalog synthesis v1

This deterministic artifact turns the normalized source catalogs into a complete priority backlog and a cross-source concept index.

- `BACKLOG.md` is the human-readable complete ranking.
- `BACKLOG.json` contains every score component, weight, and provenance record.
- `CONCEPT_MAP.md` is the human-readable concept index.
- `CONCEPT_MAP.json` contains memberships and inferred co-occurrence edges.
- `PROVENANCE.json` distinguishes source-derived and inferred material.

Validation replays generation against authoritative SQLite state. A passing `TESTED` claim covers deterministic completeness and internal consistency only; it does not mean the rankings received independent pedagogical review.
