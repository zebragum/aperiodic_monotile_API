# Aperiodic Generator — desktop client

Basic Windows app (Tkinter). No installer wizard energy — just a window, fields, Generate.

## Run from source

```powershell
python standalone_gui/untiling_generator.py
```

## Build .exe

```powershell
pip install pyinstaller
powershell -File standalone_gui/build_exe.ps1
```

Output: `standalone_gui/dist/AperiodicGenerator.exe`  
Also copied to `site/assets/downloads/AperiodicGenerator.exe` when that folder exists.

## Defaults

- Depth (`stl_extrusion_mm`) = **0** (flat)
- Formats start with PNG
- Settings saved under `%APPDATA%\Untiling\`
