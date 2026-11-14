# KRISHI-X pitch kit (PS 23)

| File | What it is |
|---|---|
| `index.html` | The pitch deck: **7 slides** (organiser limit), built for 5 min incl. a 2-min live demo on slide 4. Theme: **pastel-dream** from garden-skills. |
| `KRISHI-X-Pitch.pptx` | The same 7 slides for PowerPoint, with the script and demo steps in each slide's speaker notes. Slides are images, so edit `index.html` and re-export for changes. |
| `PITCH-SCRIPT.md` | Timed script (5:00 incl. demo), the exact demo steps with a fallback, Q&A answers for the 3-min round, and sources for every number. |
| `diagrams.html` | For Q&A (not in the 7 slides): farmer journey (UML sequence), architecture, agent workflow, order lifecycle (UML state). |
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
