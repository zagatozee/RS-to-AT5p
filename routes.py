"""AmpliTube 5 Tone Switcher — routes.py v2
- PC table built in background thread
- Persisted to /at5docs/at5_pc_table_cache.json (survives restarts + rebuilds)
- Manual rebuild trigger via POST /api/plugins/at5_tone/pc_table/rebuild
"""

import csv
import json
import logging
import re
import threading
from pathlib import Path
from fastapi import Request

log = logging.getLogger(__name__)

# ── CC map: knob suffix -> MIDI CC number ──────────────────────────────────
# Must match AT5 MIDI Learn assignments
KNOB_CC_MAP = {
    "Bass":        74,
    "Middle":      75,
    "Treble":      76,
    "Presence":    77,
    "Volume":      70,
    "Master":      71,
    "Gain":        72,
    "Reverb":      91,
    # Wharmonator — set this after MIDI Learn in AT5 Options → Control → CC tab
    # "Wharmonator": 1,   # ← UNCOMMENT and set correct CC number after MIDI Learn
}

# Pedal key substrings that indicate a whammy/wah/pitch-shift effect.
# Matched against GearList PrePedal1/2/PostPedal1/2 Key values.
WAH_WHAMMY_KEYS = (
    "whammy", "wah", "wharmonator", "pitch", "harmoniz",
)

# Knob name substrings inside a wah/whammy pedal that represent pedal position.
# Rocksmith knob values are 0-100; we map to CC 0-127.
WAH_POSITION_KNOBS = (
    "position", "pedal", "mix", "amount", "pitch",
)

# ── Module state ───────────────────────────────────────────────────────────
_lock      = threading.Lock()
_pc_table  = None          # None = not loaded yet, {} = loaded but empty
_building  = False
_csv_path  = None
_songs_path = None
_cache_path = None


def _rs_to_cc(rs_value):
    return min(127, max(0, int(rs_value * 127 / 100)))


def _knob_suffix(key):
    return key.split("_")[-1] if "_" in key else key


def _chain(gear):
    return (
        gear.get("Amp",       {}).get("Key", ""),
        gear.get("Cabinet",   {}).get("Key", ""),
        gear.get("PrePedal1", {}).get("Key", ""),
        gear.get("PrePedal2", {}).get("Key", ""),
        gear.get("PostPedal1",{}).get("Key", ""),
        gear.get("PostPedal2",{}).get("Key", ""),
        gear.get("Rack1",     {}).get("Key", ""),
        gear.get("Rack2",     {}).get("Key", ""),
    )


def _is_wah_whammy_key(key):
    """Return True if a pedal key string looks like a wah/whammy/pitch effect."""
    k = key.lower()
    return any(pat in k for pat in WAH_WHAMMY_KEYS)


def _extract_whammy_cc(gear):
    """Scan all pedal slots in a GearList for a wah/whammy pedal.
    Returns a list of {cc, value, knob} dicts (may be empty).
    Only emits CC if KNOB_CC_MAP contains 'Wharmonator'.
    """
    wharmonator_cc = KNOB_CC_MAP.get("Wharmonator")
    if wharmonator_cc is None:
        return []   # Wharmonator CC not yet configured — skip

    pedal_slots = ["PrePedal1", "PrePedal2", "PostPedal1", "PostPedal2"]
    for slot in pedal_slots:
        pedal = gear.get(slot, {})
        if not pedal:
            continue
        key = pedal.get("Key", "")
        if not _is_wah_whammy_key(key):
            continue
        # Found a wah/whammy pedal — look for position knob
        knobs = pedal.get("KnobValues", {})
        for knob_name, rs_val in knobs.items():
            if any(p in knob_name.lower() for p in WAH_POSITION_KNOBS):
                return [{"cc": wharmonator_cc, "value": _rs_to_cc(rs_val), "knob": knob_name}]
        # Pedal found but no position knob matched — emit at heel (0) as safe default
        return [{"cc": wharmonator_cc, "value": 0, "knob": "default_heel"}]

    return []


def _load_cache():
    """Load PC table from disk cache. Returns dict or None."""
    if not _cache_path or not Path(_cache_path).exists():
        return None
    try:
        data = json.loads(Path(_cache_path).read_text(encoding="utf-8"))
        log.info(f"[AT5] PC table loaded from cache: {len(data)} tones")
        return data
    except Exception as e:
        log.warning(f"[AT5] Cache load failed: {e}")
        return None


def _save_cache(table):
    """Save PC table to disk cache."""
    if not _cache_path:
        return
    try:
        Path(_cache_path).write_text(
            json.dumps(table, ensure_ascii=False), encoding="utf-8"
        )
        log.info(f"[AT5] PC table cached: {len(table)} tones → {_cache_path}")
    except Exception as e:
        log.warning(f"[AT5] Cache save failed: {e}")


