# Packaging & developer experience — Tasks

**Status:** Tasks — under review.
**Spec:** [`spec.html`](spec.html). **Plan:** [`plan.html`](plan.html).

Four tasks, labelled by repo. Tasks 1–3 land in `e-footprint`; Task 4 in `e-footprint-interface`.
The plan's "policy docs" and "PEP 621 migration" items are merged into Task 1 — they're the same
deliverable (state the support policy, in metadata *and* in prose) with no pause point between them.

## Task 1 — Support policy: PEP 621 migration + docs — repo: `e-footprint`

**Goal:** Declare the Python support policy in both metadata and prose. Migrate `pyproject.toml` to the
PEP 621 `[project]` layout (which lets us curate classifiers so they reflect the *tested* set), and
state the rolling-window policy in the README and tech stack.

**Files touched:**
- `pyproject.toml` — move project metadata + the 12 runtime dependencies into `[project]`, translating
  carets to PEP 508 (`^0.25` → `>=0.25,<0.26`, `^2` → `>=2,<3`, `2024.1` → `==2024.1`, …); set
  `requires-python = ">=3.12,<4.0"` and curated `classifiers` (3.12, 3.13). Keep
  `[tool.poetry.group.dev]`, `include`/`packages`, and `[build-system]` as-is.
- `README.md`, `specs/tech_stack.md` — state the policy: rolling window, floor `>=3.12`, no upper cap,
  supported = 3.12 + 3.13 today, next minor added when its wheels land.
- `CHANGELOG.md` — entry.

**Tests added/changed:**
- None (metadata/build change). Verification is by inspection, not pytest.

**Acceptance:**
- `poetry export` / `poetry.lock` resolves the **same dependency set** before vs after the migration
  (the guard against a caret-mistranslation).
- `poetry build` succeeds under Poetry ≥2.0; the built wheel METADATA shows
  `Requires-Python: >=3.12,<4.0` and **exactly** classifiers 3.12 + 3.13 (no auto-generated 3.14).
- README + `tech_stack.md` state the support policy.

**Depends on:** none.

---

## Task 2 — Library CI matrix — repo: `e-footprint`

**Goal:** Run the test suite on every push/PR across the supported Python versions, so "supported"
means "tested." Subsumes the roadmap's planned single-version CI item.

**Files touched:**
- `.github/workflows/ci.yml` (new) — matrix on Python 3.12 + 3.13; `poetry install --with dev`;
  `pytest` with `MPLBACKEND=Agg`; cache the Poetry venv.
- `CHANGELOG.md` — entry.

**Tests added/changed:**
- The workflow runs the existing suite; no new unit tests. (`mkdocs build --strict` is intentionally
  deferred to the SSOT-metadata roadmap item.)

**Acceptance:**
- CI triggers on push/PR, runs green on both 3.12 and 3.13.

**Depends on:** none (uses the version set Task 1 documents; can land in parallel).

---

## Task 3 — Docker image + release publish — repo: `e-footprint`

**Goal:** A one-command, toolchain-independent way to run a model, published on each release.

**Files touched:**
- `Dockerfile` (new) — `python:3.12-slim`, `pip install efootprint`, entrypoint `python`.
- `.github/workflows/docker-publish.yml` (new) — build and push `boavizta/efootprint` to Docker Hub on
  a release tag (needs `DOCKERHUB_*` repo secrets — note as a prerequisite).
- `README.md` ("Run with Docker"), `RELEASE_PROCESS.md` (publish step).
- `CHANGELOG.md` — entry.

**Tests added/changed:**
- A build-and-smoke step in the workflow (image builds; `docker run … python /work/script.py` runs a
  trivial model).

**Acceptance:**
- `docker build` produces an image; `docker run --rm -v "$PWD":/work boavizta/efootprint python /work/build_model.py`
  computes a footprint with no local Python setup.
- On a release tag, the image is published to Docker Hub as `boavizta/efootprint`.

**Depends on:** none (the image installs from PyPI; for pre-release testing it can install the current
published version).

---

## Task 4 — Interface CI pin bump — repo: `e-footprint-interface`

**Goal:** Fix the stale interface CI pin so it tests the Python it actually declares.

**Files touched:**
- `e-footprint-interface/.github/workflows/ci.yml` — replace the `3.10.12` pin with a 3.12 + 3.13 matrix.
- `e-footprint-interface/CHANGELOG.md` — entry.

**Tests added/changed:**
- Existing interface suite runs under the new matrix; no new tests.

**Acceptance:**
- Interface CI runs green on 3.12 (and 3.13); no `3.10.12` pin remains.

**Depends on:** none.

---

## Ordering rationale

**Task 1** merges the policy docs and the PEP 621 migration: they're one deliverable (the curated
`[project].classifiers` *are* the metadata half of the support statement, and the README is the prose
half), and the lockfile-diff acceptance check makes the risky part (dep translation) self-contained and
reviewable in the same PR. **Tasks 2, 3, 4** are independent infrastructure with their own files and
triggers (test-on-push vs build-on-release vs a different repo) — kept separate for independent
reviewability and parallel landability rather than split by directory. Nothing hard-blocks anything:
2/3/4 align with the version set Task 1 documents but don't import its changes.
