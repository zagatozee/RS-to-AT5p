# Slopsmith AT5 Tone Switcher — Technical Handoff
*May 2026*

---

## Status

Working end-to-end. Live convert confirmed on CDLC songs. CC knob adjustments
confirmed firing. AT5 switching presets in response to MIDI PC messages.
Song-local preset store implemented (presets seed to `at5/` folder beside each PSARC).
Save-back endpoint implemented (user AT5 edits persist back to song folder).

---

## Architecture

```
Slopsmith (Docker)
  → playSong hook (screen.js)
  → _at5RequestLiveConvert()
      → POST /api/plugins/at5_tone/live_convert
          1. Check <song_dir>/at5/<tone_key>.at5p  (song-local, user-edited)
          2. Fallback: extract PSARC → rs_to_at5.py → write to live slots
          3. Seed newly converted presets back to song-local folder
      → writes AT5_LIVE_00..07.at5p to AT5 Presets/Converted/
  → _at5StartScheduler()
      → highway.getToneChanges() [CDLC]
        OR XML parse [RS+ scrape songs]
      → setInterval 100ms polling highway.getTime()
      → _at5Lookup(): live slots first, PC table fallback
      → HTTP POST → at5_midi_bridge.py (localhost:37432)
      → winmm → MIDI OUT → cable loop → MIDI IN → AT5
```

---

## Song-Local Preset Store

On first load of a PSARC, tones are live-converted and seeded to:
```
<psarc_dir>/<psarc_stem>/at5/<tone_key>.at5p
```

On subsequent loads, these files are copied directly to live slots (~1ms, no extraction).

After dialling in a tone in AT5, click "Save current presets back to song" in the
Status tab — copies the current live slot file back to the song-local folder,
overwriting the auto-converted version. Those edits then load automatically every time.

Sloppak layout: `<sloppak_stem>/at5/` beside the `.sloppak` file.
Loose folder layout: `at5/` inside the loose folder.
(Sloppak/loose extraction not yet implemented — PSARC only for now.)

---

## Prescan (batch pre-conversion)

```
POST /api/plugins/at5_tone/prescan          -- all PSARCs in DLC folder
POST /api/plugins/at5_tone/prescan  {"filenames": ["song.psarc"]}
GET  /api/plugins/at5_tone/prescan/status?job_id=<id>
```

Runs in background thread. Skips songs that already have a complete `at5/` folder.

---

## Plugin Files

### screen.js
- `_at5RequestLiveConvert(filename)`: fires on song load, checks song-local first
- `_at5SaveBack(toneKey)`: saves dialled-in AT5 preset back to song folder
- `_at5StartScheduler(filename)`: retries highway.getToneChanges() up to 5x
- `_at5Lookup(toneKey)`: live slots first, then PC table
- Reset to PC 0 on song end (only if a tone was actually fired this session)

### routes.py
- `POST /live_convert`: song-local check → live convert → seed back
- `POST /preset/save-back`: copy live slot → song-local store
- `POST /prescan`: batch pre-convert all PSARCs (background thread)
- `GET /prescan/status`: progress polling
- `GET /live_status`: current slot assignments and source (song-local vs live-convert)
- On startup: creates AT5_LIVE_00..07.at5p using real AT5P_TEMPLATE (not hand-rolled XML)

### rs_to_at5.py
- Must be in the plugin folder — routes.py imports it at runtime
- Supports RS+ JSON, RS2014 GearList JSON, RS2014 `.tone2014.xml`
- `_convert_tone_from_gearlist()`: shared assembly used by both CLI and live convert
- DI tones: `DIBeforeAmp="1"`, amp muted, cab unmuted — correct AT5 routing
- 42 amps, 68 pedals, 17 rack effects mapped; 0 misses on 179 RS2014 official tones

---

## rs_to_at5.py Changes (this week)

- `--rs2014-xml` flag: parse `.tone2014.xml` (WCF format from PSARC toolkit)
- Added `Amp_BT15`, `Amp_GB38`, `DI_Amp_BassDriver` to AMP_MAP
- Added 20 missing RS2014 cab variants (Ribbon/Condenser/OffAxis mic positions)
- Added `Pedal_DigitalVerb`, `Pedal_Limiter` to EFFECT_MAP
- Fixed DI tone routing: `DIBeforeAmp="1"` + cab unmuted (was silencing presets)
- Refactored shared preset assembly into `_convert_tone_from_gearlist()`

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

---

## Known Issues / To Do

1. **Wharmonator CC** — MIDI Learn in AT5, then set in `KNOB_CC_MAP` in routes.py
2. **Sloppak/loose folder** — song-local preset store not yet wired for these formats
3. **Settings panel prescan UI** — endpoint exists, no UI yet
4. **AT5 screen display** — screen.html renders but may need further layout debugging
   depending on Slopsmith version (confirmed working on 0.2.8-prerelease)
5. **3dhighway plugin** — bare `catch {}` syntax bug; rename to `3dhighway_disabled`
6. **Opening AT5 screen stops song** — Slopsmith core behaviour, unfixable from plugin

---

## Slopsmith Plugin API Reference

```javascript
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
- Plugin screen loaded from `screen.html` — must exist for nav entry to work
- `plugin.json` must include `"routes": "routes.py"` for backend to load
