// AmpliTube 5 Tone Switcher — v3
// - setInterval + highway.getTime() (no setRenderer — doesn't interfere with visuals)
// - Live tone log with per-song history
// - Tone browser with manual trigger
// - All UI functions exposed as globals

(function () {
'use strict';

// ── Config ─────────────────────────────────────────────────────────────────
const AT5_BRIDGE_URL = 'http://localhost:37432';
const AT5_MIDI_CH    = 0;
const LOG_MAX        = 200;
let AT5_PREFIRE_MS   = parseFloat(localStorage.getItem('at5_prefire_ms') ?? '0.2');   // max log entries to keep

// ── Module state ───────────────────────────────────────────────────────────
let _at5Filename   = null;
let _at5PcTable    = {};
let _at5PcLoaded   = false;
let _at5BridgeOk   = false;
let _at5MidiAccess = null;
let _at5MidiOutput = null;

// Scheduler
let _at5Timer      = null;
let _at5Schedule   = [];
let _at5LastFired  = -1;
let _at5LastKey    = null;
let _at5LastT      = null;   // previous poll time — used to detect seeks

// ── Live convert state ────────────────────────────────────────────────────
const LIVE_SLOT_START = 120;
const LIVE_SLOT_COUNT = 8;
let _at5LiveSlots    = {};   // tone_key -> pc_number (from live convert)
let _at5LiveLastFile = null; // avoid re-converting same song
let _at5LiveEnabled  = true; // set false if backend says rs_to_at5 missing

// ── Live convert state ────────────────────────────────────────────────────
// Tone log — persists across screen navigations
// [{ts, toneKey, pc, presetName, songTitle, arrangement, firedAt}]
let _at5Log = [];

// ── Filename capture (same as tabview) ────────────────────────────────────
(function () {
    const orig = typeof window.playSong === 'function' ? window.playSong : null;
    if (orig) {
        window.playSong = async function (filename, arrangement) {
            _at5Filename = filename;
            const result = await orig.call(this, filename, arrangement);
            _at5InjectBadge();
            // Don't start scheduler here — wait for highway ready event
            return result;
        };
    }
    // Hook highway ready event for reliable song + arrangement detection
    if (window.highway && typeof highway.addDrawHook === 'function') {
        let _lastScheduledFile = null;
        highway.addDrawHook(() => {
            const info = highway.getSongInfo?.();
            if (!info || !_at5Filename) return;
            const key = `${_at5Filename}|${info.arrangement}`;
            if (key !== _lastScheduledFile) {
                _lastScheduledFile = key;
                _at5StartScheduler(_at5Filename);
            }
        });
    } else {
        // Fallback: start from playSong with delay
        const origFallback = window.playSong;
        if (origFallback) {
            window.playSong = async function (filename, arrangement) {
                _at5Filename = filename;
                const result = await origFallback.call(this, filename, arrangement);
                _at5InjectBadge();
                _at5StartScheduler(filename);
                return result;
            };
        }
    }
    if (window.slopsmith?.on) {
        window.slopsmith.on('arrangement:changed', (e) => {
            if (e?.detail?.filename) _at5Filename = e.detail.filename;
        });
    }
})();

// ── PC table ───────────────────────────────────────────────────────────────
async function _at5LoadPcTable() {
    if (_at5PcLoaded) return;
    try {
        const r = await fetch('/api/plugins/at5_tone/pc_table');
        if (!r.ok) return;
        const data = await r.json();
        const count = Object.keys(data).length;
        if (count > 0) {
            _at5PcTable = data;
            _at5PcLoaded = true;
            console.log(`[AT5] PC table loaded: ${count} tone keys`);
        }
    } catch (e) { console.warn('[AT5] PC table load failed:', e); }
}

function _at5Lookup(toneKey) {
    if (!toneKey) return null;
    // Live slots take priority — exact conversion of this song's actual tones
    const livePC = _at5LiveSlots[toneKey];
    if (livePC !== undefined) {
        return { pc: livePC, preset_name: `LIVE_${livePC}`, in_top128: false, cc_adjustments: [], live: true };
    }
    // Fall back to pre-baked PC table
    if (_at5PcTable[toneKey]) return _at5PcTable[toneKey];
    const lower = toneKey.toLowerCase();
    for (const [k, v] of Object.entries(_at5PcTable))
        if (k.toLowerCase() === lower) return v;
    return null;
}

// ── Bridge ─────────────────────────────────────────────────────────────────
async function _at5Ping() {
    try {
        const r = await fetch(`${AT5_BRIDGE_URL}/ping`, { signal: AbortSignal.timeout(500) });
        _at5BridgeOk = (await r.json()).ok;
    } catch { _at5BridgeOk = false; }
    return _at5BridgeOk;
}

async function _at5SendPC(program, ccAdj) {
    const ch = AT5_MIDI_CH;

    // 1. Internal VST (Desktop)
    if (window.slopsmithDesktop?.audio) {
        try {
            const api = window.slopsmithDesktop.audio;
            const chain = await api.getChainState();
            const slots = chain.filter(s => s.type === 0);
            if (slots.length) {
                for (const slot of slots) {
                    api.sendMidiToSlot(slot.id, 1, ch+1, program & 0x7F, 0);
                    api.sendMidiToSlot(slot.id, 0, 0xC0|ch, program & 0x7F, 0);
                }
                return;
            }
        } catch {}
    }

    // 2. Bridge
    if (_at5BridgeOk || await _at5Ping()) {
        try {
            const r = await fetch(`${AT5_BRIDGE_URL}/pc`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel: ch, bank_msb: 0, bank_lsb: 0, program }),
                signal: AbortSignal.timeout(1000)
            });
            if ((await r.json()).ok && ccAdj?.length) {
                await new Promise(res => setTimeout(res, 50));
                for (const { cc, value } of ccAdj) {
                    await fetch(`${AT5_BRIDGE_URL}/cc`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ channel: ch, cc, value }),
                        signal: AbortSignal.timeout(500)
                    });
                }
            }
            return;
        } catch { _at5BridgeOk = false; }
    }

    // 3. Web MIDI
    if (_at5MidiOutput) _at5MidiOutput.send([0xC0|(ch&0x0F), program & 0x7F]);
}

