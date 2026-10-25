# Optional parallel production

Parallel production is an execution optimization, not a mandatory creative
stage. Use it only when the user authorizes multiple agents and the interfaces
are already stable.

## Preconditions

- Master clock and shot IDs are locked.
- Asset interfaces and output paths are fixed.
- Each worker has an independent output directory or code worktree.
- The shared timeline, project state, and final render entry have one owner.
- Each task has explicit acceptance criteria and a stop budget.

Do not parallelize while the story, duration, shot order, or asset design is
still changing.

## Task contract

Each worker receives:

```text
goal
scope
input files and versions
owned outputs
files that must not be modified
acceptance criteria
budget and stop condition
```

Each worker returns:

- artifact paths;
- command or model parameters;
- candidate/generation records;
- evidence and review results;
- known failures and unresolved risks;
- what must be merged or re-tested.

## File ownership

- Separate shots use separate scene and output files.
- Code workers use separate worktrees when they edit overlapping source trees.
- Only the main agent merges `timeline.json`, final composition, and delivery
  manifests.
- Never have two workers write the same timeline, project state, final render,
  or source asset.

## Merge gate

The main agent verifies every returned artifact, checks its hash and declared
scope, merges only selected takes, re-runs the complete program review, and
revalidates the final delivery. A worker's self-reported success is not final
acceptance.
