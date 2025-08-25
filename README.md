# GazeDeck

Plane-relative gaze bridge over WebSocket. Emits:
- `fixation.start`, `fixation.progress`, `fixation.end`
- `mark` (confirmed placement)

## Quickstart (Windows PowerShell)

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
gazedeck
```