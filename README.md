# AT5 Tone Switcher — Slopsmith Plugin

Automatically switches AmpliTube 5 presets as you play songs in Slopsmith.

When you load a song, the plugin reads the tone information from the song file, converts it into AmpliTube 5 presets on the fly, and switches AT5 to the right preset at the right moment — automatically, in sync with the song.

---

## What's new

- **Song-local preset store** — converted presets are saved beside each song file. Subsequent loads skip conversion entirely and load in ~1ms. Dial in a tone in AT5, click "Save back to song" in the Status tab, and your edits persist permanently with that song.
- **AT5 Free / CS mode** — a checkbox in the Settings tab maps every Rocksmith tone to the closest gear available in the free version of AmpliTube 5. Full details below.
- **Batch prescan** — a background endpoint to pre-convert all your PSARCs at once.
- **Reset on song end** — AT5 returns to a neutral preset when you leave a song.
- **RS2014 support** — the converter handles both RS+ and Rocksmith 2014 tone formats.

---

## What you need

### Software
- **Slopsmith** — running in Docker on Windows
- **AmpliTube 5** — standalone or VST (paid or free CS version)
- **Python 3.10 or newer** on Windows
  - Download from https://www.python.org/downloads/
  - During install, tick "Add Python to PATH"

### Hardware — MIDI signal path
The plugin sends MIDI Program Change messages to AT5 to switch presets. You need a MIDI loopback:

**Option A — Physical MIDI cable (recommended, most reliable)**
Connect a standard MIDI cable from your interface MIDI OUT back to its MIDI IN. Works on any system without extra software.

**Option B — loopMIDI virtual port**
Install from https://www.tobias-erichsen.de/software/loopmidi.html, create a port, leave it running. Note: loopMIDI has been reported unreliable on some Windows 11 systems. A cheap USB MIDI interface used as a loopback is a more robust fallback.

---

## Files in this package

| File | Purpose |
|------|---------|
| `plugin.json` | Slopsmith plugin descriptor |
| `routes.py` | Plugin backend |
| `screen.js` | Plugin frontend |
| `screen.html` | Plugin UI |
| `rs_to_at5.py` | Tone converter — must be in the plugin folder |
| `at5_midi_bridge.py` | MIDI bridge — run on Windows host |
| `generate_at5_pc_map.py` | One-time PC map setup script |
| `start_slopsmith_at5.bat` | Launch script — edit 3 variables and double-click |

---

## Installation

### Step 1 — Plugin files

Copy all files from this package into your Slopsmith plugin folder:

    <slopsmith_root>\plugins\at5_tone\

If the `at5_tone` folder doesn't exist, create it. Restart the container:

    docker restart slopsmith-web-1

### Step 2 — Docker volume

Add this to your `docker-compose.yml` under `volumes:` for the slopsmith service:

    - "C:/Users/<username>/Documents/IK Multimedia/AmpliTube 5:/at5docs"

Adjust the path to wherever AT5 stores its documents.

> Finding the right path: Common locations are
>     C:/Users/yourname/Documents/IK Multimedia/AmpliTube 5
>     C:/Users/yourname/OneDrive/Documents/IK Multimedia/AmpliTube 5
> Check which exists in File Explorer. You can also find it in AT5 under Options > General.

Restart the container after changing docker-compose.yml.

### Step 3 — Create live slot files

