# AT5 Tone Switcher — Slopsmith Plugin
**v0.5.8**

Automatically switches AmpliTube 5 presets in sync with song playback in Slopsmith. When you load a song, the plugin extracts the guitar tone data, converts it to AT5 presets, and fires MIDI Program Change messages at the right moments — no manual switching needed.

---

## Installation

### Option A — Plugin Manager (recommended)

1. In Slopsmith, open **Plugins** in the nav bar
2. Click **Add from GitHub**
3. Enter: `zagatozee/RS-to-AT5p`
4. Click Install

### Option B — Manual

Download the zip, extract the `at5_tone` folder, and copy it to:

**Desktop app:**
```
C:\Users\<username>\AppData\Roaming\slopsmith-desktop\plugins\at5_tone\
```

**Docker:**
```
<slopsmith_root>\plugins\at5_tone\
```
Then restart the container: `docker restart slopsmith-web-1`

---

## Setup — Desktop App

The plugin's Status tab will guide you through setup with buttons. Here's what it does:

### Step 1 — Link Presets folder
The plugin needs access to your AmpliTube 5 Presets folder. Click **Create Symlink** in the Status tab. This creates a symbolic link so Slopsmith and AT5 share the same Presets folder.

> If the button fails, run Slopsmith Desktop as administrator (right-click → Run as administrator), then try again.

### Step 2 — Populate live slots
Click **Run Setup** in the Status tab. This creates 8 preset slots (AT5_LIVE_00–07) and registers them in AT5's Program Change list.

### Step 3 — Configure AT5
In AmpliTube 5:
- **Options → Audio/MIDI → MIDI Input:** set to your audio interface or loopMIDI port
- **Options → Control → Program Change:** enable Preset Control, Receive Channel: All
- Restart AT5

### Step 4 — MIDI output
In the AT5 plugin Status tab, select your MIDI output from the dropdown:

| Your setup | Select |
|-----------|--------|
| AT5 loaded as VST in Slopsmith Desktop chain | Internal VST (no extra software needed) |
| AT5 standalone + loopMIDI | Your loopMIDI port (e.g. "AT5 Bridge") |
| AT5 standalone + audio interface | Your interface (e.g. "AXE IO") — requires MIDI cable looped OUT→IN |

> **Simplest setup:** load AT5 as a VST inside Slopsmith Desktop's audio chain. No loopMIDI, no cable, no bridge script needed.

> **loopMIDI download:** https://www.tobias-erichsen.de/software/loopmidi.html — free, create one virtual port, leave it running in the system tray.

---

## Setup — Docker

### Step 1 — Docker volume
Add to your `docker-compose.yml` under `volumes:`:
```yaml
- "C:/Users/<username>/Documents/IK Multimedia/AmpliTube 5:/at5docs"
```
> If AT5 documents are in OneDrive, use:
> `C:/Users/<username>/OneDrive/Documents/IK Multimedia/AmpliTube 5:/at5docs`
>
> Check the correct path in AT5 under Options → General.

Restart the container after changing docker-compose.yml.

### Step 2 — Populate live slots
Run once from a terminal on the Windows host:
```
python plugins\at5_tone\generate_at5_pc_map.py
```
Restart AmpliTube 5 after running.

### Step 3 — Configure AT5
Same as Desktop Step 3 above.

### Step 4 — MIDI bridge
Docker can't access Windows MIDI directly. You need one of:

**loopMIDI (no cable needed):**
1. Install loopMIDI, create a port named "AT5 Bridge"
2. Set AT5 MIDI Input to "AT5 Bridge"
3. Run the bridge: `python plugins\at5_tone\at5_midi_bridge.py --midi-port "AT5 Bridge"`

**Physical MIDI cable:**
Connect MIDI OUT → MIDI IN on your audio interface, then:
```
python plugins\at5_tone\at5_midi_bridge.py --midi-port "Your Interface Name"
```

---

