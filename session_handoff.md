# Slopsmith AT5 Tone Switcher — Technical Handoff
*June 2026 — v0.4.0*

---

## Status

Working end-to-end. Live convert confirmed on CDLC songs. Four-tier AT5 version
system implemented (CS/SE/AT5/MAX). Global noise gate working. Tone Browser
fixed and functional. Status tab rebuilt with per-slot controls. Save-back
working. Path resolution fixed for updated docker-compose layout.

---

## What's new in v0.4.0

- **Four-tier AT5 version selector** (CS/SE/AT5/MAX) replaces free mode checkbox.
  Gear lists verified against IK official PDF v5.0.3. Each tier uses a separate
  cache subfolder (`at5/cs/`, `at5/se/`, `at5/at5/`, `at5/max/`) to prevent
  cross-tier cache contamination.
- **Global noise gate** — checkbox in Settings tab, inserts AT5 Noise Gate at
  pre-amp stomp slot 0, shifting other effects down. Available all tiers.
- **Status tab rebuilt** — per-slot ▶ audition and 💾 save-back buttons, MIDI
  output selector with Test button, manual PC send input, save-back explanation.
- **MIDI trigger offset slider** (0–1000ms) in Settings tab. Fires preset changes
  ahead of the chart event. Persists in localStorage.
- **Tone Browser fixed** — search now works (/api/library endpoint), format
  filter dropdown, clickable results, arrangement column, ▶ per tone row.
- **Path resolution fixed** — `match-cdlc-tones` and `live_convert` now try
  multiple path candidates to handle Songs/ subdirectory layout.
- **AT5 screen rendering fixed** — removed outer wrapper div from screen.html
  (Slopsmith now creates it, was causing duplicate DOM element / zero height).
- **at5_midi_bridge.py** — added GET `/send_cc` and `/send_pc` endpoints for
  testing CC/PC from browser or PowerShell without stopping the bridge.
- **Amp mapping improvements** verified against IK PDF:
  - Peavey/5150 → Metal Lead V in SE+
  - Roland JC/Fender → Jazz Amp 120 in SE+
  - Bogner/Diezel → German 34 in AT5+
  - Silver Jubilee → Brit Silver in AT5+
  - Ampeg/Aguilar → Solid State Bass Preamp all tiers
  - Mesa Dual Rectifier → SLD 100 CS, Metal Lead V in SE+

---

## Architecture

```
Slopsmith (Docker)
  → playSong hook (screen.js)
  → _at5RequestLiveConvert()
      → POST /api/plugins/at5_tone/live_convert
          1. Check <song_dir>/at5/<tier>/<tone_key>.at5p  (song-local, tier-specific)
          2. Fallback: extract PSARC → rs_to_at5.py → write to live slots
          3. Seed newly converted presets back to song-local folder
      → writes AT5_LIVE_00..07.at5p to AT5 Presets/Converted/
  → _at5StartScheduler()
      → highway.getToneChanges() [CDLC]
      → setInterval 100ms polling highway.getTime()
      → _at5SendPC() → HTTP POST → at5_midi_bridge.py (localhost:37432)
      → winmm → MIDI OUT → cable loop → MIDI IN → AT5
```

---

## Module-Level State (routes.py)

```python
_at5_tier       = "max"   # "cs" | "se" | "at5" | "max"
_at5_free_mode  = False   # legacy alias — True maps to tier="cs"
_at5_noise_gate = False   # global pre-amp noise gate
_live_state     = {"song": None, "slots": {}, "warnings": [], ...}
```

---

## AT5 Version Tiers (from IK PDF v5.0.3)

| Tier | Amps | Cabs | Stomps | Rack |
|------|------|------|--------|------|
| CS   | 6    | 7    | 10     | 6    |
| SE   | 13   | 14   | 19     | 13   |
| AT5  | 35   | 28   | 35     | 34   |
| MAX  | 107  | 101  | full   | full |

Song-local preset cache uses tier subfolder: `at5/<tier>/<tone_key>.at5p`

---

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /live_convert` | Check tier cache → live convert → seed back |
| `GET/POST /settings` | tier, free_mode, noise_gate |
| `POST /preset/save-back` | Copy live slot → song-local tier folder |
| `GET /live_status` | Current slots, tier, cache_mode |
| `GET /match-cdlc-tones/{filename}?skip_scrape=true` | Tone Browser PSARC lookup |

---

## at5_midi_bridge.py Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /ping` | Health check, returns midi_port and ready status |
| `GET /send_cc?cc=N&value=N[&channel=N]` | Send CC (for MIDI Learn testing) |
| `GET /send_pc?program=N[&channel=N]` | Send PC (for testing) |
| `POST /pc` | Send PC with full bank/channel control |
| `POST /cc` | Send CC via POST |

---

## MIDI CC Map (confirmed via MIDI Learn + AT5 PRESET tab)

Assigned via AT5 Control → Control Change → PRESET → Amp A → Brit 8000:

| Parameter   | CC# |
|------------|-----|
| Sensitivity | 23  |
| Presence    | 24  |
| Bass        | 25  |
| Middle      | 26  |
| Treble      | 27  |
| Master      | 28  |
| PreAmp      | 29  |

**Important:** CC assignments are stored in the AT5 project file
(`RS_to_AT5_Converter_Midi_Mappings.at5proj`), NOT in settings.properties or
the registry. Users must load this project file in AT5 to have CC control.
The `externalPluginData` blob is IK-proprietary encoded — cannot be generated
programmatically.

---

## Noise Gate

```python
NOISE_GATE_GUID     = "0455f997-43ca-4c9b-9269-286a19d10d48"
NOISE_GATE_THRESHOLD = -50.0  # dB default
```

Inserts at pre-amp stomp slot 0, shifts existing effects down. Last effect
dropped if all 6 slots already occupied (extremely rare in RS tones). Available
in all AT5 tiers (CS through MAX per IK PDF).

---

## Live Slot Config

```python
LIVE_SLOT_START  = 120
LIVE_SLOT_COUNT  = 8
LIVE_SLOT_PREFIX = "AT5_LIVE"
```

---

## Open Questions / Future Work

1. **Wharmonator CC** — needs MIDI Learn in AT5, then set in KNOB_CC_MAP
2. **Sloppak/loose folder live convert** — song-local cache wired but live
   extraction not yet implemented for these formats
3. **AT5 CC map programmatic write** — CC assignments stored in opaque
   `externalPluginData` blob in .at5proj file. Ship pre-configured project
   file with plugin as workaround.
4. **Soundshed Guitar integration** — developer has reached out. Need:
   .gfxpreset format schema, programmatic preset switching method, Tone3000 API.
5. **Pre-bake free/max presets into sloppaks** — plan to generate both
   `at5/free/` and `at5/max/` preset folders for all songs and bundle with
   sloppak packages.
6. **Slopsmith plugin-tones integration** — RS2014 gear images available via
   `GET /api/plugins/tones/song/{filename}`. Natural fit for Tone Browser display.
