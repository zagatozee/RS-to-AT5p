# AT5 Tone Switcher — Technical Handoff
*June 2026 — v0.5.0*

## v0.5.0 changes (Slopsmith schema compliance)

- `plugin.json` — `nav.screen` corrected to `"plugin-at5_tone"`, added `settings` field pointing to `settings.html`
- `settings.html` — NEW FILE. Settings panel (tier selector, noise gate, MIDI trigger offset) extracted from the plugin screen and moved here. Slopsmith injects this into the global Settings page automatically.
- `screen.html` — Settings tab removed (now in settings.html). Status / Tone Browser / Live Log tabs remain.
- `screen.js` — wrapped in IIFE `(function(){'use strict';...})()` per plugin conventions. Settings tab removed from tab switcher array.
- `routes.py` — uses `context["load_sibling"]` for rs_to_at5 loading (with importlib fallback). Uses `context["log"]` logger. `GET /settings` now returns `noise_gate` field.

## Key architectural notes

- Settings are now split: settings.html is shown in Slopsmith's Settings page; screen.html is the main plugin screen (Status/Tone Browser/Live Log).
- settings.html has its own inline `<script>` that fetches `/api/plugins/at5_tone/settings` on load and restores the UI state.
- The settings controls (at5SetTier, at5SetNoisegate, at5SetPrefire) are exposed on `window.*` from screen.js and called from settings.html.

## See v0.4.0 handoff for full architecture details
