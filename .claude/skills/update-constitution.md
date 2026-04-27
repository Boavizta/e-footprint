---
name: update-constitution
description: Use when the user wants to change specs/constitution.md. Constitutional changes go in their own commit, with explicit justification, separate from feature work.
---

# update-constitution

You are about to amend the constitution. Constitution changes are deliberate and rare.

## Process

1. **Read the current `specs/constitution.md`** in full.

2. **Confirm the proposed change** with the user. Ask:
   - What rule is being added, removed, or modified?
   - **Why now?** What past pain or future risk justifies amending the constitution?
   - What downstream artifacts (`architecture.md`, `conventions.md`, CI tests, mkdocs pages) need to follow?

3. **Apply the change** to `specs/constitution.md`. Keep it short — the constitution is supposed to grow slowly. If a rule is more conditional than absolute, suggest moving it to `conventions.md` instead.

4. **Update downstream artifacts** the user identified.

5. **Stage and commit separately.** Constitutional changes do not blend into a feature commit. Recommended commit message format: `[constitution] <short summary>`.

## Constraints

- Don't add a rule that contradicts existing rules without resolving the contradiction.
- Don't add aspirational rules that are routinely broken — those belong in `conventions.md` (strong preference) or `roadmap.md` (planned).
- The constitution is hard rules only. If a "rule" comes with caveats and exceptions, it isn't constitutional.