// ── MIDI init ──────────────────────────────────────────────────────────────
function _at5InitMidi() {
    if (!navigator.requestMIDIAccess) return;
    navigator.requestMIDIAccess({ sysex: false }).then(access => {
        _at5MidiAccess = access;
        _at5PickOutput();
        access.onstatechange = _at5PickOutput;
    }).catch(() => {});
}

function _at5PickOutput() {
    const saved = localStorage.getItem('at5_output_id');
    if (!_at5MidiAccess || saved === 'internal' || saved === 'bridge') {
        _at5MidiOutput = null; return;
    }
    const outputs = [];
    _at5MidiAccess.outputs.forEach(o => outputs.push(o));
    _at5MidiOutput = outputs.find(o => o.id === saved) || outputs[0] || null;
}

// ── Tone log ───────────────────────────────────────────────────────────────
function _at5LogTone(toneKey, entry, firedAt) {
    const songInfo = highway?.getSongInfo?.() || {};
    _at5Log.unshift({
        ts:          Date.now(),
        firedAt:     firedAt?.toFixed(1) ?? '0.0',
        toneKey,
        pc:          entry?.pc ?? null,
        presetName:  entry?.preset_name ?? null,
        inTop128:    entry?.in_top128 ?? false,
        ccCount:     entry?.cc_adjustments?.length ?? 0,
        ccAdj:       entry?.cc_adjustments ?? [],
        song:        songInfo.title ?? _at5Filename ?? '',
        artist:      songInfo.artist ?? '',
        arrangement: songInfo.arrangement ?? '',
        filename:    _at5Filename ?? '',
    });
    if (_at5Log.length > LOG_MAX) _at5Log.length = LOG_MAX;
    _at5RefreshLogUI();
}

