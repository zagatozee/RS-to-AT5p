# Slopsmith AT5 Tone Switcher — Technical Handoff
*May 2026*

## Status

Working end-to-end. Live convert confirmed on CDLC songs. CC knob adjustments
confirmed firing. AT5 switching presets in response to MIDI PC messages.

---

## Architecture

```
Slopsmith (Docker)
  → playSong hook (screen.js)
  → _at5RequestLiveConvert()
      → POST /api/plugins/at5_tone/live_convert
      → rs_to_at5.py converter
      → writes AT5_LIVE_00..07.at5p to AT5 Presets/Converted/
  → _at5StartScheduler()
      → highway.getToneChanges() [CDLC]
        OR XML parse [songs with explicit tone schedule]
      → setInterval 100ms polling highway.getTime()
      → _at5Lookup(): live slots first, PC table fallback
      → HTTP POST → at5_midi_bridge.py (localhost:37432)
      → winmm → MIDI OUT → cable loop → MIDI IN → AT5
```

---

## Plugin Files

### screen.js — key behaviours

- `_at5RequestLiveConvert(filename)`: fires immediately on song load, parallel to scheduler
  - URL-decodes filename before sending to backend
  - Clears stale live slots from previous song before converting (mutates in-place — IIFE scope)
  - On success: populates `_at5LiveSlots` = { toneKey: pcNumber, ... }
- `_at5StartScheduler(filename)`: 800ms delay, retries `highway.getToneChanges()` up to 5x at 400ms intervals
  - If highway returns data: uses it as tone schedule, enriches unmapped tones via CDLC fallback endpoint
  - If no highway data: tries XML schedule parse, then falls back to first live slot as base tone at t=0
- `_at5Lookup(toneKey)`: checks `_at5LiveSlots` first, then `_at5PcTable`
- Three-tab UI: Status | Tone Browser | Live Log

### routes.py — key behaviours

- On startup: creates `AT5_LIVE_00..07.at5p` using the real `AT5P_TEMPLATE` from rs_to_at5
  (important — hand-rolled XML causes AT5 to crash on startup)
- `POST /live_convert`: locates PSARC via `context["get_dlc_dir"]()`, extracts tones via
  Slopsmith's `read_psarc_entries()`, converts via `rs_to_at5._convert_tone_from_gearlist()`,
  writes to slot files, returns `{"slots": {"ToneKey": 120, ...}}`
- PC table (optional): if `/scrape` is mounted and a CSV is present, builds a frequency-sorted
  table of pre-converted tones as fallback for songs not covered by live convert
- CC adjustments: when two tones share the same signal chain but differ in knob values,
  fires CC messages after the PC to adjust individual parameters

### rs_to_at5.py — key facts

- Must be in the plugin folder — routes.py imports it at runtime
- `_convert_tone_from_gearlist(tone_key, tone_name, gear, source_path, output_dir)`:
  the shared assembly function used by both live convert and CLI batch mode
- Supports RS+ JSON, RS2014 GearList JSON, and RS2014 `.tone2014.xml` formats
- 42 amps, 68 pedals, 17 rack effects mapped to AT5 GUIDs
- Knob values: Rocksmith 0-100 scale → AT5 0-10 (divide by 10)
- Amp knob param names include per-amp suffix (e.g. `Gain_JCM800AT4`) sourced from
  AT5 factory presets

---

## Live Convert — Confirmed Results

- KITN (RATM): 4 tones, JCM800 amp correct, knob values correct
- Tone switching firing at correct timestamps from `highway.getToneChanges()`
- AT5 confirmed re-reading `.at5p` files from disk on every PC trigger — no restart needed
- Typical conversion time: 30-100ms for 2-6 tones

---

## CC Map (confirmed via MIDI Learn in AT5)

| Knob | CC |
|------|----|
| Bass | 74 |
| Middle | 75 |
| Treble | 76 |
| Presence | 77 |
| Volume | 70 |
| Master | 71 |
| Gain | 72 |
| Reverb | 91 |
| Wharmonator | **not yet set** — MIDI Learn in AT5, then uncomment in KNOB_CC_MAP |

---

## Live Slot Config

Defined in both `routes.py` and `screen.js` — keep in sync:

```python
LIVE_SLOT_START  = 120
LIVE_SLOT_COUNT  = 8
LIVE_SLOT_PREFIX = "AT5_LIVE"
```

PC map is written by `generate_at5_pc_map.py`. Re-run it if slot count changes.

---

## Known Issues / To Do

1. **Wharmonator CC** — MIDI Learn in AT5, then set in `KNOB_CC_MAP` in routes.py
2. **>8 tones per song** — first 8 converted exactly, remainder get no live slot;
   expand `LIVE_SLOT_COUNT` if needed
3. **3dhighway plugin** — bare `catch {}` syntax bug aborts plugin load loop if enabled;
   rename to `3dhighway_disabled` to work around
4. **Badge position** — appears after Close button instead of before it
5. **Opening AT5 screen stops song** — Slopsmith core `showScreen()` calls `highway.stop()`;
   unfixable from a plugin
6. **Settings endpoint** — `GET /api/plugins/at5_tone/settings` not yet implemented

---

## Slopsmith Plugin API Reference

```javascript
// highway object
highway.getTime()           // audio-aligned time in seconds
highway.getToneChanges()    // [{t, name}] — CDLC songs only
highway.getToneBase()       // initial tone key string
highway.getSongInfo()       // {title, artist, arrangement, duration, ...}
highway.stop()              // stops playback (also called by showScreen)

// plugin context (routes.py setup function)
context["get_dlc_dir"]()    // Path to DLC/PSARC folder
context["extract_meta"]     // function to extract PSARC metadata
context["meta_db"]          // MetadataDB instance
context["config_dir"]       // Path to plugin config directory
```

### Key behaviours
- `showScreen(id)` stops audio if id !== 'player' — unavoidable from plugins
- `window.playSong` is safe to monkey-patch
- `window.slopsmith.on('arrangement:changed', cb)` fires with `{index, filename}`
