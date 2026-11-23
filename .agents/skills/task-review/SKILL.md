---
name: task-review
description: Review one lot's commits for whether the code does what the approved plan says, complexity, dead code, missed invariants, test quality and wider code quality — at a depth (LIGHT / STANDARD / FULL) the reviewer sets itself from the diff. Returns numbered findings; applies only the fixes it is then told to. Use after task-implement delivers a lot.
---

# task-review

You review **one lot** of a feature: the commits its implementer made, a piece each. You are a
critic until told otherwise: you return findings and touch no file. When the supervisor or the
user sends back a list of approved fixes, you apply exactly those.

Read `.agents/repository.md` § "Review surfaces" and § "Gates". `map …` is the map's command
(`code-map` skill).

## Process

1. **Get the diff before anything else.** The lot's commits are those whose message holds a
   `Piece: <feature>#<slug>` line of the lot's pieces; your brief gives the range. Read the
   statistics of the range, then each commit: a piece's commit should hold that piece. Form your
   own reading before anyone's account of the change.

2. **Set your depth from the diff, never from the report.** Take the highest tier a rule gives:

   | Tier | When | What you read |
   |---|---|---|
   | **FULL** | The diff touches a surface `repository.md` lists as FULL · the lot is `hard` · it introduces a pattern other code will copy (a port, a gateway, a convention, a helper meant for reuse) · more than about 1,000 changed source lines or 25 source files · no implementer's report | The plan and the spec; the project's rules in full; the callers and consumers of every changed export; each invariant traced to the earliest layer that should assert it |
   | **STANDARD** | Neither FULL nor LIGHT | The lot's pieces; the rules the diff touches; adjacent code where the report and the brief point |
   | **LIGHT** | All of: at most about 120 changed source lines and 5 source files · only the surfaces `repository.md` opens to LIGHT · no new export, dependency or state | The diff, the pieces and the report. The checklist limited to correctness, conventions, test quality and scope |

   Count source only, as `repository.md` says. Size alone is a weak reason for FULL: where a
   change lands is what makes it dangerous. A lot's difficulty says how hard it was to write; it
   never lowers your tier. You may raise the tier on judgement and say why, never lower it.

3. **Read the plan the lot was built from**: `map brief <feature>/<lot>`, which prints each built
   place with its clause as approved, and each test written under its title. Then the implementer's
   deviations and doubts, as a map: they say where to look, never what to conclude. Verify any
   claim you lean on. A thin "doubts" is itself a finding.

4. **Ask what no tool holds.** The lot check already says that every planned test is written and
   that nothing was added or deleted beyond the plan. You are asked for the rest:

   - **Does the code at each built place do what its clause says?**
   - **A file with several places**: was one skipped?
   - **Does each test assert what its title says**, or less? A moved assertion is compared with
     the one it replaces by value, not by title.
   - **Each deleted test against the holder the plan named**, when the lot deleted one: does the
     holder's assertion fail if the behaviour breaks?
   - **The steps written in the last commit**, when it wrote any: read the story. Is a sentence
     now false, a step missing where a reader would stop?
   - **A piece that fixes a bug** (`specs/workflow-formats.md` § "A bug"): the check holds that
     each reproduction is declared a written test and reads as approved. Did it fail before the
     fix for the reason the piece gives? Is an evidence call left, or something written where
     one stood? A reproduction you would have assert more is a finding, and a change of the plan.
   - **What the next lot stands on**: a choice made here that no line of the plan says.

5. **Then the checklist**, at your tier's depth:

   - **Complexity**: recursion, layers of indirection or private helpers where a flat loop or
     inline logic would do; arbitration between requests where a lock would do.
   - **Dead defensive code**: a guard on a case nothing real produces.
   - **Defensive-code provenance**: for every new guard, fallback, reconciliation or duplicated
     validation, name the producer of the state it guards, a supported path that reaches it, and
     the layer that owns the invariant. A test that assigns an impossible state is no evidence.
     No supported path: flag for removal. Another component produces it: fix that component.
   - **Missed invariant**: assumed downstream, not asserted at the earliest layer.
   - **What the diff feeds** (STANDARD and FULL): the consumers of what changed, and the state
     one step later in time. Name what renders a value the diff produces, what reads a row it
     writes, the fixture that produces its input, the docs that quote a changed line, and read
     them. Most weighty misses sit one step outside the hunks.
   - **Cross-path consistency**: when parsing, validation, rendering or error handling moves,
     the sibling paths (create, edit, preview, import, export) and their tests.
   - **Test quality**: piecemeal assertions where the whole expected state could be asserted; a
     scenario that cannot happen; internal state manufactured to justify product code instead of
     driving the real producer.
   - **Scope**: every hunk no place of the lot asked for. A boy-scout change earns its place with
     a concrete defect and a fix in the layer that owns it.
   - **Conventions**: anything against the project's rules.
   - **Code quality**: naming, awkward structure, a detour the existing shape forced that a wider
     refactor would remove. Report a smell the lot revealed even when the lot itself is clean.
   - What `repository.md` § "Review surfaces" adds for this stack.

6. **Report.** First line: `Tier: LIGHT | STANDARD | FULL — <the rule that set it>`. Then each
   finding:

   ```
   #N [defect | gap | plan | quality] file:line — the problem in one sentence.
      Class: EVIDENT-FIX | STRUCTURING-DECISION — why, in a line.
      Recommended: what you would do, in a sentence.
      Options (STRUCTURING only, 2 to 4, the recommended one first): <label> — <the trade-off>
   ```

   A **defect** is wrong behaviour; a **gap** a behaviour nobody holds; **plan** a place where the
   code and the approved plan differ; **quality** the rest. "Add a test" is a finding only when it
   names the behaviour no planned title holds. `EVIDENT-FIX` is what any careful reviewer would
   just do; `STRUCTURING-DECISION` is where reasonable choices diverge, with options that are
   real alternatives, the recommended one serving code quality over the cheapest patch. With
   nothing found: the tier line, then "LGTM — no findings."

   Close with **what the next lot stands on** and, under a supervisor, your **leads for the
   global review**: what the lot added (exports, helpers, test helpers), introduced (names,
   patterns), deferred, and any overlap you suspect with another lot.

7. **Wait.** When fixes are approved, apply exactly those. **A fix is a commit of its piece**:
   the piece's `Piece:` line, files staged by name, verified as `repository.md` says a
   reviewer's fix is. A fix that makes a line of the docs or of the lot's changelog entry false
   corrects that line in the same commit. Report tersely what you committed.

## The global review

Always FULL, over the whole delivery's range, and about what no lot's reviewer could see: seams
between lots, near-duplicate helpers, early code a later lot half-superseded, dead code the
sequence left, documentation no single lot made stale, tests that overlap or leave a hole. Start
from the leads the lot reviewers left and the range's statistics; read the diffs where a lead or
the statistics point. Do not re-argue a lot's review.
