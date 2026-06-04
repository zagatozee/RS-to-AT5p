# AT5 Tone Switcher — Slopsmith Plugin
**v0.4.0**

Automatically switches AmpliTube 5 presets as you play songs in Slopsmith.

When you load a song, the plugin reads the tone information from the song file,
converts it into AmpliTube 5 presets on the fly, and switches AT5 to the right
preset at the right moment — automatically, in sync with the song.

---

## What's new in v0.4.0

- **AT5 version selector** — Settings tab now has CS / SE / AT5 / MAX radio
  buttons instead of a free mode checkbox. Each tier uses gear lists verified
  against the official IK Multimedia comparison document (v5.0.3).
- **Tier-separated preset cache** — presets are stored in `at5/cs/`, `at5/se/`,
  `at5/at5/`, or `at5/max/` beside each song. Switching tiers forces a fresh
  conversion and never serves cached presets from the wrong tier.
- **Global noise gate** — checkbox in Settings tab. Inserts the AT5 Noise Gate
  at pre-amp stomp slot 0, shifting other effects down. Available in all tiers.
- **Status tab rebuilt** — each live slot has its own ▶ audition button and 💾
  save-back button. MIDI output selector with Test button. Manual PC send with
  number input. Clear explanation of what save-back does.
- **MIDI trigger offset** — slider in Settings (0–1000ms). Fires preset changes
  ahead of the chart event to compensate for AT5 switching latency.
- **Tone Browser fixed** — search now works correctly, format filter added,
  results are clickable, tone rows show arrangement column and ▶ audition button.
- **Path resolution fixed** for updated Slopsmith docker-compose layouts where
  songs are in a `Songs/` subdirectory.
- **AT5 screen rendering fixed** for updated Slopsmith versions.
- **Bridge `/send_cc` and `/send_pc` GET endpoints** — send CC or PC directly
  from a browser URL or PowerShell for testing and MIDI Learn without stopping
  the bridge.

---

## What you need

### Software
- **Slopsmith** — running in Docker on Windows
- **AmpliTube 5** — standalone or VST (any version including free CS)
- **Python 3.10 or newer** on Windows (not inside Docker)

### Hardware — MIDI signal path
**Option A — Physical MIDI cable (recommended)**
Connect a MIDI cable from your interface MIDI OUT back to its MIDI IN.

**Option B — loopMIDI virtual port**
Install from https://www.tobias-erichsen.de/software/loopmidi.html, create a
port, leave it running. Note: unreliable on some Windows 11 systems — a cheap
USB MIDI interface as a loopback is more robust.

---

## Files

| File | Purpose |
|------|---------|
| `plugin.json` | Slopsmith plugin descriptor |
| `routes.py` | Plugin backend |
| `screen.js` | Plugin frontend |
| `screen.html` | Plugin UI (required — don't omit) |
| `rs_to_at5.py` | Tone converter — must be in plugin folder |
| `at5_midi_bridge.py` | MIDI bridge — run on Windows host |
| `generate_at5_pc_map.py` | One-time PC map setup |
| `gear_mapping_reference.md` | RS → AT5 gear mapping tables |
| `RS_to_AT5_Converter_Midi_Mappings.at5proj` | AT5 project with CC assignments pre-configured |

---

## Installation

### Step 1 — Plugin files

Copy all files into your Slopsmith plugin folder:

    <slopsmith_root>\plugins\at5_tone\

Create the `at5_tone` folder if it doesn't exist. Restart the container:

    docker restart slopsmith-web-1

### Step 2 — Docker volume

Add to your `docker-compose.yml` under `volumes:`:

    - "C:/Users/<username>/OneDrive/Documents/IK Multimedia/AmpliTube 5:/at5docs"

Adjust the path to your AT5 documents folder (check Options → General in AT5).
Restart the container after changing docker-compose.yml.

### Step 3 — PC map

Start Slopsmith. The plugin creates `AT5_LIVE_00.at5p` through `AT5_LIVE_07.at5p`
in your `Presets\Converted\` folder automatically.

Then run once:

    python generate_at5_pc_map.py

Restart AmpliTube 5 after running it.

### Step 4 — Configure AT5

- Options → Audio/MIDI → MIDI Input: set to your MIDI interface
- Options → Control → Program Change → enable Preset Control, Receive Channel: All

### Step 5 — Load the CC project (optional but recommended)

Open `RS_to_AT5_Converter_Midi_Mappings.at5proj` in AT5. This pre-configures
MIDI CC assignments for all amp knobs (Sensitivity=CC23, Presence=CC24,
Bass=CC25, Middle=CC26, Treble=CC27, Master=CC28, PreAmp=CC29). Without this,
tone switching still works but knob value adjustments won't fire automatically.

### Step 6 — Find your MIDI device name

```powershell
python -c "
import ctypes
class MIDIOUTCAPS(ctypes.Structure):
    _fields_ = [('wMid',ctypes.c_uint16),('wPid',ctypes.c_uint16),
                ('vDriverVersion',ctypes.c_uint32),('szPname',ctypes.c_wchar*32),
                ('wTechnology',ctypes.c_uint16),('wVoices',ctypes.c_uint16),
                ('wNotes',ctypes.c_uint16),('wChannelMask',ctypes.c_uint16),
                ('dwSupport',ctypes.c_uint32)]
winmm = ctypes.windll.winmm
for i in range(winmm.midiOutGetNumDevs()):
    caps = MIDIOUTCAPS()
    winmm.midiOutGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps))
    print(f'{i}: {caps.szPname}')
