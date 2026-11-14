# KRISHI-X pitch kit (PS 23)

| File | What it is |
|---|---|
| `index.html` | The 5-minute pitch deck (16 slides + 4 diagram appendix slides + credits). Theme: **pastel-dream** from garden-skills. |
| `PITCH-SCRIPT.md` | Steve Jobs-style script with a timing per slide, the sources for every number, and answers for judges' questions. |
| `diagrams.html` | Standalone page: farmer journey (UML sequence), system architecture, agent workflow, order lifecycle (UML state). |
| `diagrams.js` | Mermaid sources for the diagrams, shared by both pages. |
| `assets/shots/` | Screenshots of the running app (14 Nov 2026, live prices). |
| `assets/photos/` | Farmer and mandi photos from Wikimedia Commons (credits on the last slide). |
| `vendor/` | Mermaid and fonts, so everything works **offline** at the venue. |

## Presenting
Open `index.html` in Chrome or Edge (double-click works, no server needed) and press **F** for fullscreen.

- **→ / Space / click**: next (some slides reveal step by step) · **←**: back
- **N**: speaker notes (the script for this slide) · **T**: 5-minute timer (turns red after 5:00)
- Jump to a slide with `index.html#7`

## Refreshing the screenshots
With `docker compose up -d` running, open the app at http://localhost:3000 and take new screenshots into `assets/shots/` with the same file names.
