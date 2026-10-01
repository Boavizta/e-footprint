# Communications

Working assets for e-footprint's external communication. **Not** part of the published library, **not** part of the mkdocs site — these are internal-but-public working drafts.

## Scope

This folder is the brand-level home for e-footprint communications:

- **Strategy and foundations** — source of truth for all three actors (Boavizta, Publicis Sapient, Vincent):
  - `strategy.md` — the *why* and the per-actor rules (audiences, narrative rationale, coexistence rules). The authoritative reference; on any conflict, it wins.
  - `messaging-one-pager.md` — the shared narrative in one page (*what we say*: thesis, three differentiating messages, ready-to-use phrasings). All downstream pieces cite it rather than restate it.
  - `pitch-deck-outline.md` — *(planned)* outline for the shared 10-slide deck.
- **Editorial calendar** — `editorial-calendar.csv`. Single pipeline view across both repos.
- **Tool/method articles** — articles whose subject is the tool, the method, or the underlying modeling concepts. Lives in `articles/`.
- **Conference tracker** — `conferences/submissions.md`. CFP targets and submission status.

All LinkedIn post and video authoring, including tool and method highlights, lives in the interface repo at `e-footprint-interface/communications/`. Interface-feature articles and release notes live there too. The editorial calendar here references both repositories.

## Where things go

| Subject of the piece | Repo |
|---|---|
| Tool and method articles (web vs edge, user journeys, simulation) | `e-footprint/communications/` |
| Brand, strategy, messaging | `e-footprint/communications/` |
| Editorial calendar (single source) | `e-footprint/communications/editorial-calendar.csv` |
| All LinkedIn posts and videos; interface UI features, walkthroughs, release notes | `e-footprint-interface/communications/` |
| PS-branded client case studies | **Not in either repo.** PS-owned, lives in PS systems. |

For ambiguous articles, use the repository where the dominant subject lives. LinkedIn posts and videos always belong in the interface repository.

## Channels referenced

- `boavizta-blog` — articles published on Boavizta's site
- `boavizta-newsletter` — Boavizta's newsletter
- `linkedin-vincent` — Vincent's personal LinkedIn (dual-hat, see `strategy.md` §4)
- `linkedin-boavizta` — Boavizta's LinkedIn
- `linkedin-ps` — Publicis Sapient's corporate LinkedIn
- `mkdocs` — e-footprint documentation site
- External: `greenit-fr`, `devoxx`, etc.
