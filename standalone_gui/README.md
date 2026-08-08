# Aperiodic Generator — desktop client

Simple Windows app. Shape → size → format → **Make it**.

## Run from source

```powershell
python standalone_gui/untiling_generator.py
```

## Build .exe

```powershell
powershell -File standalone_gui/build_exe.ps1
```

Output lands in `standalone_gui/dist/AperiodicGenerator.exe` and
`site/assets/downloads/AperiodicGenerator.exe`.

## Behavior

- Only shows size fields that match the shape (rectangle → width/height; circle → radius; …).
- Thickness is disabled for PNG/JPG/SVG.
- SVG / GLB without a key prompts **Get a key** (Stripe checkout in the browser), then claim/paste.
- Settings save under `%APPDATA%\Untiling\`.