function _at5RefreshLogUI() {
    const el = document.getElementById('at5-log-list');
    if (!el) return;
    if (!_at5Log.length) {
        el.innerHTML = `<p class="text-xs text-gray-600 py-4 text-center">Play a song to see tone switches here.</p>`;
        return;
    }
    el.innerHTML = _at5Log.map((entry, i) => `
        <div class="flex items-center gap-3 py-2 border-b border-gray-800/50 hover:bg-dark-700/30 px-2 rounded group">
            <span class="text-xs text-gray-600 w-14 shrink-0 font-mono">${entry.firedAt}s</span>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-xs font-semibold text-white truncate">${esc(entry.toneKey)}</span>
                    ${entry.pc !== null
                        ? `<span class="text-xs text-orange-400 font-mono shrink-0">PC ${entry.pc + 1}</span>`
                        : `<span class="text-xs text-red-500 shrink-0">not mapped</span>`}
                    ${entry.ccCount ? (() => {
                        const isWah = entry.ccAdj?.some(c => c.knob && (
                            c.knob.toLowerCase().includes('whammy') ||
                            c.knob.toLowerCase().includes('wah') ||
                            c.knob.toLowerCase().includes('position') ||
                            c.knob === 'default_heel'
                        ));
                        const tip = entry.ccAdj?.map(c=>`CC${c.cc}=${c.value} (${c.knob})`).join(', ') || '';
                        return `<span class="text-xs text-blue-400 shrink-0" title="${tip}">${isWah ? '〰 WAH' : entry.ccCount + ' CC'}</span>`;
                    })() : ''}
                    ${entry.inTop128 ? `<span class="text-xs text-green-600 shrink-0">●</span>` : ''}
                </div>
                <div class="text-xs text-gray-600 truncate">${esc(entry.presetName ?? '')} · ${esc(entry.song)}</div>
            </div>
            ${entry.pc !== null ? `
            <button onclick="_at5FireLogEntry(${i})"
                class="shrink-0 opacity-0 group-hover:opacity-100 text-xs border border-gray-700 hover:border-orange-500 text-gray-400 hover:text-orange-400 rounded-lg px-2 py-1 transition">
                ▶ Test
            </button>` : ''}
        </div>`).join('');
}

function _at5FireLogEntry(idx) {
    const entry = _at5Log[idx];
    if (!entry || entry.pc === null) return;
    console.log(`[AT5] Manual trigger: ${entry.toneKey} → PC ${entry.pc}`);
    _at5SendPC(entry.pc, entry.ccAdj || []);
}

// ── Live convert ──────────────────────────────────────────────────────────
async function _at5RequestLiveConvert(filename) {
    if (!_at5LiveEnabled || !filename) return;
    // Note: no cache check here — always reconvert so slots stay fresh per song
    _at5LiveLastFile = filename;
    Object.keys(_at5LiveSlots).forEach(k => delete _at5LiveSlots[k]);

    const decodedFilename = decodeURIComponent(filename);
    // Clear stale slots from previous song immediately so they can't fire incorrectly
    Object.keys(_at5LiveSlots).forEach(k => delete _at5LiveSlots[k]);
    console.log(`[AT5 Live] Converting ${decodedFilename}...`);
    try {
        const r = await fetch('/api/plugins/at5_tone/live_convert', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ filename: decodedFilename }),
            signal:  AbortSignal.timeout(15000),
        });
        const data = await r.json();
        if (!r.ok) {
            if (r.status === 503) { _at5LiveEnabled = false; }
            console.warn('[AT5 Live] Error:', data.message);
            return;
        }
        if (data.status === 'ok' && data.slots) {
            // Mutate in place so window._at5LiveSlots reference stays valid
            Object.keys(_at5LiveSlots).forEach(k => delete _at5LiveSlots[k]);
            Object.assign(_at5LiveSlots, data.slots);
            const n = Object.keys(_at5LiveSlots).length;
            console.log(`[AT5 Live] ${n} tones in live slots (${data.elapsed_ms}ms)${data.cached ? ' [cached]' : ''}`);
            if (data.warnings?.length) data.warnings.forEach(w => console.warn('[AT5 Live]', w));
            _at5RenderStatus(); // refresh UI to show live slot status
        }
    } catch(e) {
        console.warn('[AT5 Live] Fetch error:', e.message);
    }
}

// ── Scheduler ──────────────────────────────────────────────────────────────
function _at5StopScheduler() {
    if (_at5Timer) { clearInterval(_at5Timer); _at5Timer = null; }
    _at5Schedule  = [];
    _at5LastFired = -1;
    _at5LastKey   = null;
    _at5LastT     = null;
}

