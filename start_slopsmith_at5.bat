@echo off
title Slopsmith + AT5 Bridge

REM ─────────────────────────────────────────────────────────────────────────
REM  Edit these two paths before running:
REM
REM  SLOPSMITH_DIR  = folder containing your docker-compose.yml
REM  BRIDGE_DIR     = folder containing at5_midi_bridge.py
REM  MIDI_PORT      = exact name of your MIDI output device
REM                   (run: python -c "import rtmidi; print(rtmidi.MidiOut().get_ports())"
REM                    or see README Step 6 for the detection command)
REM ─────────────────────────────────────────────────────────────────────────

set SLOPSMITH_DIR=I:\Docker\slopsmith
set BRIDGE_DIR=I:\Docker\AT5 MIDI Test
set MIDI_PORT=AXE IO

REM ─────────────────────────────────────────────────────────────────────────

echo Starting Slopsmith...
cd /d "%SLOPSMITH_DIR%"
docker compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start Slopsmith. Is Docker running?
    pause
    exit /b 1
)

echo.
echo Starting AT5 MIDI Bridge...
cd /d "%BRIDGE_DIR%"
start "AT5 MIDI Bridge" cmd /k "python at5_midi_bridge.py --midi-port "%MIDI_PORT%""

echo.
echo ─────────────────────────────────────────────────────────────────────────
echo  Slopsmith : http://localhost:8000
echo  AT5 Bridge: http://localhost:37432/ping
echo ─────────────────────────────────────────────────────────────────────────
echo.
echo Open AmpliTube 5, then go to http://localhost:8000 in your browser.
echo.
pause