def _build_sync():
    """Full PC table build — runs in background thread."""
    global _pc_table, _building

    log.info("[AT5] Building PC table...")

    csv_p   = Path(_csv_path)   if _csv_path   else None
    songs_p = Path(_songs_path) if _songs_path else None

    # 1. Load PC assignments from reference CSV
    pc_by_key = {}
    if csv_p and csv_p.exists():
        with open(csv_p, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pc      = int(row.get("PC", 0)) - 1   # CSV is 1-indexed
                key     = row.get("ToneKey", "").strip()
                preset  = row.get("Preset",  "").strip()
                if key:
                    pc_by_key[key] = {
                        "pc":          pc,
                        "preset_name": Path(preset).stem if preset else key,
                    }
    log.info(f"[AT5] CSV: {len(pc_by_key)} top-128 tones")

    if not pc_by_key:
        log.debug("[AT5] No tone CSV found — PC table empty, live convert will handle switching")
        with _lock:
            _pc_table = {}
            _building = False
        return

    # 2. Load tone data from scrape (knobs + signal chains)
    tone_data = {}   # key -> {knobs, chain, amp}
    if songs_p and songs_p.exists():
        tone_files = list(songs_p.rglob("tone_*.json"))
        log.info(f"[AT5] Scanning {len(tone_files)} tone files...")
        for tf in tone_files:
            try:
                d   = json.loads(tf.read_text(encoding="utf-8", errors="replace"))
                td  = d.get("toneData", {})
                key = td.get("Key", "")
                if not key or key in tone_data:
                    continue
                gear  = td.get("GearList", {})
                knobs = gear.get("Amp", {}).get("KnobValues", {})
                tone_data[key] = {
                    "knobs": knobs,
                    "chain": _chain(gear),
                    "amp":   gear.get("Amp", {}).get("Key", ""),
                }
            except Exception:
                pass
        log.info(f"[AT5] Loaded {len(tone_data)} unique tone definitions")

    # 3. Build table
    table = {}

    # Top-128: direct PC, no CC adjustment
    for key, pc_info in pc_by_key.items():
        table[key] = {
            "pc":             pc_info["pc"],
            "preset_name":    pc_info["preset_name"],
            "cc_adjustments": [],
            "in_top128":      True,
        }

    # Remainder: same chain → PC of template + CC diff
    top_chains = {}
    for key, pc_info in pc_by_key.items():
        td = tone_data.get(key, {})
        c  = td.get("chain")
        if c and c not in top_chains:
            top_chains[c] = (key, pc_info)

    cc_covered = 0
    for key, td in tone_data.items():
        if key in table:
            continue
        c = td.get("chain")
        if not c or c not in top_chains:
            continue
        template_key, pc_info = top_chains[c]
        template_td = tone_data.get(template_key, {})
        cc_adj = []
        for rs_key, rs_val in td["knobs"].items():
            suffix = _knob_suffix(rs_key)
            if suffix in KNOB_CC_MAP:
                tmpl_val = template_td.get("knobs", {}).get(rs_key, rs_val)
                if abs(rs_val - tmpl_val) > 2:
                    cc_adj.append({
                        "cc":    KNOB_CC_MAP[suffix],
                        "value": _rs_to_cc(rs_val),
                        "knob":  suffix,
                    })
        table[key] = {
            "pc":             pc_info["pc"],
            "preset_name":    pc_info["preset_name"],
            "cc_adjustments": cc_adj,
            "in_top128":      False,
            "template":       template_key,
        }
        cc_covered += 1

    log.info(f"[AT5] PC table: {len(pc_by_key)} direct + {cc_covered} CC-covered = {len(table)} total")

    _save_cache(table)
    with _lock:
        _pc_table = table
        _building = False


def _get_table():
    """Return current PC table, loading from cache or starting build if needed."""
    global _pc_table, _building

    if _pc_table is not None:
        return _pc_table

    with _lock:
        if _pc_table is not None:
            return _pc_table

        # Try disk cache first
        cached = _load_cache()
        if cached is not None:
            _pc_table = cached
            return _pc_table

        # Start background build
        if not _building:
            _building = True
            t = threading.Thread(target=_build_sync, daemon=True)
            t.start()

        return {}


def _resolve_tone_id(tone_id, song_dir):
    """Match a toneId UUID to a tone key by reading tone JSON files."""
    for tf in song_dir.glob("tone_*.json"):
        if tone_id.lower() in tf.name.lower() or \
           tone_id.replace("-","")[:8].lower() in tf.name.lower():
            try:
                d = json.loads(tf.read_text(encoding="utf-8", errors="replace"))
                return d.get("toneData", {}).get("Key", "")
            except Exception:
                pass
    # Fallback: search inside file content
    for tf in song_dir.glob("tone_*.json"):
        try:
            text = tf.read_text(encoding="utf-8", errors="replace")
            if tone_id in text:
                d = json.loads(text)
                return d.get("toneData", {}).get("Key", "")
        except Exception:
            pass
    return None



# ── Live Convert ───────────────────────────────────────────────────────────
# Converts a PSARC's tones on-demand to AT5 preset files in fixed "live slots"
# (PC 120-127). AT5 re-reads .at5p files from disk on every PC trigger (confirmed),
# so overwriting the slot files mid-session works without restarting AT5.

import importlib.util as _ilu
import sys as _sys
import time as _time
import uuid as _uuid

LIVE_SLOT_START  = 120
LIVE_SLOT_COUNT  = 8
LIVE_SLOT_PREFIX = "AT5_LIVE"

# AT5 version tier: "cs" | "se" | "at5" | "max"
_at5_tier = "max"  # default: full library, no constraints
_at5_free_mode = False  # legacy alias — True maps to tier="cs"

_live_state = {
    "song":       None,
    "slots":      {},   # tone_key -> pc_number
    "warnings":   [],
    "elapsed_ms": 0,
    "source":     None,
}

_prescan_state = {}   # job_id -> progress dict

_rs_to_at5_mod = None   # cached module reference


def _load_converter():
    """Load rs_to_at5.py — tries plugin folder first, then /at5docs/."""
    global _rs_to_at5_mod
    if _rs_to_at5_mod is not None:
        return _rs_to_at5_mod
    candidates = [
        Path(__file__).parent / "rs_to_at5.py",
        Path("/at5docs/rs_to_at5.py"),
    ]
    for p in candidates:
        if p.exists():
            spec = _ilu.spec_from_file_location("rs_to_at5", p)
            mod  = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _rs_to_at5_mod = mod
            log.info(f"[AT5 Live] Loaded rs_to_at5 from {p}")
            return mod
    raise FileNotFoundError(
        "rs_to_at5.py not found in plugin folder or /at5docs/. "
        "Copy it to I:\\Docker\\slopsmith\\plugins\\at5_tone\\"
    )


def _get_presets_dir(at5_dir):
    """Return Path to the AT5 Converted presets folder, creating it if needed."""
    # Check existing paths first
    for p in [Path("/at5docs/Presets/Converted"), at5_dir / "Presets" / "Converted"]:
        if p.exists():
            return p

    # /at5docs is mounted but Presets/Converted doesn't exist yet — create it
    at5docs = Path("/at5docs")
    if at5docs.exists():
        converted = at5docs / "Presets" / "Converted"
        converted.mkdir(parents=True, exist_ok=True)
        log.info(f"[AT5 Live] Created {converted}")
        return converted

    # at5_dir exists (from config) but no Converted folder — create it
    if at5_dir.exists():
        converted = at5_dir / "Presets" / "Converted"
        converted.mkdir(parents=True, exist_ok=True)
        log.info(f"[AT5 Live] Created {converted}")
        return converted

    raise FileNotFoundError(
        "Could not find or create AT5 Presets folder. "
        "Add a volume mount to docker-compose.yml: "
        '"C:/Users/<username>/Documents/IK Multimedia/AmpliTube 5:/at5docs" '
        "(adjust path to match your system)"
    )


def _ensure_slot_files(presets_dir):
    """Write placeholder .at5p files for slots that don't exist yet.
    Uses rs_to_at5's real AT5P_TEMPLATE and NULL_GUID so AT5 can load them without crashing.
    AT5 needs to have seen these filenames before you assign them in the PC map.
    """
    mod = _load_converter()
    created = []
    for i in range(LIVE_SLOT_COUNT):
        path = presets_dir / f"{LIVE_SLOT_PREFIX}_{i:02d}.at5p"
        if not path.exists():
            _write_null_preset(path, i, mod)
            created.append(path.name)
    if created:
        log.info(f"[AT5 Live] Created placeholder slots: {created}")
    return created


def _write_null_preset(path, slot_index, mod=None):
    """Write a valid empty AT5 preset using the real template from rs_to_at5."""
    if mod is None:
        mod = _load_converter()
    NULL   = mod.NULL_GUID
    DESC   = f"AT5 Live Slot {slot_index:02d}"
    na2    = mod.null_attrs(2);  ns2 = mod.null_slots(2)
    na3    = mod.null_attrs(3);  ns3 = mod.null_slots(3)
    na4    = mod.null_attrs(4);  ns4 = mod.null_slots(4)
    na6    = mod.null_attrs(6);  ns6 = mod.null_slots(6)
    xml = mod.AT5P_TEMPLATE.format(
        guid          = str(_uuid.uuid4()),
        amp_guid      = NULL,
        amp_muted     = "1",
        amp_params    = "",
        null_guid     = NULL,
        cab_model     = mod.DEFAULT_CAB_4x12,
        cab_muted     = "1",
        speaker_a     = mod.DEFAULT_SPEAKER_A.replace("-", ""),
        speaker_b     = mod.DEFAULT_SPEAKER_B.replace("-", ""),
        stompa1_attrs = na6, stompa1_slots = ns6,
        stompb1_attrs = na6, stompb1_slots = ns6,
        racka_attrs   = na2, racka_slots   = ns2,
        rackb_attrs   = na2, rackb_slots   = ns2,
        null2_attrs   = na2, null2_slots   = ns2,
        null3_attrs   = na3, null3_slots   = ns3,
        null4_attrs   = na4, null4_slots   = ns4,
        null6_attrs   = na6, null6_slots   = ns6,
        description   = DESC,
        song          = "",
    )
    path.write_text(xml, encoding="utf-8")


def _normalise_gearlist(gear):
    """Normalise PSARC manifest GearList to the {Key, Knobs} format rs_to_at5 expects."""
    SLOTS = ["Amp","Cabinet",
             "PrePedal1","PrePedal2","PrePedal3","PrePedal4",
             "PostPedal1","PostPedal2","PostPedal3","PostPedal4",
             "Rack1","Rack2","Rack3","Rack4"]
    out = {}
    for slot in SLOTS:
        sd = gear.get(slot)
        if not sd:
            continue
        if isinstance(sd, str):
            out[slot] = {"Key": sd, "Knobs": {}}
            continue
        key = sd.get("Key") or sd.get("PedalKey") or ""
        if not key:
            continue
        knobs = sd.get("Knobs") or sd.get("KnobValues") or {}
        if isinstance(knobs, list):
            knobs = {k["Key"]: float(k["Value"]) for k in knobs if "Key" in k and "Value" in k}
        out[slot] = {"Key": key, "Knobs": knobs}
    return out


def _extract_psarc_tones(psarc_path):
    """Extract unique tones from a PSARC using Slopsmith's psarc module.
    Returns dict: { tone_key: {"Key", "Name", "GearList"} }
    """
    from psarc import read_psarc_entries
    entries = read_psarc_entries(str(psarc_path), ["*.json"])
    tones = {}
    for name, data in entries.items():
        try:
            obj = json.loads(data)
        except Exception:
            continue
        # Manifest format: Entries -> Attributes -> GearList / Tones
        for entry_id, entry in obj.get("Entries", {}).items():
            attrs = entry.get("Attributes", {})
            if attrs.get("ArrangementName") in ("Vocals","ShowLights","JVocals"):
                continue
            # Each arrangement has a Tones list
            for tone in attrs.get("Tones", []):
                tk = tone.get("Key","")
                if not tk or tk in tones:
                    continue
                gear = tone.get("GearList", {})
                tones[tk] = {
                    "Key":      tk,
                    "Name":     tone.get("Name", tk),
                    "GearList": _normalise_gearlist(gear),
                }
            # Also grab Tone_Base
            base_key = attrs.get("Tone_Base","")
            if base_key and base_key not in tones:
                # Tone_Base may not have a GearList in this attrs block — skip if missing
                pass
        # Flat tone format (single tone JSON)
        if "GearList" in obj and "Key" in obj:
            tk = obj["Key"]
            if tk not in tones:
                tones[tk] = {
                    "Key":      tk,
                    "Name":     obj.get("Name", tk),
                    "GearList": _normalise_gearlist(obj["GearList"]),
                }
    return tones


def _write_live_slots(tones, presets_dir, slot_offset=0):
    """Convert tones and overwrite live slot .at5p files.
    slot_offset: start writing at this slot index (for partial updates).
    Returns (slot_map, warnings): slot_map = {tone_key: pc_number}
    """
    mod = _load_converter()
    available = LIVE_SLOT_COUNT - slot_offset
    items    = list(tones.items())[:available]
    slot_map = {}
    warnings = []

    if len(tones) > available:
        warnings.append(
            f"{len(tones)} tones but only {available} live slot(s) remaining — "
            f"first {available} converted, rest fall back to PC table."
        )

    for i, (tone_key, tone_data) in enumerate(items):
        slot_idx  = slot_offset + i
        pc_num    = LIVE_SLOT_START + slot_idx
        slot_path = presets_dir / f"{LIVE_SLOT_PREFIX}_{slot_idx:02d}.at5p"
        try:
            # _convert_tone_from_gearlist writes <safe_name>.at5p to output_dir.
            # We want the file at the exact slot path, so write to a temp dir then rename.
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                mod._convert_tone_from_gearlist(
                    tone_key,
                    tone_data.get("Name", tone_key),
                    tone_data["GearList"],
                    slot_path,   # source_path (logging only)
                    tmp_path,    # output_dir
                    free_mode=_at5_free_mode,
                    tier=_at5_tier,
                )
                written = list(tmp_path.glob("*.at5p"))
                if written:
                    import shutil
                    shutil.copy2(written[0], slot_path)
                    slot_map[tone_key] = pc_num
                    log.info(f"[AT5 Live] Slot {i} PC{pc_num}: {tone_key} -> {slot_path.name}")
                else:
                    warnings.append(f"Slot {i} ({tone_key}): converter produced no output")
        except Exception as e:
            warnings.append(f"Slot {i} ({tone_key}): {e}")
            log.error(f"[AT5 Live] {tone_key} error: {e}", exc_info=True)

    return slot_map, warnings



# ── Song-local preset store ────────────────────────────────────────────────
# Each PSARC/sloppak/loose folder can carry its own .at5p preset files.
# On song load the plugin checks here first; live-convert is the fallback.
# File naming: <tone_key>.at5p inside an "at5" subfolder next to the song.
#
# Priority order on load:
#   1. <song_dir>/at5/<tone_key>.at5p  (user-edited, song-local)
#   2. Live convert from PSARC          (auto-generated, written back to #1)
#
# "Save back" copies the current live slot file → song-local store so
# user edits made in AT5 persist across sessions.


def _song_preset_dir(psarc_path: Path, free_mode: bool = None) -> Path:
    """
    Return the song-local preset folder next to the PSARC.
    Uses at5/free/ or at5/max/ subfolder based on free_mode setting.
    This ensures cached presets from one mode never contaminate the other.
    """
    if free_mode is None:
        free_mode = _at5_free_mode
    mode = "free" if free_mode else "max"
    if psarc_path.is_dir():
        return psarc_path / "at5" / mode
    elif psarc_path.suffix == ".sloppak":
        return psarc_path.parent / psarc_path.stem / "at5" / mode
    else:
        return psarc_path.parent / psarc_path.stem / "at5" / mode


def _load_song_presets(psarc_path: Path, free_mode: bool = None) -> dict:
    """
    Return dict of { tone_key: Path } for any .at5p files stored for this song.
    Looks in the mode-specific subfolder (at5/free/ or at5/max/).
    Returns empty dict if folder doesn't exist yet.
    """
    d = _song_preset_dir(psarc_path, free_mode)
    if not d.exists():
        return {}
    return {p.stem: p for p in d.glob("*.at5p")}


def _seed_song_presets(psarc_path: Path, slot_map: dict,
                        presets_dir: Path, free_mode: bool = None) -> dict:
    """
    After live-convert, copy the generated live slot files into the
    song-local at5/<mode>/ folder so they persist and can be user-edited.
    Returns { tone_key: dest_path } for files written.
    Skips any tone that already has a file (preserves user edits).
    """
    song_dir = _song_preset_dir(psarc_path, free_mode)
    song_dir.mkdir(parents=True, exist_ok=True)
    seeded = {}
    for tone_key, pc_num in slot_map.items():
        dest = song_dir / f"{tone_key}.at5p"
        if dest.exists():
            continue                        # never overwrite user-edited file
        slot_idx = pc_num - LIVE_SLOT_START
        slot_file = presets_dir / f"{LIVE_SLOT_PREFIX}_{slot_idx:02d}.at5p"
        if slot_file.exists():
            import shutil
            shutil.copy2(slot_file, dest)
            seeded[tone_key] = str(dest)
    if seeded:
        log.info(f"[AT5 Live] Seeded {len(seeded)} preset(s) -> {song_dir}")
    return seeded


def _copy_song_presets_to_slots(song_presets: dict, slot_map_order: list,
                                 presets_dir: Path) -> dict:
    """
    Copy song-local .at5p files into live slots, maintaining order.
    slot_map_order: list of tone_keys in slot order (slot 0, 1, 2 …)
    Returns { tone_key: pc_number } slot map.
    """
    import shutil
    result = {}
    for i, tone_key in enumerate(slot_map_order[:LIVE_SLOT_COUNT]):
        if tone_key not in song_presets:
            continue
        pc_num    = LIVE_SLOT_START + i
        slot_file = presets_dir / f"{LIVE_SLOT_PREFIX}_{i:02d}.at5p"
        shutil.copy2(song_presets[tone_key], slot_file)
        result[tone_key] = pc_num
        log.info(f"[AT5 Live] Slot {i} PC{pc_num}: {tone_key} <- song-local {('free' if _at5_free_mode else 'max')} preset")
    return result

# ── Plugin setup ───────────────────────────────────────────────────────────

def setup(app, context):
    global _csv_path, _songs_path, _cache_path

    at5_dir = context["config_dir"].parent   # IK Multimedia/AmpliTube 5

    # Resolve paths — Docker mounts take priority
    for csv_candidate in [Path("/at5docs/at5_pc_reference.csv"), at5_dir / "at5_pc_reference.csv"]:
        if csv_candidate.exists():
            _csv_path = str(csv_candidate)
            break

    # Optional: mount /scrape in docker-compose.yml to enable PC table tone matching
    for songs_candidate in [Path("/scrape")]:
        if songs_candidate.exists():
            _songs_path = str(songs_candidate)
            break

    # Cache lives in at5docs so it survives container rebuilds
    for cache_dir in [Path("/at5docs"), at5_dir]:
        if cache_dir.exists():
            _cache_path = str(cache_dir / "at5_pc_table_cache.json")
            break

    log.info(f"[AT5] csv={_csv_path} songs={_songs_path} cache={_cache_path}")

    # Load from cache immediately (non-blocking)
    _get_table()
    _setup_cdlc_routes(app, context)

    # ── Live convert setup ────────────────────────────────────────────────
    try:
        _live_presets_dir = _get_presets_dir(at5_dir)
        _ensure_slot_files(_live_presets_dir)
        log.info(f"[AT5 Live] Slots ready at {_live_presets_dir}, PC {LIVE_SLOT_START}–{LIVE_SLOT_START+LIVE_SLOT_COUNT-1}")
    except Exception as e:
        _live_presets_dir = None
        log.warning(f"[AT5 Live] Setup failed (non-fatal): {e}")

    @app.post("/api/plugins/at5_tone/live_convert")
    async def live_convert(request: Request):
        """Convert a PSARC's tones into live slots on demand.
        Body: { "filename": "ragekilling_p.psarc" }
        """
        if _live_presets_dir is None:
            return {"status": "error", "message": "Live slots not configured — check logs"}
        try:
            body = await request.json()
        except Exception:
            body = {}
        filename = body.get("filename", "")
        if not filename:
            return {"status": "error", "message": "filename required"}

        # Avoid re-converting the same song
        if _live_state["song"] == filename and _live_state["slots"]:
            return {"status": "ok", "cached": True, **_live_state}

        t0 = _time.time()

        # Locate the PSARC
        dlc_dir = context.get("get_dlc_dir", lambda: None)()
        psarc_path = None
        if dlc_dir:
            parts = filename.replace('\\', '/').split('/')
            candidates = [Path(dlc_dir) / filename]
            for i in range(len(parts)):
                candidates.append(Path(dlc_dir) / '/'.join(parts[i:]))
            for c in candidates:
                if c.resolve().exists():
                    psarc_path = c.resolve()
                    break
        if not psarc_path:
            return {"status": "error", "message": f"PSARC not found: {filename}"}

        # ── Step 1: check song-local preset store ─────────────────────────
        song_presets = _load_song_presets(psarc_path)
        if song_presets:
            # We have song-local presets — extract tone order from PSARC
            # so we can copy them into slots in the right order
            try:
                tones = _extract_psarc_tones(psarc_path)
            except Exception:
                tones = {}
            tone_order = list(tones.keys()) if tones else list(song_presets.keys())

            # Use song-local files for tones we have, live-convert for the rest
            missing = [k for k in tone_order if k not in song_presets]
            slot_map = _copy_song_presets_to_slots(
                song_presets, tone_order, _live_presets_dir)
            warnings = []
            source = "song-local"

            if missing and tones:
                # Convert and slot the missing tones
                missing_tones = {k: tones[k] for k in missing if k in tones}
                if missing_tones:
                    # Write into slots after the song-local ones
                    next_slot = len(slot_map)
                    extra_map, extra_warn = _write_live_slots(
                        missing_tones, _live_presets_dir,
                        slot_offset=next_slot)
                    slot_map.update(extra_map)
                    warnings.extend(extra_warn)
                    # Seed the newly converted ones back to song folder
                    _seed_song_presets(psarc_path, extra_map, _live_presets_dir)

            elapsed = int((_time.time() - t0) * 1000)
            log.info(f"[AT5 Live] {filename}: {len(slot_map)} tones from {source} in {elapsed}ms")

        else:
            # ── Step 2: no song-local presets — live convert ───────────────
            try:
                tones = _extract_psarc_tones(psarc_path)
            except ImportError:
                return {"status": "error", "message": "psarc module unavailable — must run inside Slopsmith container"}
            except Exception as e:
                return {"status": "error", "message": f"Extraction failed: {e}"}

            if not tones:
                return {"status": "error", "message": f"No tones found in {filename}"}

            slot_map, warnings = _write_live_slots(tones, _live_presets_dir)
            source = "live-convert"
            elapsed = int((_time.time() - t0) * 1000)

            # Seed converted presets into song folder for future use / user editing
            _seed_song_presets(psarc_path, slot_map, _live_presets_dir)
            log.info(f"[AT5 Live] {filename}: {len(slot_map)} tones {source} in {elapsed}ms")

        _live_state.update({
            "song":       filename,
            "slots":      slot_map,
            "warnings":   warnings,
            "elapsed_ms": elapsed,
            "source":     source,
        })

        return {
            "status":      "ok",
            "slots":       slot_map,
            "warnings":    warnings,
            "elapsed_ms":  elapsed,
            "source":      source,
            "song_presets": list(song_presets.keys()),
        }

    @app.get("/api/plugins/at5_tone/settings")
    def get_settings():
        return {
            "tier":      _at5_tier,
            "free_mode": _at5_tier == "cs",  # legacy compat
        }

    @app.post("/api/plugins/at5_tone/settings")
    async def update_settings(request: Request):
        global _at5_tier, _at5_free_mode
        try:
            body = await request.json()
        except Exception:
            body = {}
        if "tier" in body:
            new_tier = body["tier"]
            if new_tier in ("cs", "se", "at5", "max"):
                _at5_tier = new_tier
                _at5_free_mode = (_at5_tier == "cs")
                log.info(f"[AT5] tier set to {_at5_tier}")
                _live_state.update({"song": None, "slots": {}, "warnings": [], "elapsed_ms": 0})
        elif "free_mode" in body:
            # Legacy boolean support
            _at5_tier = "cs" if bool(body["free_mode"]) else "max"
            _at5_free_mode = (_at5_tier == "cs")
            log.info(f"[AT5] tier set to {_at5_tier} (via free_mode)")
            _live_state.update({"song": None, "slots": {}, "warnings": [], "elapsed_ms": 0})
        return {"status": "ok", "tier": _at5_tier, "free_mode": _at5_free_mode}

    @app.get("/api/plugins/at5_tone/live_status")
    def live_status():
        return {
            **_live_state,
            "slot_start":  LIVE_SLOT_START,
            "slot_count":  LIVE_SLOT_COUNT,
            "presets_dir": str(_live_presets_dir) if _live_presets_dir else None,
            "free_mode":   _at5_free_mode,
            "tier":        _at5_tier,
            "cache_mode":  _at5_tier,
        }

    @app.post("/api/plugins/at5_tone/preset/save-back")
    async def preset_save_back(request: Request):
        """
        Copy the current live slot file(s) back to the song-local at5/ folder,
        overwriting any existing file.  Call this after the user has dialled in
        a tone in AT5 and wants to save it permanently with the song.

        Body: { "tone_key": "RageKilling_lead" }   -- save one tone
              { "tone_key": "*" }                   -- save all current slots
        """
        try:
            body = await request.json()
        except Exception:
            body = {}

        if not _live_state.get("song"):
            return {"status": "error", "message": "No song loaded"}

        dlc_dir = context.get("get_dlc_dir", lambda: None)()
        if not dlc_dir:
            return {"status": "error", "message": "DLC dir unavailable"}

        filename   = _live_state["song"]
        psarc_path = (Path(dlc_dir) / filename).resolve()
        if not psarc_path.exists():
            return {"status": "error", "message": f"PSARC not found: {filename}"}

        song_dir = _song_preset_dir(psarc_path)  # uses current free_mode
        song_dir.mkdir(parents=True, exist_ok=True)

        tone_key   = body.get("tone_key", "*")
        slots      = _live_state.get("slots", {})
        to_save    = slots if tone_key == "*" else {tone_key: slots[tone_key]} if tone_key in slots else {}

        if not to_save:
            return {"status": "error", "message": f"Tone key '{tone_key}' not in current slots"}

        import shutil
        saved = []
        for tk, pc_num in to_save.items():
            slot_idx  = pc_num - LIVE_SLOT_START
            slot_file = _live_presets_dir / f"{LIVE_SLOT_PREFIX}_{slot_idx:02d}.at5p"
            if not slot_file.exists():
                continue
            dest = song_dir / f"{tk}.at5p"
            shutil.copy2(slot_file, dest)
            saved.append(tk)
            log.info(f"[AT5 Live] Saved back: {tk} -> {dest}")

        return {
            "status": "ok",
            "saved":  saved,
            "song_dir": str(song_dir),
        }

    @app.post("/api/plugins/at5_tone/prescan")
    async def prescan(request: Request):
        """
        Batch-convert tones for a list of PSARCs (or all PSARCs in the DLC dir).
        Seeds .at5p files into each song's at5/ subfolder.
        Skips songs that already have a complete set.

        Body: { "filenames": ["song1.psarc", ...] }  -- specific files
              {}                                      -- all PSARCs in DLC dir

        Returns immediately with a job ID; conversion runs in background.
        Poll GET /api/plugins/at5_tone/prescan/status for progress.
        """
        try:
            body = await request.json()
        except Exception:
            body = {}

        dlc_dir = context.get("get_dlc_dir", lambda: None)()
        if not dlc_dir:
            return {"status": "error", "message": "DLC dir unavailable"}

        dlc_path = Path(dlc_dir)
        filenames = body.get("filenames")
        if filenames:
            psarcs = [dlc_path / f for f in filenames]
        else:
            psarcs = list(dlc_path.rglob("*.psarc"))

        if not psarcs:
            return {"status": "error", "message": "No PSARCs found"}

        # Run in background thread so request returns immediately
        import threading
        job_id = str(_uuid.uuid4())[:8]
        _prescan_state[job_id] = {
            "total": len(psarcs), "done": 0, "skipped": 0,
            "errors": 0, "running": True, "job_id": job_id,
        }

        def _run():
            state = _prescan_state[job_id]
            for psarc_path in psarcs:
                if not psarc_path.exists():
                    state["errors"] += 1
                    state["done"]   += 1
                    continue
                try:
                    existing = _load_song_presets(psarc_path)
                    tones    = _extract_psarc_tones(psarc_path)
                    missing  = [k for k in tones if k not in existing]
                    if not missing:
                        state["skipped"] += 1
                        state["done"]    += 1
                        continue
                    # Convert missing tones to a temp dir, seed to song folder
                    import tempfile, shutil
                    with tempfile.TemporaryDirectory() as tmp:
                        tmp_path = Path(tmp)
                        mod = _load_converter()
                        slot_map = {}
                        for i, tk in enumerate(missing[:LIVE_SLOT_COUNT]):
                            td = tones[tk]
                            results = mod._convert_tone_from_gearlist(
                                tk, td.get("Name", tk), td["GearList"],
                                psarc_path, tmp_path)
                            written = list(tmp_path.glob("*.at5p"))
                            if written:
                                slot_map[tk] = LIVE_SLOT_START + i
                                dest = _song_preset_dir(psarc_path) / f"{tk}.at5p"
                                _song_preset_dir(psarc_path).mkdir(parents=True, exist_ok=True)
                                if not dest.exists():
                                    shutil.copy2(written[0], dest)
                                for f in tmp_path.glob("*.at5p"):
                                    f.unlink()
                except Exception as e:
                    log.error(f"[AT5 Prescan] {psarc_path.name}: {e}")
                    state["errors"] += 1
                state["done"] += 1
            state["running"] = False
            log.info(f"[AT5 Prescan] Job {job_id} done: "
                     f"{state['done']} processed, {state['skipped']} skipped, "
                     f"{state['errors']} errors")

        threading.Thread(target=_run, daemon=True).start()
        return {"status": "ok", "job_id": job_id, "total": len(psarcs)}

    @app.get("/api/plugins/at5_tone/prescan/status")
    def prescan_status(job_id: str = ""):
        if job_id and job_id in _prescan_state:
            return _prescan_state[job_id]
        # Return all jobs if no specific id
        return list(_prescan_state.values())

    # ── Endpoints ──────────────────────────────────────────────────────────

    @app.get("/api/plugins/at5_tone/pc_table")
    def get_pc_table():
        return _get_table()

    @app.get("/api/plugins/at5_tone/pc_table/status")
    def get_pc_table_status():
        table = _get_table()
        in_top = sum(1 for v in table.values() if v.get("in_top128"))
        with_cc = sum(1 for v in table.values() if v.get("cc_adjustments"))
        return {
            "total":       len(table),
            "in_top128":   in_top,
            "with_cc":     with_cc,
            "building":    _building,
            "csv_path":    _csv_path,
            "csv_exists":  bool(_csv_path and Path(_csv_path).exists()),
            "songs_path":  _songs_path,
            "cache_path":  _cache_path,
            "cache_exists": bool(_cache_path and Path(_cache_path).exists()),
        }

    @app.post("/api/plugins/at5_tone/pc_table/rebuild")
    def rebuild_pc_table():
        """Manual rebuild trigger — clears cache and restarts background scan."""
        global _pc_table, _building
        with _lock:
            if _building:
                return {"ok": False, "error": "Already building"}
            _pc_table = None
            # Delete cache so _get_table doesn't reload it
            if _cache_path and Path(_cache_path).exists():
                try: Path(_cache_path).unlink()
                except: pass
            _building = True
        threading.Thread(target=_build_sync, daemon=True).start()
        return {"ok": True, "message": "Rebuild started — takes ~60s"}

    @app.get("/api/plugins/at5_tone/song-tone-schedule/{filename:path}")
    def get_tone_schedule(filename: str, arrangement: str = ""):
        """Return tone change schedule from song XML files."""
        if not _songs_path:
            return {"tones": [], "error": "Songs path not configured"}

        songs_dir = Path(_songs_path)

        try:
            import urllib.parse
            decoded = urllib.parse.unquote(filename)
        except Exception:
            decoded = filename

        song_dir = (songs_dir / decoded).resolve()
        try:
            song_dir.relative_to(songs_dir.resolve())
        except ValueError:
            return {"tones": [], "error": "Invalid path"}

        if not song_dir.exists():
            title = Path(decoded).name
            matches = list(songs_dir.rglob(f"*{title}*"))
            dirs = [m if m.is_dir() else m.parent for m in matches]
            if dirs:
                song_dir = dirs[0]
            else:
                return {"tones": [], "error": f"Song not found: {decoded}"}

        # Filter XMLs by arrangement name if provided
        # XML filenames: Official_Lead1_<uuid>.xml, UGC_bass_<uuid>.xml etc.
        arr_lower = arrangement.lower() if arrangement else ""

        def xml_matches_arrangement(xml_path):
            if not arr_lower:
                return True
            name_lower = xml_path.name.lower()
            # Skip lyrics and non-arrangement files
            if 'lyric' in name_lower or 'showlight' in name_lower:
                return False
            # Match arrangement name in filename
            return arr_lower in name_lower

        tones = []
        all_xmls = sorted(song_dir.rglob("*.xml"))

        # Try arrangement-filtered XMLs first
        filtered_xmls = [x for x in all_xmls if xml_matches_arrangement(x)]
        # Fall back to all XMLs if no filtered match found
        xmls_to_try = filtered_xmls if filtered_xmls else all_xmls

        for xml_file in xmls_to_try:
            if 'lyric' in xml_file.name.lower() or 'showlight' in xml_file.name.lower():
                continue
            try:
                text = xml_file.read_text(encoding="utf-8", errors="replace")
                iterations = re.findall(
                    r'toneId="([^"]+)"\s+startTime="([^"]+)"', text
                )
                if not iterations:
                    continue
                for tone_id, start_time in iterations:
                    key = _resolve_tone_id(tone_id, song_dir)
                    tones.append({
                        "toneId":    tone_id,
                        "key":       key or tone_id,
                        "startTime": float(start_time),
                    })
                if tones:
                    break
            except Exception:
                continue

        if not tones:
            for tf in sorted(song_dir.glob("tone_*.json")):
                try:
                    d   = json.loads(tf.read_text(encoding="utf-8", errors="replace"))
                    key = d.get("toneData", {}).get("Key", "")
                    if key:
                        tones.append({"key": key, "startTime": 0.0})
                except Exception:
                    pass

        return {"tones": tones, "source": str(song_dir), "arrangement": arrangement}


# ── CDLC tone matching ─────────────────────────────────────────────────────

def _match_cdlc_tone(gear, table, tone_data):
    """Find best PC match for a CDLC tone's GearList.
    Returns (pc, preset_name, match_type, cc_adjustments) or None.
    cc_adjustments includes whammy/wah CC if a wah pedal is detected.
    """
    amp_key = gear.get("Amp", {}).get("Key", "")
    whammy_cc = _extract_whammy_cc(gear)   # [] or [{cc, value, knob}]
    
    # Build amp-key -> best PC lookup from our table
    amp_to_pc = {}
    for key, entry in table.items():
        td = tone_data.get(key, {})
        a = td.get("amp", "")
        if a and a not in amp_to_pc:
            amp_to_pc[a] = entry

    # 1. Same amp key
    if amp_key and amp_key in amp_to_pc:
        e = amp_to_pc[amp_key]
        return e["pc"], e["preset_name"], "amp_match", whammy_cc

    # 2. Same amp family (e.g. Amp_CA100 -> Amp_CA38, Amp_CA85)
    if amp_key:
        # Extract family prefix: Amp_CA100 -> Amp_CA
        parts = amp_key.split("_")
        if len(parts) >= 2:
            # Try progressively shorter prefixes
            family = "_".join(parts[:2])  # e.g. Amp_CA
            family_prefix = ''.join(c for c in family if not c.isdigit())  # Amp_CA
            for a, e in amp_to_pc.items():
                a_prefix = ''.join(c for c in a if not c.isdigit())
                if a_prefix == family_prefix:
                    return e["pc"], e["preset_name"], "amp_family", whammy_cc

    # 3. Tone descriptor — classify by effects present
    has_dist  = bool(gear.get("PrePedal1") or gear.get("PrePedal2"))
    has_verb  = any(
        "verb" in str(gear.get(f"Rack{i}", {}).get("Key", "")).lower() or
        "verb" in str(gear.get(f"PostPedal{i}", {}).get("Key", "")).lower()
        for i in [1, 2, 3, 4]
    )
    amp_key_l = amp_key.lower()
    is_bass   = "bass" in amp_key_l or "bt" in amp_key_l

    # Pick default by instrument/character
    defaults = {
        "bass":       "BassWR",
        "distortion": "CaliDist",
        "clean_verb": "JzUSCleanSpring",
        "clean":      "USClean",
        "acoustic":   "AcStrum",
    }

    if is_bass:
        fallback_key = "bass"
    elif has_dist:
        fallback_key = "distortion"
    elif has_verb:
        fallback_key = "clean_verb"
    else:
        fallback_key = "clean"

    tone_key = defaults[fallback_key]
    if tone_key in table:
        e = table[tone_key]
        return e["pc"], e["preset_name"], f"descriptor_{fallback_key}", whammy_cc

    # 4. Last resort — PC 0 (most used preset)
    if table:
        first = next(iter(table.values()))
        return first["pc"], first["preset_name"], "default", whammy_cc

    return None


# ── This is added to setup() ───────────────────────────────────────────────
def _setup_cdlc_routes(app, context):
    """Register CDLC tone matching endpoints. Called from setup()."""

    @app.get("/api/plugins/at5_tone/match-cdlc-tones/{filename:path}")
    def match_cdlc_tones(filename: str, skip_scrape: bool = False):
        """For a PSARC/CDLC file, read its tone GearLists and find
        the best AT5 PC match for each tone key."""
        table = _get_table()
        if not table:
            return {"matches": {}, "error": "PC table not ready"}

        # Load tone_data (amp keys) from our scrape for matching
        # skip_scrape=True skips this expensive scan (used by Tone Browser)
        td = {}
        if _songs_path and not skip_scrape:
            sp = Path(_songs_path)
            for tf in list(sp.rglob("tone_*.json"))[:5000]:  # sample
                try:
                    d = json.loads(tf.read_text(encoding="utf-8", errors="replace"))
                    key = d.get("toneData", {}).get("Key", "")
                    gear = d.get("toneData", {}).get("GearList", {})
                    if key and key not in td:
                        td[key] = {
                            "amp": gear.get("Amp", {}).get("Key", ""),
                            "chain": _chain(gear),
                        }
                except Exception:
                    pass

        # Find the PSARC/CDLC file
        dlc_dir = context.get("get_dlc_dir", lambda: None)()
        if not dlc_dir:
            return {"matches": {}, "error": "DLC folder not configured"}

        import urllib.parse
        decoded = urllib.parse.unquote(filename)
        # Try the path as-is, then with common prefix variations
        psarc_path = None
        candidates = [
            Path(dlc_dir) / decoded,
            Path(dlc_dir) / decoded.lstrip('/'),
        ]
        # Also try stripping leading path components (Songs/, CDLC/ etc)
        parts = decoded.replace('\\', '/').split('/')
        for i in range(len(parts)):
            candidates.append(Path(dlc_dir) / '/'.join(parts[i:]))

        for c in candidates:
            if c.resolve().exists():
                psarc_path = c.resolve()
                break

        if not psarc_path:
            return {"matches": {}, "error": f"File not found: {decoded} (tried {len(candidates)} paths)"}

        if psarc_path.name.lower().endswith(".sloppak") or psarc_path.is_dir():
            return {"matches": {}, "error": "sloppak not supported for CDLC matching"}

        # Read tone GearLists from PSARC manifest
        try:
            from psarc import read_psarc_entries
            files = read_psarc_entries(str(psarc_path), ["*.json"])
        except Exception as e:
            return {"matches": {}, "error": str(e)}

        matches = {}
        # Track which arrangements each tone key appears in
        tone_arrangements = {}

        for path, data in sorted(files.items()):
            if not path.endswith(".json"):
                continue
            try:
                j = json.loads(data)
            except Exception:
                continue
            for k, v in j.get("Entries", {}).items():
                attrs = v.get("Attributes", {})
                arr = attrs.get("ArrangementName", "")
                if arr in ("Vocals", "ShowLights", "JVocals"):
                    continue
                for tone in attrs.get("Tones", []):
                    tone_key = tone.get("Key", "")
                    if not tone_key:
                        continue
                    # Track arrangement membership
                    if tone_key not in tone_arrangements:
                        tone_arrangements[tone_key] = []
                    if arr and arr not in tone_arrangements[tone_key]:
                        tone_arrangements[tone_key].append(arr)
                    if tone_key in matches:
                        continue
                    # Already in PC table — exact match
                    if tone_key in table:
                        e = table[tone_key]
                        matches[tone_key] = {
                            "pc":         e["pc"],
                            "preset":     e["preset_name"],
                            "match_type": "exact",
                        }
                        continue
                    # Try GearList matching
                    gear = tone.get("GearList", {})
                    result = _match_cdlc_tone(gear, table, td)
                    if result:
                        pc, preset, match_type, cc_adj = result
                        matches[tone_key] = {
                            "pc":             pc,
                            "preset":         preset,
                            "match_type":     match_type,
                            "cc_adjustments": cc_adj,
                        }

        # Add arrangement info to each match
        for tone_key in matches:
            matches[tone_key]["arrangements"] = tone_arrangements.get(tone_key, [])

        return {"matches": matches, "total": len(matches)}