async function _at5StartScheduler(filename) {
    _at5StopScheduler();
    _at5RequestLiveConvert(filename);   // fire & forget — runs in parallel with scheduler startup
    await _at5LoadPcTable();

    // Wait for highway to load song data
    await new Promise(res => setTimeout(res, 800));
    if (_at5Filename !== filename) return;

    // Try highway.getToneChanges() first (CDLC/PSARC: [{t, name}])
    // Retry a few times — highway may not be fully ready at 800ms
    let hwChanges = highway.getToneChanges?.() || [];
    let hwBase    = highway.getToneBase?.() || '';
    if (!hwChanges.length && !hwBase) {
        for (let attempt = 0; attempt < 5; attempt++) {
            await new Promise(r => setTimeout(r, 400));
            hwChanges = highway.getToneChanges?.() || [];
            hwBase    = highway.getToneBase?.() || '';
            if (hwChanges.length || hwBase) break;
        }
    }

    if (hwChanges.length > 0 || hwBase) {
        // CDLC path — enrich with fallback matching for unmapped tones
        _at5Schedule = [];
        if (hwBase) _at5Schedule.push({ key: hwBase, startTime: 0 });
        for (const tc of hwChanges) _at5Schedule.push({ key: tc.name, startTime: tc.t });
        _at5Schedule.sort((a, b) => a.startTime - b.startTime);
        console.log(`[AT5] ${_at5Schedule.length} tone changes (highway) for ${filename}`);

        // Find unmapped tones and fetch CDLC fallback matches
        const unmapped = _at5Schedule.filter(t => !_at5Lookup(t.key)).map(t => t.key);
        if (unmapped.length > 0) {
            try {
                const decoded = decodeURIComponent(filename);
                const r = await fetch('/api/plugins/at5_tone/match-cdlc-tones/' + encodeURIComponent(decoded));
                if (r.ok) {
                    const d = await r.json();
                    // Inject fallback matches into PC table
                    for (const [key, match] of Object.entries(d.matches || {})) {
                        if (!_at5PcTable[key]) {
                            _at5PcTable[key] = {
                                pc:             match.pc,
                                preset_name:    match.preset + ` (${match.match_type})`,
                                cc_adjustments: match.cc_adjustments || [],
                                in_top128:      false,
                                fallback:       true,
                                match_type:     match.match_type,
                            };
                        }
                    }
                    console.log(`[AT5] CDLC fallback: ${Object.keys(d.matches||{}).length} tones matched`);
                }
            } catch (e) {
                console.warn('[AT5] CDLC match fetch failed:', e);
            }
        }
    } else {
        // RS+ scrape path: parse XML schedule
        const tones = await _at5FetchSchedule(filename);
        if (!tones.length) {
            // Last resort: if live slots were converted, use them as a single base tone
            const liveKeys = Object.keys(_at5LiveSlots);
            if (liveKeys.length) {
                console.log(`[AT5] No highway/XML schedule — using ${liveKeys.length} live slot(s) as base tone`);
                _at5Schedule = [{ key: liveKeys[0], startTime: 0 }];
            } else {
                console.log(`[AT5] No tone schedule for ${filename}`);
                return;
            }
        } else {
            _at5Schedule = tones.sort((a, b) => a.startTime - b.startTime);
            console.log(`[AT5] ${_at5Schedule.length} tone changes (XML) for ${filename}`);
        }
    }

    // Fire initial tone
    const first = _at5Schedule[0];
    const entry = _at5Lookup(first.key);
    if (entry) {
        console.log(`[AT5] Initial tone: ${first.key} → PC ${entry.pc}`);
        _at5SendPC(entry.pc, entry.cc_adjustments || []);
        _at5LastFired = 0;
        _at5LastKey   = first.key;
        _at5UpdateBadge(first.key, entry);
        _at5LogTone(first.key, entry, 0);
    }

    // Poll every 100ms
    _at5Timer = setInterval(() => {
        let t;
        try { t = highway.getTime(); } catch { return; }
        if (t == null) return;

        // Seek detection — if time jumped > 2s, rescan from scratch
        if (_at5LastT !== null && Math.abs(t - _at5LastT) > 2.0) {
            console.log(`[AT5] Seek detected (${_at5LastT.toFixed(1)}→${t.toFixed(1)}s) — rescanning`);
            _at5LastFired = -1;
            _at5LastKey   = null;
        }
        _at5LastT = t;

        let idx = -1;
        for (let i = 0; i < _at5Schedule.length; i++) {
            if (_at5Schedule[i].startTime - AT5_PREFIRE_MS <= t) idx = i;
            else break;
        }
        if (idx < 0 || idx === _at5LastFired) return;

        const tone  = _at5Schedule[idx];
        if (tone.key === _at5LastKey) { _at5LastFired = idx; return; }

        const entry2 = _at5Lookup(tone.key);
        _at5LastFired = idx;
        _at5LastKey   = tone.key;

        if (entry2) {
            console.log(`[AT5] t=${t.toFixed(1)}s: ${tone.key} → PC ${entry2.pc}`);
            _at5SendPC(entry2.pc, entry2.cc_adjustments || []);
            _at5UpdateBadge(tone.key, entry2);
        } else {
            console.log(`[AT5] t=${t.toFixed(1)}s: ${tone.key} — not mapped`);
            _at5UpdateBadge(tone.key, null);
        }
        _at5LogTone(tone.key, entry2, t);
    }, 100);
}

