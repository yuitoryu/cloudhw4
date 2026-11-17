# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- Spec: `.scratch/<feature-slug>/spec.md`
- Implementation tickets: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`,
  one file per ticket, numbered from `01`.
- Triage state: a `Status:` line near the top of each issue file,
  using the role strings in `triage-labels.md`.
- Comments: append under a `## Comments` heading.

## Publishing and fetching

When a skill says "publish to the issue tracker", create the corresponding
file under `.scratch/<feature-slug>/`, creating directories as needed.

When a skill says "fetch the relevant ticket", read the referenced file.
The user will normally supply its path or issue number.

## Wayfinding operations

Used by `/wayfinder`. The map has one child file per ticket.

- Map: `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far, and Fog.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`,
  with the question in the body.
- Type: a `Type:` line containing `research`, `prototype`, `grilling`, or `task`.
- State: a `Status:` line; claimed tickets use `claimed`, completed tickets
  use `resolved`.
- Blocking: a `Blocked by: NN, NN` line near the top. A ticket is unblocked
  when every listed ticket is `resolved`.
- Frontier: scan for open, unblocked, unclaimed tickets; lowest number wins.
- Claim: set `Status: claimed` and save before starting work.
- Resolve: append the answer under `## Answer`, set `Status: resolved`,
  then append a gist and ticket link to Decisions-so-far in the map.
