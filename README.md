# ClassVision AI — *Visualizing every explanation, live.*

ClassVision AI turns a teacher's explanation into an on-the-spot visual.
**Teach → Trigger → Understand → Visualize.**

It runs next to PowerPoint, captures the visible slide, listens (locally) to the last ~45 seconds of your
explanation, notes where your cursor is, asks a multimodal AI for a **structured diagram spec**, renders it
to SVG **locally**, and shows it in an always-on-top overlay beside your slides.

## Requirements
- Windows 10/11 (macOS/Linux may work for most features but are untested)
- Python 3.11+
- A microphone (optional — **F9 always works without it**)
- Internet + an API key for AI generation (Anthropic Messages API; any image-capable Claude model)

## Install
```bash
git clone <your-repo-url> classvision-ai
cd classvision-ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Edit `.env` (or use **Settings** in the app):
```env
AI_API_KEY=your_api_key_here
AI_MODEL=claude-sonnet-5
WHISPER_MODEL=base
```
Run:
```bash
python app.py
```
The first launch shows a **System Check** telling you exactly what to fix. The first voice session downloads the
Whisper model once (`base` ≈ 150 MB).

## Use it
1. **Start Session** (starts mic + local transcription + the global **F9** hotkey).
2. Open PowerPoint and teach normally.
3. Point at the relevant part of the slide and press **F9** (or say “visualize this”).
4. The overlay appears on the right. Drag its title bar to move, drag the corner to resize,
   **Regenerate** for a clearer alternative (max 5 per capture), ✕ to close.

**No slides handy?** Click **Load Demo Slide** — it shows a client–server slide and pins a sample transcript, then press F9.

Tips: the overlay is a normal always-on-top window. If it hides behind a full-screen slideshow, use
*Slide Show → Set Up Slide Show → Browsed by an individual (window)* or *Reading View*.

## How it works
```
Screen (mss) ─┐
Cursor (pyautogui) ─┼─► Orchestrator ─► Claude (image + transcript text + cursor hint) ─► diagram JSON
Mic ─► faster-whisper (local) ─► 45 s transcript buffer ─┘                                   │
                                                    validate (pydantic, 1 repair retry) ◄────┘
                                                                     ▼
                                              local SVG renderer ─► PySide6 overlay
```
Diagram types: flowchart, process, architecture, timeline, cycle, comparison, hierarchy, concept_map, sequence,
labeled_diagram (unknown types fall back to concept_map). The AI never writes SVG/HTML — only JSON.

## Privacy
- Speech is transcribed **locally**; raw audio is never uploaded or stored.
- Sent to the AI on each request: the slide screenshot, recent transcript **text**, cursor position, instructions.
- Screenshots live in memory only (nothing is written to disk). Logs never contain keys, audio or screenshots.
- The API key is read from `.env` (git-ignored). Never commit it.

## Troubleshooting
| Problem | Fix |
|---|---|
| “Voice recognition unavailable” | Install/enable a microphone; F9 still works. |
| “AI service rejected the API key” | Re-enter the key in Settings. |
| “model not found” | Change **AI model** in Settings. |
| F9 does nothing | Check the log (`logs/classvision.log`); use **Visualize Now** button meanwhile. |
| Screenshot is black | Some protected/full-screen apps block capture; try windowed slideshow. |

## Tests
```bash
pip install pytest
pytest
```
Covers cursor maths, transcript buffer, trigger detection, JSON validation, and SVG rendering for every diagram type.

## Project layout
`app.py` entry · `config/` settings · `core/` session, orchestrator, state · `capture/` screen + cursor ·
`speech/` recorder, transcriber, triggers · `ai/` client, prompts, schema · `diagram/` SVG renderer ·
`ui/` main window, overlay, settings · `utils/` logging, paths, system check.

## Future improvements (not implemented)
Multi-language support · cloud diagram history · lecture history · teacher accounts · student companion app ·
analytics · native PowerPoint plugin · multiple classrooms · enterprise deployment · offline multimodal model ·
automatic slide navigation.
