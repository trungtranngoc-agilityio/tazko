---
name: prototype-compare
description: Screenshot a Tazko screen next to the matching prototype screen in light and dark, and list visible differences. Use in the verify step of every milestone and after any UI task.
---
1. Start the API: `uv run --project backend tazko serve` (dev data seeded by `uv run --project backend tazko admin seed-demo`).
2. For each screen in docs/milestones/<Mx>.md:
   - Open the prototype screen with tools/h.mjs (design/tazko-prototype.html, same route hash).
   - Open the same screen in the web app at http://localhost:5173 (`npm --prefix frontend run dev`, API on :8791).
   - Take both screenshots at 1280x800, light and dark, into docs/screens/<Mx>/.
3. Compare: layout, spacing, text, icons, states (empty, loading, error, read-only), keys.
4. Write a table in docs/milestones/<Mx>.md under "Visual check": screen, theme, difference, fixed?
Differences listed in design/KNOWN-DEVIATIONS.md are expected and must stay different.
