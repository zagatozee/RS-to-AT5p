# AT5 Tone Switcher — Slopsmith Plugin

Automatically switches AmpliTube 5 presets as you play songs in Slopsmith.

When you load a song, the plugin reads the tone information from the song file, converts it into AmpliTube 5 presets on the fly, and switches AT5 to the right preset at the right moment — automatically, in sync with the song.

---

## What you need

### Software
- **Slopsmith** — running in Docker on Windows (this is a plugin for it)
- **AmpliTube 5** — the IK Multimedia guitar amp simulator (standalone app or VST)
- **Python 3.10 or newer** — installed on Windows, not inside Docker
  - Download from https://www.python.org/downloads/
  - During install, tick "Add Python to PATH"

### Hardware — MIDI signal path
The plugin works by sending MIDI Program Change messages to AT5 to switch presets. You need a way to route MIDI from the plugin (running inside Docker on your PC) to AT5 (also running on your PC). This sounds circular but requires one of:

**Option A — Physical MIDI cable loop (recommended, most reliable)**
If your audio interface has both a MIDI IN and MIDI OUT port (5-pin DIN sockets), connect a standard MIDI cable from the MIDI OUT to the MIDI IN on the same interface. That's it — the signal goes out one port and straight back in the other.

> This is the most reliable method. If your interface has MIDI ports, use this.

**Option B — loopMIDI virtual port**
If your interface has no MIDI ports (USB-only interfaces, built-in audio etc.), install loopMIDI to create a virtual MIDI cable entirely in software:
1. Download from https://www.tobias-erichsen.de/software/loopmidi.html
2. Install and open it
3. Click the + button to create a new port — name it anything, e.g. "AT5 Bridge"
4. Leave loopMIDI running in the system tray

> Note: loopMIDI has been reported as unreliable on some Windows 11 systems. If you have trouble, a cheap USB MIDI interface with physical ports (under £10) used as a loopback is a more robust solution.

---

## Installation — step by step

### Step 1 — Get the plugin files into Slopsmith

Find your Slopsmith plugins folder. If you followed the standard Slopsmith Docker setup it will be something like:

    C:\Users\<yourname>\slopsmith\plugins\

or wherever you put it when setting up Docker. Inside that folder there should already be an `at5_tone` folder. If not, create it.

Copy these files into that `at5_tone` folder, replacing any existing files:

    routes.py
    screen.js
    rs_to_at5.py       ← this is a new file, it won't exist yet

Then restart the Slopsmith Docker container so it picks up the changes:

    Open PowerShell and run:
    docker restart slopsmith-web-1

### Step 2 — Connect Slopsmith to your AT5 folder

The plugin needs to write preset files directly into your AmpliTube 5 presets folder. You do this by adding a "volume mount" to your Slopsmith Docker configuration.

Open your Slopsmith `docker-compose.yml` file in a text editor and find the `volumes:` section under the slopsmith service. Add this line:

    - "C:/Users/<yourname>/Documents/IK Multimedia/AmpliTube 5:/at5docs"

Replace `<yourname>` with your actual Windows username. If your AT5 documents are stored somewhere else (OneDrive, a different drive, etc.) adjust the path accordingly — it's wherever AT5 keeps its presets.

The full volumes section might look like this when done:

    volumes:
      - "./songs:/songs"
      - "./dlc:/dlc"
      - "C:/Users/yourname/Documents/IK Multimedia/AmpliTube 5:/at5docs"

Save the file, then restart the container again:

    docker restart slopsmith-web-1

> How to find your AT5 documents folder: open AmpliTube 5, go to
> Options > General, and look for the User Data folder path.

### Step 3 — Let the plugin create its preset files