async function _at5FetchSchedule(filename) {
    if (!filename) return [];
    try {
        const decoded = decodeURIComponent(filename);
        const songInfo = highway?.getSongInfo?.() || {};
        const arrangement = songInfo.arrangement || '';
        const url = '/api/plugins/at5_tone/song-tone-schedule/' 
            + encodeURIComponent(decoded)
            + (arrangement ? `?arrangement=${encodeURIComponent(arrangement)}` : '');
        const r = await fetch(url);
        if (!r.ok) return [];
        const d = await r.json();
        return (d.tones || []).filter(t => t.key && t.key !== t.toneId);
    } catch { return []; }
}

// ── Badge ──────────────────────────────────────────────────────────────────
function _at5InjectBadge() {
    if (document.getElementById('btn-at5')) return;
    const bar = document.getElementById('player-controls')
        || document.querySelector('[data-player-controls]')
        || document.querySelector('.player-controls');
    if (!bar) return;
    const btn = document.createElement('button');
    btn.id = 'btn-at5';
    btn.className = 'px-3 py-1.5 bg-orange-900/40 hover:bg-orange-900/60 rounded-lg text-xs text-orange-300 transition';
    btn.textContent = 'AT5';
    btn.title = 'AmpliTube 5 Tone Switcher — click to open';
    btn.onclick = () => { if (typeof showScreen === 'function') showScreen('plugin-at5_tone'); };
    const closeBtn = Array.from(bar.querySelectorAll('button')).find(b =>
        b.textContent.includes('Close') || b.textContent.includes('×') || b.title?.includes('Close')
    );
    try {
        if (closeBtn && closeBtn.parentNode === bar) bar.insertBefore(btn, closeBtn);
        else bar.appendChild(btn);
    } catch { bar.appendChild(btn); }
}

function _at5UpdateBadge(toneKey, entry) {
    const btn = document.getElementById('btn-at5');
    if (!btn) return;
    if (entry) {
        btn.textContent = `AT5 #${entry.pc + 1}`;
        btn.title = `${toneKey} → ${entry.preset_name} (PC ${entry.pc}) — click to open`;
        btn.className = 'px-3 py-1.5 bg-orange-900/40 hover:bg-orange-900/60 rounded-lg text-xs text-orange-300 transition';
    } else {
        btn.textContent = 'AT5 ?';
        btn.title = `${toneKey} — not mapped`;
        btn.className = 'px-3 py-1.5 bg-dark-600 rounded-lg text-xs text-gray-500 transition';
    }
}

