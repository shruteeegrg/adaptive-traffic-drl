# Git / PR Workflow

This project is tracked entirely through GitHub so that weekly logs can be
verified against actual commits, per the module's tracking requirements.

## Branching

- `main` — protected, always in a working state. Only updated via merged PRs.
- One branch per week: `week-01-env-setup`, `week-02-sumo-network`,
  `week-03-qtable-baseline`, etc. (see README for the week-by-week topics).
- If a week's work is large, it's fine to split it into a few smaller PRs
  into the same weekly branch, or straight into `main` — the point is
  granular, dated commits, not one big PR per week.

## Commits

- Commit as you go (ideally most days you work on the project), not once at
  the end of the week. Commit messages should be specific enough that the
  weekly log can be cross-checked against them, e.g.:
  - `feat(env): add TraCI wrapper for lane occupancy reads`
  - `fix(agent): correct target network update frequency`
  - `docs(logs): add week 3 log`

## Pull Requests

- Open a PR from the weekly branch into `main` at the end of each week (or
  incrementally, whichever fits).
- PR description template:

  ```
  ## Done this week
  - ...

  ## Planned for next week
  - ...

  ## Notes / blockers
  - ...
  ```

- Copy the same content into `logs/week-XX.md` so the log survives even if
  PRs are later squashed or the branch is deleted.
- Merge into `main` once the week's work is stable (doesn't need to be
  "finished" forever — a research project's code evolves).

## Collaborators

- `kcpawan@gmail.com` (supervisor) has been added as a collaborator with
  read/write access so progress can be reviewed directly in the repo,
  including PR history and commit timestamps.

## Weekly log rule

A weekly log is only valid if the work it describes is visible in this
repository (commits, PRs, or files) by the Monday submission. Logs
describing work not reflected in the repo will not be signed off, per the
module requirements.
