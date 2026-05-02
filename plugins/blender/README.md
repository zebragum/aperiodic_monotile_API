# Blender Demo Add-on

`aperiodic_monotile_demo.py` is a minimal launch demo for the hosted API.

## What It Does

- Adds a **Monotile API** panel in Blender's 3D View sidebar.
- Lets a user paste an API key.
- Generates a circle, 9:4 rectangle, triangle, or square SVG patch.
- Downloads the SVG from the live API.
- Attempts to import the SVG into Blender if Blender's SVG importer is enabled.

## Install

1. In Blender, open **Edit > Preferences > Add-ons**.
2. Click **Install...**.
3. Select `aperiodic_monotile_demo.py`.
4. Enable **Aperiodic Monotile API Demo**.
5. Open the 3D View sidebar and use the **Monotile API** tab.

## Notes

This is intentionally a demo add-on, not the final paid plugin. The production
plugin should eventually add:

- API key storage via Blender preferences.
- Better progress UI and cancellation.
- JSON/CSV/glTF import paths.
- Tile instancing instead of SVG-only import.
- Material palette controls.
- Direct commercial-tier feature gating.