Open Slopsmith in your browser (usually http://localhost:8000) and just leave it on the library screen for a moment. In the background, the plugin will automatically create 8 preset files in your AT5 folder:

    AT5_LIVE_00.at5p
    AT5_LIVE_01.at5p
    ...
    AT5_LIVE_07.at5p

These will appear in your AT5 Presets\Converted\ folder. You can open AT5 and browse to Presets > Converted to confirm they're there. They'll show as empty/silent presets — that's correct, they get overwritten with real tone data each time you load a song.

### Step 4 — Set up the AT5 PC map

AT5 needs to know which Program Change number (PC) corresponds to which preset file. Run this script once from PowerShell to set it up automatically:

    python generate_at5_pc_map.py

This writes a file called `ProgramChangePresetList.ik` into your AT5 documents folder, which tells AT5 to use the `AT5_LIVE` presets when it receives PC messages 120-127.

Then **restart AmpliTube 5** so it loads the new mapping.

### Step 5 — Configure AT5 to receive MIDI

In AmpliTube 5:

1. Go to **Options > Audio/MIDI**
2. Set **MIDI Input** to your MIDI interface (or your loopMIDI port name if using Option B)
3. Go to **Options > Control**
4. Click the **Program Change** tab
5. Tick **Preset Control**
6. Set **Receive Channel** to **All**
7. Click OK

### Step 6 — Find your MIDI device name and start the bridge

The MIDI bridge is a small Python script that runs on Windows and translates the plugin's preset-switch requests into actual MIDI messages.

First, find the exact name Windows uses for your MIDI output device. Open PowerShell and run:

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

This will print something like:

    0: Microsoft GS Wavetable Synth
    1: Scarlett 2i2 USB
    2: AT5 Bridge

Use the name of your audio interface (if using a physical cable loop) or your loopMIDI port name. Copy it exactly.

Put `at5_midi_bridge.py` anywhere convenient on your PC, open a PowerShell window in that folder, and run:

    python .\at5_midi_bridge.py --midi-port "Your Device Name Here"

You should see:

    MIDI output ready -> [1] Your Device Name Here
    Listening on http://localhost:37432

**Leave this PowerShell window open** — the bridge needs to keep running while you use Slopsmith.

---

## Using it

Once everything is running:

1. Open AmpliTube 5
2. Make sure the MIDI bridge is running (the PowerShell window from Step 6)
3. Load any CDLC song in Slopsmith

Within a second or two of loading the song you should see the plugin working:

- In the browser console (press F12 in Slopsmith): `[AT5 Live] 4 tones in live slots (45ms)`
- In the bridge window: `PC -> ch=0 bank=0 prog=120 (preset #121) OK`
- In AT5: the preset display will change as the song plays

The plugin tab in Slopsmith (click "AT5" in the player bar) shows a live log of every preset switch.

---

## Troubleshooting

**Bridge says `{"ok": false}`**
The MIDI port name doesn't match. Re-run the device name script above and copy the name exactly as shown, including capitalisation and spaces.

**Browser console shows `live_convert 422 error`**
`rs_to_at5.py` is missing from the plugin folder. Make sure you copied all three plugin files in Step 1.

**AT5 crashes on startup after setup**
The placeholder preset files were created incorrectly. Delete any files starting with `AT5_LIVE_` from your AT5 `Presets\Converted\` folder, then restart Slopsmith and wait a moment for them to be recreated properly.

**No preset switches happening at all**
Check in order:
1. Is the MIDI bridge running? (the PowerShell window should still be open)
2. Is AT5's MIDI Input set to the right device?
3. Is Program Change > Preset Control ticked in AT5?
4. Is the MIDI cable plugged into both MIDI IN and MIDI OUT? (or loopMIDI running?)

**Bridge window shows PC messages firing but AT5 doesn't switch**
AT5 is not receiving the MIDI. Either the cable loop isn't connected, loopMIDI isn't running, or AT5's MIDI input is set to the wrong device.

**Song loads but nothing happens at all**
Open the browser console (F12) and look for any `[AT5]` messages. If there are none, the plugin may not have loaded — check that `routes.py`, `screen.js`, and `rs_to_at5.py` are all in the `at5_tone` plugin folder and that you restarted the container after copying them.

**The plugin stops the song when I open it**
This is a known Slopsmith limitation — opening any plugin screen pauses playback. It can't be fixed from a plugin. Use the live log in the plugin tab to review what happened after the fact.

---

## How it works (the short version)

Every CDLC song file (PSARC) contains the guitar tone settings used in Rocksmith — amp model, cabinet, pedals, all the knob positions. When you load a song, this plugin reads those settings and converts them into AmpliTube 5 preset files using a mapping of Rocksmith amp/effect models to their AT5 equivalents. It writes those presets to 8 reserved slots, then as the song plays it sends MIDI Program Change messages at exactly the right moments to switch AT5 to the matching preset.

The conversion happens in the background in about 50ms — fast enough that the presets are ready before the first tone change fires.

---

## Limitations

- Works with CDLC (PSARC) songs. Songs in other formats may only get a base tone at song start rather than full switching.
- Up to 8 unique tones per song. Most songs use 2-4, so this is rarely a limit. If a song has more than 8, the first 8 are converted exactly and the rest are silent.
- The Whammy pedal effect (Wharmonator in AT5) requires a one-time MIDI Learn step in AT5 to enable. See `KNOB_CC_MAP` in `routes.py`.
