# Design questions

Answer these before or during implementation. They are prompts, not requirements beyond the
contract in `REQUIREMENTS.md`.

## Frames

1. Which fields must change together on allocation and free?
2. How do you distinguish exhaustion from frame zero, which is a valid result?
3. Why is a double free an invariant violation rather than an idempotent operation?

## Processes

1. Should the scheduler cursor mean “currently running” or “most recently chosen”? What happens
   when that process blocks between scheduling calls?
2. Which states count as live when deciding whether a slot can be reused?
3. How do you ensure an old PID never aliases a newly spawned process?

## Virtual memory

1. In what order should duplicate checks, slot checks, and physical allocation occur?
2. Why does translation preserve the low 12 address bits for a 4096-byte page?
3. What cleanup is necessary if a later step fails after a frame has been acquired?

## Filesystem

1. How can name validation avoid reading past the fixed maximum?
2. Should an undersized read copy a prefix or fail atomically? What does the contract choose?
3. Which bytes should be cleared on unlink, and which clearings are security hardening rather than
   required observable behavior?

## Integration

1. What properties can host tests establish that an ELF-format check cannot, and vice versa?
2. What hardware initialization would be needed before this could safely enable interrupts?
