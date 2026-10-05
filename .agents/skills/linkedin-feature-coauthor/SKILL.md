---
name: linkedin-feature-coauthor
description: Co-author an e-footprint feature highlight or release post for LinkedIn together with a captioned demo video outline. Use for editorial drafting, not recording or publishing.
---

# LinkedIn feature co-authoring

Work from the maintainer's story and first video outline. The story may explain a hard modeling problem, a practical decision, or another reason the feature matters; do not force a difficulty narrative.

## Start with the author

Ask for (1) the story or angle they want to tell, (2) their rough video flow, and (3) **which image they want as the video's LinkedIn thumbnail** before researching or drafting. A few sentences or unordered beats are enough for the story and flow. If any answer is already in the request or current conversation, ask only for what is missing. Wait for the story and flow rather than inventing them; if the author has no thumbnail in mind, propose a concrete frame or image from the outline for their choice.

## Ground and shape the video flow

Use the supplied story and flow as the starting point. Read available previous LinkedIn posts for voice and format, the communication strategy for channel positioning, and the interface design hub (`specs/design/index.html`) for product understanding. Follow its pointer to the relevant journey; inspect documentation or code only far enough to check claims that matter to this piece. Verify numerical comparisons against the example model when used. Distinguish the feature's broader capability from the illustrative angle chosen for the post or video.

Propose an exhaustive, ordered video outline before writing the post. Show every planned on-screen action (including scrolls, hovers, clicks, control changes, and transitions) and **every visible caption with its exact proposed wording**. Number the captions and state which actions happen while each remains on screen; include actions without captions and off-camera preparation. Record the chosen thumbnail image alongside the outline; it need not be the video's opening frame. Do not collapse multiple captions into a single thematic "caption point." Preserve the author's intended sequence and example while making transitions and claims clear. Keep captions short, one idea at a time, and avoid narrating obvious clicks. Open with the feature and what it enables; close on its benefit. Use no narration unless requested.

**Wait for the author's validation of the full action-and-caption sequence before drafting the LinkedIn post.** Incorporate their corrections into the outline first. If recording later calls for additional or changed captions or visible actions, show the revised sequence for validation before producing the video.

## Draft and revise the post

After validation, draft a concise post that tells the supplied story and explains the feature's value. Give newcomers a brief explanation of what e-footprint is and does. Across the next five or six feature posts, vary that context's wording and angle so readers gradually learn the tool without repeated boilerplate. Make a new feature's novelty clear and explain any specialist term needed to understand it. End with a brief description of what the video shows and, when natural, a concrete invitation to watch or try the feature; the post should stand on its own rather than transcribe the video. Use previous posts as style references and honor the author's channel and voice. Use LinkedIn-compatible spacing, selective Unicode emphasis, symbols or emoji when they improve reading; keep paragraph breaks at meaningful shifts rather than after every sentence. Do not add hashtags, dramatic hooks, or engagement questions by formula.

Read the latest draft before every revision, especially after the author edits it. Preserve wording and structure they explicitly favor, and change only what their feedback calls for. Treat maintainer experience as their account; ground technical mechanisms and numerical claims in the project. Never claim a feature is the first or only one of its kind without support.

Save video outlines and posts in the interface repository's `communications/linkedin/` area, the single LinkedIn authoring home. Prefix each post-specific Markdown filename with its planned post date as `YY-MM-DD <slug>.md` (for example, `26-10-05 sankey.md` and `26-10-05 sankey-outline.md`); use the editorial calendar date or ask the author if it is unknown. Keep shared files such as `README.md` and `backlog.md` undated. Cross-repo modeling facts may need the companion library. Follow a specified worktree. Recording, editing, and publication are separate tasks.