// ── Status panel ──────────────────────────────────────────────────────────
async function _at5RenderStatus() {
    const el = document.getElementById('at5-midi-status');
    if (!el) return;
    const bridgeUp = await _at5Ping();
    const hasInternal = !!(window.slopsmithDesktop?.audio);
    const pcCount = Object.keys(_at5PcTable).length;
    const savedId = localStorage.getItem('at5_output_id');
    const outputs = [];
    if (_at5MidiAccess) _at5MidiAccess.outputs.forEach(o => outputs.push(o));

    let html = `<div class="bg-dark-700/50 border border-gray-800/50 rounded-xl p-3 space-y-2">`;
    html += bridgeUp
        ? `<div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-green-400 inline-block"></span><span class="text-green-400 text-xs font-semibold">Bridge Ready</span><span class="text-gray-600 text-xs">at5_midi_bridge.py · auto tone switching active</span></div>`
        : `<div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-yellow-500 inline-block"></span><span class="text-yellow-500 text-xs font-semibold">Bridge Offline</span><span class="text-gray-600 text-xs">Run at5_midi_bridge.py --midi-port "AXE IO"</span></div>`;

    if (hasInternal || outputs.length || bridgeUp) {
        html += `<div class="flex items-center gap-3"><span class="text-xs text-gray-500">Output</span>
            <select id="at5-device-select" onchange="localStorage.setItem('at5_output_id',this.value);_at5PickOutput()"
                class="bg-dark-600 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300 outline-none">`;
        if (hasInternal) html += `<option value="internal" ${savedId==='internal'?'selected':''}>Internal VST (Desktop)</option>`;
        if (bridgeUp)    html += `<option value="bridge"   ${savedId==='bridge'||(!hasInternal&&!savedId)?'selected':''}>Bridge → AT5 (Docker)</option>`;
        for (const o of outputs) html += `<option value="${o.id}" ${savedId===o.id?'selected':''}>${esc(o.name)}</option>`;
        html += `</select></div>`;
    }

    html += `<div class="text-xs ${pcCount>0?'text-gray-500':'text-yellow-600'}">PC table: ${pcCount > 0 ? `${pcCount} tones mapped` : 'loading…'}</div>`;
    // Live slot status
    if (_at5LiveEnabled) {
        const liveCount = Object.keys(_at5LiveSlots).length;
        const liveLabel = liveCount > 0
            ? `${liveCount} tones converted (PC ${LIVE_SLOT_START}–${LIVE_SLOT_START+liveCount-1})`
            : (_at5LiveLastFile ? 'converting…' : 'idle — loads on next song');
        html += `<div class="text-xs ${liveCount > 0 ? 'text-green-500' : 'text-gray-500'}">Live slots: ${liveLabel}</div>`;
        if (liveCount > 0) {
            html += `<div class="text-xs text-gray-600 pl-2">` +
                Object.entries(_at5LiveSlots).map(([k,pc]) => `PC${pc}: ${esc(k)}`).join(' · ') +
                `</div>`;
        }
    }
    html += `</div>`;
    el.innerHTML = html;
    document.getElementById('at5-test')?.classList.remove('hidden');
}

// ── Tone browser ───────────────────────────────────────────────────────────
async function at5SearchSongs() {
    const q = document.getElementById('at5-search')?.value.trim();
    if (!q) return;
    const res = await fetch(`/api/songs?q=${encodeURIComponent(q)}&limit=10`)
        .then(r => r.json()).catch(() => ({ songs: [] }));
    const container = document.getElementById('at5-search-results');
    if (!container) return;
    if (!res.songs?.length) {
        container.innerHTML = `<p class="text-sm text-gray-600">No songs found.</p>`; return;
    }
    container.innerHTML = res.songs.map(s => `
        <button onclick="at5BrowseSong(${JSON.stringify(s.filename)}, ${JSON.stringify(s.title||s.filename)}, ${JSON.stringify(s.artist||'')})"
            class="w-full text-left bg-dark-700 hover:bg-dark-600 border border-gray-800 rounded-xl px-4 py-3 transition">
            <span class="text-sm text-white">${esc(s.title||s.filename)}</span>
            <span class="text-xs text-gray-500 ml-2">${esc(s.artist||'')}</span>
        </button>`).join('');
}