"
```

### Step 7 — Run the bridge

    python at5_midi_bridge.py --midi-port "Your Device Name"

Leave the window open while using Slopsmith.

---

## AT5 Version Selector

In the Settings tab, select your version of AmpliTube 5:

| Version | Amps | Cabs | Stomps | Notes |
|---------|------|------|--------|-------|
| **CS — Free** | 6 | 7 | 10 | Brit 8000, American Tube Clean 1 & 2, British Tube Lead 1, SLD 100, Bass Preamp |
| **SE** | 13 | 14 | 19 | Adds: American Lead MKIII, Brit 9000, Jazz Amp 120, Metal Lead V/W, Modern Tube Lead |
| **AT5** | 35 | 28 | 35 | Adds: Brit Silver, German 34, Red Pig, American Clean MKIII and more |
| **MAX** | 107 | 101 | full | Exact model matching, no fallback |

Every Rocksmith amp maps to the closest available model in your tier. Switching
tiers clears the live slots and rebuilds from scratch on the next song load.
Cached presets are stored separately per tier so switching never corrupts your
saved edits.

### Amp mapping logic (CS tier example)

| Rocksmith amp family | Maps to |
|---------------------|---------|
| Marshall JCM/DSL/JVM, Orange | Brit 8000 |
| Peavey 5150, Mesa Rectifier, Soldano | SLD 100 |
| Fender, Roland JC, Mesa clean | American Tube Clean 1 |
| Roland JC-120 specifically | American Tube Clean 2 |
| Marshall JTM45, Silver Jubilee, Bluesbreaker | British Tube Lead 1 |
| Ampeg, Aguilar, bass amps | Solid State Bass Preamp |

SE and AT5 tiers route the same amps to closer matches where available
(e.g. Peavey → Metal Lead V in SE+, Roland JC → Jazz Amp 120 in SE+,
Bogner → German 34 in AT5+).

### Effects in constrained tiers

Effects with no CS equivalent are dropped rather than substituted wrongly.
Dropped in CS: pitch shift, octave, whammy, phaser, ring mod, bit crusher,
acoustic/bass emulator, vibe. Kept and remapped: wah, chorus, flanger,
overdrive/distortion, compressor, delay, reverb, tremolo, noise gate, EQ.

---

## Global Noise Gate

Enable in Settings → Signal Chain. Inserts the AT5 Noise Gate at pre-amp stomp
slot 0 in every converted tone, shifting other effects down by one slot.
Cuts guitar and pickup noise before the gain stages. Available in all tiers.

---

## MIDI Trigger Offset

The slider in Settings → MIDI Trigger Offset (0–1000ms, default 200ms) fires
preset changes this many milliseconds before the tone change event in the song
chart. Increase if AT5 is switching too late. Adjust by ear — start around
200–400ms. Persists across sessions.

---

## Save-back

After dialling in a tone in AT5:
1. Open the AT5 plugin screen
2. Status tab → click 💾 on a slot (saves that tone) or "Save all presets back
   to song" (saves all)

Your edited preset is stored beside the song file in `at5/<tier>/` and loads
automatically on every subsequent load of that song. Switching to a different
tier generates a fresh conversion without touching your edits in other tiers.

---

## Troubleshooting

**Bridge says `{"ok": false}`**
The `--midi-port` name doesn't match. Re-run the device name script.

**Live convert 422 error**
`rs_to_at5.py` is missing from the plugin folder.

**AT5 crashes on startup**
Delete `AT5_LIVE_*.at5p` from `Presets\Converted\` and let the plugin recreate
them after restarting Slopsmith.

**No tone switches**
Check: bridge running, AT5 MIDI Input set correctly, Program Change enabled,
MIDI cable connected at both ends.

**Bridge receives PC but AT5 doesn't switch**
Restart AmpliTube 5 — it sometimes loses its MIDI connection after the Docker
container restarts.

**Opening AT5 plugin screen stops song**
Known Slopsmith core behaviour — opening any plugin screen pauses playback.
Unfixable from a plugin.

---

## How it works

Every CDLC PSARC contains the guitar tone settings used in Rocksmith. When you
load a song, the plugin reads those settings and converts them to AT5 preset
files using a mapping of Rocksmith amp/effect models to their AT5 equivalents.
It writes the presets to 8 reserved PC slots (120–127), then sends MIDI Program
Change messages at the correct timestamps as the song plays.

The first load converts and seeds presets beside the song file in a
tier-specific subfolder. Every subsequent load copies them directly — no
extraction needed. If you edit the AT5 preset and save it back, your version
loads from then on.
