# Design questions

Write down your answers before implementing each stage. These prompts intentionally do not include
model answers.

## Interface

1. Which output is intended for programs, and which belongs on stderr?
2. Why is the literal `--` useful even though the command must be absolute?
3. Which exit code should the controller return when the isolated command fails?

## Filesystem and paths

1. At what exact point must a container name be validated?
2. How will you prove that deletion cannot escape `ROOT/containers`?
3. What observable difference distinguishes copying `ROOTFS` from copying its contents?
4. What happens if copying fails halfway through?

## Lifecycle and races

1. What operation lets exactly one concurrent mutation claim a name?
2. When should the lock be released during a long-running `run` operation?
3. What should a second `run` observe while the first command is active?
4. Which failures can still leave stale state after an uncatchable process termination?

## Isolation

1. Why do a new PID namespace and a private `/proc` need to be used together?
2. Which guarantees come from changing root, and which do not?
3. Why can a machine have `unshare` installed but reject the real runner?
4. What additional controls would be required before accepting hostile input?

## Testing

1. How can a fake runner show that `"two words"` stayed one argument?
2. Which state transitions can be tested without kernel namespace support?
3. How would you make a race test deterministic enough to be useful?
