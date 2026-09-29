# Journey: LOAN-12 on the Antigravity Interactions API path

This is a live run on 2026-09-29 (UTC) of one ticket, from issue to merged PR, with
`SDLC_MODE=interactions`. In stage-3 the fix is made by the **Antigravity agent through
the Gemini API Interactions API** (`antigravity-preview-09-2026`, preview).

How the fix step works:
- CI uploads the service code and the project rules into a **Google-hosted sandbox**, with
  no network egress.
- The agent edits and tests the code there, and CI reads the changed files back.
- The agent holds no credentials and has no access to the repo.

Identities on GitHub:
- **Developer** ([@robertoTerralogiq](https://github.com/robertoTerralogiq)) is a person.
- **Developer assistant** ([@developmentAssistant](https://github.com/developmentAssistant)) is the
  automated actor. It writes the first draft, posts the CI review and pushes the AI fixes. It has
  write access, but no admin rights and no `workflow` scope.

The merge gate has two requirements: `stage-4: merge-gate` must pass, and every conversation
must be resolved.

## Stages

| # | Stage | Who | What happened | Evidence |
| --- | --- | --- | --- | --- |
| 1 | Ticket | Developer | LOAN-12 filed | [#1](../../issues/1) |
| 2 | Implement | Assistant | First draft pushed and PR opened with auto-merge | [`1184fcf`](../../pull/2/commits/1184fcf), [#2](../../pull/2) |
| 3 | Review, run 1 | CI stage-2 (as assistant) | **8 findings, including blockers** ⇒ gate failed | [run](../../actions/runs/36510956644) |
| 4 | **ai-fix round 1** | CI stage-3, **Interactions API** | **Fixed 8/8** in the remote sandbox (295 s, 28 polls). Added `tests/conftest.py`. Tests went from 5 to 15 passed. Pushed as the assistant | [`3e2d6e3`](../../pull/2/commits/3e2d6e3) |
| 5 | Review, run 2 | CI stage-2 | **Resolved all 9 round-1 threads by itself.** 2 new blockers: the dummy `CORE_API_KEY`, once in `conftest.py` and once in a test module ⇒ gate failed | [run](../../actions/runs/36511534485) |
| 6 | **ai-fix round 2** | CI stage-3, **Interactions API** | Split decision: **fixed** the key in the test module, and **declined** the `conftest.py` one with a reason posted on its thread (326 s) | [`6091a81`](../../pull/2/commits/6091a81) |
| 7 | Review, run 3 | CI stage-2 | Resolved 1 more stale thread. The `conftest.py` blocker was still reported ⇒ gate failed | [run](../../actions/runs/36512150481) |
| 8 | Decision | Developer | Read the agent's argument ("a dummy default only feeds the test harness; production still fails fast"), agreed, and resolved the thread with a reason | [#2](../../pull/2) |
| 9 | ai-fix round 3 | CI stage-3 | It had already been queued before the decision. Changed nothing, consistent with round 2 (233 s) | same run |
| 10 | Review, re-run | CI stage-2 | 1 finding, **accepted by a person**, so not gating ⇒ **gate passed** | [run](../../actions/runs/36512150481) |
| 11 | Merge | GitHub auto-merge | Squash-merged, branch deleted, #1 closed | [`65f6f7c`](../../commit/65f6f7c) |

**Totals**
- About **23 minutes** from the PR opening to the merge.
- 3 fix rounds: 2 pushes and 1 deliberate no-change.
- 11 threads: 10 resolved by the re-reviews and 1 by the developer.
- No follow-up issues.
- Tests went from 5 to 15.
- There were no pipeline fixes during the run. The SDK and ADK runs had already
  found and fixed those issues.

## What this path shows

- **Strongest isolation.** The agent runs in Google's sandbox with no egress. It never sees
  the runner, the repo remote or any secret. The CI script, not the agent, decides what gets
  committed.
- **Least infrastructure.** No agent runtime is installed in CI, and no tools are written by
  hand. The whole engine is one API call plus reading the files back.
- **The slowest and most expensive of the three.** Each round took 4–6 minutes whatever its
  size, and 230 s even for a trivial probe. A local measurement of one round-1 fix used about
  **1.3 M tokens** (89 steps). Plan for a 25-minute deadline and a token cap
  (`agent_config.max_total_tokens`).
- **It is a preview.** While the engine was being built, one status poll without a timeout
  hung for about 15 hours, and cancelling a run returned HTTP 400. The engine now polls with a
  timeout and enforces its own deadline.
- **Its judgment was good.** It fixed what was real and argued its case on the one false
  positive, splitting a two-finding round into one fix and one reasoned decline.

## What was live, and what the stand-ins were

- **Live:** every GitHub action, CI run, Gemini review (`gemini-2.5-pro`) and Antigravity fix.
  The fix code in this PR was written by the agent; nobody typed it.
- **Stand-in:** the stage-2 first draft is the committed `demo/mr-fixture/`, with the defects
  planted on purpose.