async function at5BrowseSong(filename, title, artist) {
    document.getElementById('at5-search-results').innerHTML = '';
    const titleEl = document.getElementById('at5-editor-title');
    if (titleEl) titleEl.textContent = `${artist ? artist + ' — ' : ''}${title}`;
    document.getElementById('at5-editor')?.classList.remove('hidden');

    await _at5LoadPcTable();
    const tones = await _at5FetchSchedule(filename);
    const container = document.getElementById('at5-mappings');
    if (!container) return;

    if (!tones.length) {
        container.innerHTML = `<p class="text-sm text-gray-600 py-3">No tone schedule found — may be a single-tone song, or a CDLC with no explicit tone change events.</p>`;
        return;
    }

    // Deduplicate by key for display, keep timestamps
    const seen = new Set();
    const unique = [];
    for (const t of tones) {
        if (!seen.has(t.key)) { seen.add(t.key); unique.push(t); }
    }

    container.innerHTML = `
        <div class="grid grid-cols-[60px_1fr_80px_100px_80px_60px] gap-x-3 text-xs text-gray-600 font-semibold px-2 mb-1">
            <span>Time</span><span>Tone Key</span><span>Preset</span><span>Name</span><span>Type</span><span></span>
        </div>` +
        tones.map(tone => {
            const entry = _at5Lookup(tone.key);
            const pcNum = entry ? entry.pc + 1 : null;
            const type = !entry ? 'unmapped'
                : entry.in_top128 ? 'direct'
                : entry.cc_adjustments?.length ? 'CC adj'
                : 'template';
            const typeColor = !entry ? 'text-red-500' : entry.in_top128 ? 'text-green-500' : 'text-blue-400';
            return `
            <div class="grid grid-cols-[60px_1fr_80px_100px_80px_60px] gap-x-3 items-center py-2 border-b border-gray-800/40 hover:bg-dark-700/30 px-2 rounded group">
                <span class="text-xs text-gray-600 font-mono">${tone.startTime?.toFixed(1) ?? '0.0'}s</span>
                <span class="text-xs font-semibold text-white truncate">${esc(tone.key)}</span>
                <span class="text-xs text-orange-400 font-mono">${pcNum ? `#${pcNum}` : '—'}</span>
                <span class="text-xs text-gray-500 truncate">${esc(entry?.preset_name ?? '')}</span>
                <span class="text-xs ${typeColor}">${type}</span>
                ${pcNum ? `<button onclick="_at5SendPC(${pcNum-1}, ${JSON.stringify(entry?.cc_adjustments||[])})"
                    class="opacity-0 group-hover:opacity-100 text-xs border border-gray-700 hover:border-orange-500 text-gray-400 hover:text-orange-400 rounded px-2 py-0.5 transition">▶</button>`
                    : `<span></span>`}
            </div>`;
        }).join('');
}

function at5TestSend() {
    const prog = parseInt(document.getElementById('at5-test-prog')?.value) || 0;
    _at5SendPC(prog, []);
}

// ── Tab switcher ───────────────────────────────────────────────────────────
function at5ShowTab(tab) {
    ['status', 'browser', 'log'].forEach(t => {
        document.getElementById(`at5-tab-${t}`)?.classList.toggle('hidden', t !== tab);
        document.getElementById(`at5-tabbtn-${t}`)?.classList.toggle('border-orange-500', t === tab);
        document.getElementById(`at5-tabbtn-${t}`)?.classList.toggle('text-white', t === tab);
        document.getElementById(`at5-tabbtn-${t}`)?.classList.toggle('border-transparent', t !== tab);
        document.getElementById(`at5-tabbtn-${t}`)?.classList.toggle('text-gray-500', t !== tab);
    });
    if (tab === 'log') _at5RefreshLogUI();
    if (tab === 'status') _at5RenderStatus();
}

// ── Init ───────────────────────────────────────────────────────────────────
_at5InitMidi();
_at5Ping();
_at5LoadPcTable();

// Expose globals
window.at5SearchSongs    = at5SearchSongs;
window.at5BrowseSong     = at5BrowseSong;
window.at5TestSend       = at5TestSend;
window.at5ShowTab        = at5ShowTab;
window._at5PickOutput    = _at5PickOutput;
window._at5RenderStatus  = _at5RenderStatus;
window._at5SendPC        = _at5SendPC;
window._at5FireLogEntry  = _at5FireLogEntry;
window._at5Log           = _at5Log;
window._at5SetPrefire    = (v) => { AT5_PREFIRE_MS = parseFloat(v) || 0; };
window._at5LiveSlots     = _at5LiveSlots;
window._at5RequestLiveConvert = _at5RequestLiveConvert;

// Hook showScreen
(function () {
    const orig = window.showScreen;
    if (orig) window.showScreen = function (id) {
        orig(id);
        if (id === 'plugin-at5_tone') {
            _at5RenderStatus();
            _at5RefreshLogUI();
        }
    };
})();

// Stub viz registration (harmless — prevents plugin manager warnings)
window.slopsmithViz_at5tone = { init(){}, draw(){}, destroy(){} };

})();
