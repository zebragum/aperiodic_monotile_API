# Aperiodic Monotile Generator Blender Add-on

This is the first Blender client for the hosted Aperiodic Monotile Generator API.
It lets a Blender user choose generation parameters, submit a GLB job, download
the completed GLB, and import it into the current scene.

## Install

1. Zip the folder `aperiodic_monotile_generator`.
2. In Blender, open `Edit > Preferences > Add-ons`.
3. Click `Install...`.
4. Select the zip file.
5. Enable `Aperiodic Monotile Generator`.

The panel appears in the 3D View sidebar under the `Monotile` tab.

## First test

1. Open the 3D View sidebar with `N`.
2. Open the `Monotile` tab.
3. Paste a paid API key into `API Key`.
4. Choose a boundary:
   - `Rectangle`
   - `Square`
   - `Circle`
   - `Triangle`
   - `Hexagon`
   - `Rounded rectangle`
5. Set tile scale and depth.
6. Click `Generate and Import GLB`.

`Max Wait` is how long Blender should wait for the hosted job to finish before
giving up. If the timeout is reached, the API job may still finish later; this
just prevents Blender from waiting forever.

The add-on will:

1. Call `POST /v1/patch` with `formats: ["glb"]`.
2. Poll `GET /v1/jobs/{job_id}`.
3. Fetch signed URLs from `GET /v1/jobs/{job_id}/urls`.
4. Download `patch.glb`.
5. Import the GLB into Blender.
6. Move imported objects into a collection named `Monotile <job id>`.

## Fill Selected Bounds

Select an object and click `Use Selected Bounds` to copy that object's
world-space X/Y bounding box into the rectangle width and height fields.

This is a first practical approximation of "fill selected shape": it works best
with planes, rectangles, flat meshes, or reference objects whose bounding box is
the intended region. True arbitrary mesh-boundary extraction should be a later
version.

## Material helper

`Randomize Tile Materials` assigns a warm orange/yellow palette to selected mesh
objects. If nothing is selected, it applies to mesh objects in the scene.

## Current limitations

- GLB import is the main supported path.
- Arbitrary selected mesh boundaries are not converted into polygon masks yet.
- The API key is stored in the Blender scene if you save the file. Treat it like
  a credential.
- The operator is synchronous, so Blender may pause while the job is queued,
  generated, downloaded, and imported.

## Future add-on upgrades

- Magic-link or account-based auth instead of pasting API keys.
- True "fill selected shape" from mesh boundary projection.
- Direct SVG/STL/CSV/JSON download options.
- Recolor tiles by embedded tile IDs or tile labels.
- Animation helpers for exploding, drifting, or selecting independent tiles.