Start Slopsmith. The plugin automatically creates 8 placeholder preset files
(`AT5_LIVE_00.at5p` through `AT5_LIVE_07.at5p`) in your `Presets\Converted\` folder.

Then run the PC map generator to register them in AT5's Program Change list:

    python generate_at5_pc_map.py

Restart AmpliTube 5 after running it.

### Step 4 — Configure AT5

In AmpliTube 5:
- Options > Audio/MIDI > MIDI Input: set to your MIDI interface (or loopMIDI port)
- Options > Control > Program Change > enable Preset Control, Receive Channel: All

### Step 5 — Find your MIDI device name

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

---

## Running

Edit `start_slopsmith_at5.bat` and set the three variables at the top:

    SLOPSMITH_DIR  = folder containing your docker-compose.yml
    BRIDGE_DIR     = folder containing at5_midi_bridge.py
    MIDI_PORT      = your MIDI device name from Step 5

Then double-click it. It starts Slopsmith and the MIDI bridge together.

Or manually:
1. `docker compose up -d` from your Slopsmith folder
2. `python .\at5_midi_bridge.py --midi-port "Your Device Name"`
3. Open AmpliTube 5
4. Load any CDLC song in Slopsmith

---

## Using it

Load a song and within a second you should see in the browser console (F12):

    [AT5 Live] Converting song_name_p.psarc...
    [AT5 Live] 4 tones in live slots (45ms)

And in the bridge window:

    PC -> ch=0 bank=0 prog=120  (preset #121)  OK

The plugin tab in Slopsmith (click AT5 in the nav bar) shows a Status tab with
live slot assignments, a Tone Browser for manually previewing tones, a Live Log
of every switch, and a Settings tab.

### Saving your edits

After dialling in a tone in AT5:
1. Open the AT5 plugin screen
2. Status tab > click "Save current presets back to song"
3. Your edited preset is saved beside the song file and loads automatically next time

---

## AT5 Free / CS Mode

If you have the free version of AmpliTube 5 (AT5 CS), enable this in the
Settings tab. The plugin will map every Rocksmith tone to the closest gear
available in the free version.

### What AT5 CS includes

The free version of AT5 includes 41 gear items total:

**6 Amplifiers**
- Brit 8000
- American Tube Clean 1
- American Tube Clean 2
- British Tube Lead 1
- SLD 100
- Solid State Bass Preamp

**7 Cabinets**
- 1x12 Open Vintage, 1x15 Bass Vintage, 2x12 Closed Vintage
- 4x10 Open Vintage, 4x12 Brit 8000, 4x12 Closed Vintage, 4x12 Metal T

**10 Stomps**
- 7 Band Graphic, Chorus, Compressor, Delay, Diode Overdrive
- Flanger, Noise Gate, Opto Tremolo, Volume, Wah

**6 Rack Effects**
- Digital Chorus, Digital Delay, Digital Reverb
- Graphic EQ, Parametric EQ 3, Tube Compressor

### Amp mapping logic

Rocksmith uses fictional amp names (e.g. `Amp_BT100`) that represent specific
real-world amps. In free mode, each amp family maps to the closest CS amp:

| Rocksmith amp family | Real-world amp | Maps to in CS |
|---------------------|---------------|---------------|
| BT100, BT45, GB100, GB50, Marshall JCM/DSL/JVM/JMP/Plexi, Orange high-gain | Marshall JCM 800 family / Orange | **Brit 8000** |
| TW22, TW26, TW40, Marshall JTM45, Bluesbreaker, Silver Jubilee | Fender tweed, Marshall vintage clean | **British Tube Lead 1** |
| HG100, HG180, HG500, Mesa Rectifier, Marshall Slash | Soldano, Mesa Rectifier, Peavey 5150 | **SLD 100** |
| CA85, CA100, Mesa Lead MKIII | Mesa Mark III lead channel | **SLD 100** |
| CA38, CS90, CS100, CS120, AT20, AT120 | Mesa Mark III clean, Roland JC, Fender clean | **American Tube Clean 1** |
| BT15, BT30 bass amps | Small Marshall, bass-oriented | **Solid State Bass Preamp** |

The Brit 8000 is the default fallback for any amp not matched above — it covers
the widest range of rock and metal tones in the CS lineup.

### Cabinet mapping logic

Rocksmith cab keys encode the enclosure size and type. In free mode they map to
the closest CS cabinet by size and character:

| Rocksmith cab type | Maps to in CS |
|-------------------|---------------|
| Bass cabs, 1x15 | **1x15 Bass Vintage** |
| 1x12 (any) | **1x12 Open Vintage** |
| 2x12 (any) | **2x12 Closed Vintage** |
| 4x10 (any) | **4x10 Open Vintage** |
| High-gain / Mesa / Metal 4x12 | **4x12 Metal T** |
| British 4x12 (Marshall, Orange) | **4x12 Brit 8000** |
| All other 4x12 | **4x12 Closed Vintage** (default) |

### Effect mapping logic

Effects are mapped by category to the closest CS equivalent. Some effect types
have no reasonable CS equivalent and are **dropped entirely** (the slot is left
empty) rather than replaced with something inappropriate.

**Mapped to CS equivalents:**

| Effect type | CS equivalent |
|------------|---------------|
| Wah, auto-wah, filter | Wah |
| Chorus (all variants) | Chorus / Digital Chorus |
| Flanger (all variants) | Flanger |
| Overdrive, distortion, fuzz, boost | Diode Overdrive |
| Compressor, limiter | Compressor / Tube Compressor |
| Delay, echo (all variants) | Delay / Digital Delay |
| Reverb (spring, plate, room, hall) | Digital Reverb |
| Tremolo (all variants) | Opto Tremolo |
| Noise gate | Noise Gate |
| EQ (5-band, 8-band, parametric) | Graphic EQ |

**Dropped (no CS equivalent — slot left empty):**

- Pitch shifter, whammy, octave pedals
- Phaser
- Ring modulator
- Bit crusher
- Acoustic emulator, bass emulator
- Vibe, rotary effects
- Lo-fi filter, synth filter

Dropping is intentional — an empty slot is preferable to a wildly inappropriate
effect. The overall tone character (amp + cab + core drive/modulation) will still
be recognisable even without these specialty effects.

### Honest expectations

With only 6 amps and 7 cabs available, coverage is inherently limited:

- **High-gain rock/metal tones** — good. Marshall and Soldano family tones land
  in the right ballpark with Brit 8000 and SLD 100.
- **Clean tones** — decent. The two American Tube Clean amps cover most
  Fender-style and Roland JC-style clean sounds reasonably well.
- **Mid-gain crunch** — fair. British Tube Lead 1 handles many classic crunch
  tones, though nuance is lost.
- **Specialty effects** (pitch, octave, acoustic emulation) — these are dropped,
  which means some tones will sound noticeably different from the original.

Free mode is a starting point, not a perfect replica. The paid version of AT5
(SE at minimum) adds significantly more amp variety and makes a meaningful
difference in coverage.

---

## Troubleshooting

**`{"ok": false}` from bridge**
The `--midi-port` name doesn't match exactly. Re-run the device name script and
copy the name precisely including capitalisation.

**Live convert 422 error in browser console**
`rs_to_at5.py` is missing from the plugin folder.

**AT5 crashes on startup**
Delete `AT5_LIVE_*.at5p` from `Presets\Converted\` and let the plugin recreate
them after restarting Slopsmith.

**No tone switches firing**
Check AT5 MIDI Input is set correctly and Program Change is enabled.
Verify the MIDI cable is connected at both ends (or loopMIDI is running).

**Converting fires but bridge shows nothing**
The song may have no tone change events (single-tone CDLC). The base tone still
fires at song start.

**Opening AT5 plugin screen stops playback**
This is a Slopsmith core behaviour — opening any plugin screen pauses the song.
It cannot be fixed from within a plugin. Use the Live Log to review what happened.

---

## How it works

Every CDLC song file (PSARC) contains the guitar tone settings used in Rocksmith
— amp model, cabinet, pedals, all the knob positions. When you load a song, the
plugin reads those settings and converts them to AmpliTube 5 preset files using a
mapping of Rocksmith amp/effect models to their AT5 equivalents. It writes the
presets to 8 reserved slots (PC 120-127), then sends MIDI Program Change messages
at the correct timestamps as the song plays.

The first load converts and saves presets beside the song file. Every subsequent
load copies them directly — no extraction needed. If you edit the AT5 preset and
save it back, your version loads from then on.

---

## Limitations

- CDLC / PSARC songs only for live convert. RS+ scrape songs use a pre-built PC
  table if configured.
- 8 tones per song maximum. Songs with more than 8 unique tones will use the first
  8 exactly. Increase `LIVE_SLOT_COUNT` in `routes.py` and `screen.js` if needed,
  then re-run `generate_at5_pc_map.py`.
- Whammy pedal CC switching is in place but requires a one-time MIDI Learn step.
  See `KNOB_CC_MAP` in `routes.py`.