## Files

| File | Purpose |
|------|---------|
| `plugin.json` | Slopsmith plugin descriptor |
| `routes.py` | Plugin backend |
| `screen.js` | Plugin frontend |
| `screen.html` | Plugin UI |
| `settings.html` | Settings panel (injected into Slopsmith Settings page) |
| `rs_to_at5.py` | Tone converter |
| `at5_midi_bridge.py` | MIDI bridge for Docker users |
| `generate_at5_pc_map.py` | One-time PC map setup |
| `gear_mapping_reference.md` | RS → AT5 gear mapping tables |

---

## AT5 Version Selector

In **Settings**, select your version of AT5:

| Version | Amps | Notes |
|---------|------|-------|
| CS — Free | 6 | Covers most rock/metal tones. Some effects dropped. |
| SE | 13 | Adds Peavey, Roland JC, Mesa family. Recommended minimum. |
| AT5 | 35 | Adds Bogner, Silver Jubilee, many more. |
| MAX | 107 | Full library — closest possible match for every tone. |

Each tier uses a separate preset cache. Switching tiers re-converts all tones from scratch without touching your saved edits in other tiers.

---

## Global Noise Gate

Enable in **Settings → Signal Chain**. Inserts the AT5 Noise Gate at pre-amp slot 0 in every converted tone. Cuts hum and noise before the gain stage. Available in all AT5 versions.

---

## Save-back

Dial in a tone in AT5, then in the plugin Status tab click 💾 on a slot. Your edited preset is stored beside the song file and loads automatically on every subsequent play of that song.

---

## Troubleshooting

**Setup panel shows "Presets folder not linked" after clicking Create Symlink**
Run Slopsmith Desktop as administrator and try again. Windows requires elevated privileges to create symbolic links.

**Live slots not populating**
Make sure the Presets folder is linked first (Step 1), then run Setup again.

**AT5 crashes on startup**
Delete `AT5_LIVE_*.at5p` from your AT5 Presets/Converted folder and let the plugin recreate them.

**No tone switches firing**
Check: AT5 MIDI Input is set correctly, Program Change is enabled in AT5 Control settings, correct MIDI output selected in plugin Status tab.

**Tone Browser shows no results**
The bundled `slopsmith-plugin-midi` is required and should always be present. If missing, reinstall Slopsmith.

**Docker: bridge shows `{"ok": false}`**
The `--midi-port` name doesn't match exactly. Run this to list available ports:
```powershell
python -c "
import ctypes
class MIDIOUTCAPS(ctypes.Structure):
    _fields_ = [('wMid',ctypes.c_uint16),('wPid',ctypes.c_uint16),('vDriverVersion',ctypes.c_uint32),('szPname',ctypes.c_wchar*32),('wTechnology',ctypes.c_uint16),('wVoices',ctypes.c_uint16),('wNotes',ctypes.c_uint16),('wChannelMask',ctypes.c_uint16),('dwSupport',ctypes.c_uint32)]
winmm = ctypes.windll.winmm
for i in range(winmm.midiOutGetNumDevs()):
    caps = MIDIOUTCAPS()
    winmm.midiOutGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps))
    print(f'{i}: {caps.szPname}')
"
```

**Opening the plugin screen pauses playback**
This is a Slopsmith core behaviour affecting all plugins. Use the Live Log tab to review what happened after resuming.

---

## How it works

Every CDLC PSARC contains the guitar tone settings used in Rocksmith — amp model, cabinet, pedals, all knob positions. When you load a song, the plugin reads those settings and converts them to AT5 preset files using a mapping of Rocksmith gear to AT5 equivalents. It writes the presets to 8 reserved PC slots (120–127) and sends MIDI Program Change messages at the correct timestamps during playback.

The first load converts and seeds presets beside the song file in a tier-specific subfolder. Every subsequent load copies them directly. If you edit a preset in AT5 and save it back, your version loads from then on.
