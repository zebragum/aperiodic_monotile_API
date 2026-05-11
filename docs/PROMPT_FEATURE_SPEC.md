# Natural-language "prompt" parameter — design notes

A user-facing wishlist item: instead of hand-writing the JSON body, let a
caller send a sentence like *"a 1080p horizontal rectangle 200 units wide in
an autumn color palette"* and get a valid `POST /v1/patch` request back. This
document describes how we'd build it without an external LLM bill and without
adding launch-blocking complexity.

## Status

**Not in launch scope.** It is intentionally separated from Tier 1 so launch
risk stays low. The reasoning:

1. A serious natural-language parser implies an LLM dependency. Hosting one on
   Render's standard plan is not realistic; a small model fits a 4 GB image,
   but quality is poor for free-form geometry phrases.
2. Calling out to a hosted LLM (OpenAI, Anthropic, Mistral) means either we
   pay the bill per request or we ask customers to bring their own key. The
   first is hard to price; the second is non-trivial UX.
3. Pragmatically, the JSON body is already short (`mask`, `formats`, raster
   sizes, optional style overrides). Customers willing to read 20 lines of
   docs will be unblocked. The prompt is a delight feature, not a gate.

So this ships post-launch as `POST /v1/prompt/compile`. The endpoint returns a
ready-to-submit `PatchRequest` body, never a job. The caller can then send it
to `POST /v1/patch` exactly as if they had typed it.

## Public API sketch

```
POST /v1/prompt/compile
{
  "prompt": "a 1080p horizontal rectangle 200 units wide in an autumn palette",
  "mode": "deterministic" | "llm"          # default: "deterministic"
}
```

```
200 OK
{
  "request": {                              # ready to feed into POST /v1/patch
    "mask": {"type": "rectangle", "width": 200, "height": 112.5},
    "formats": ["png"],
    "png_width_px": 1920,
    "png_height_px": 1080,
    "svg_deterministic_palette": false,
    "svg_fill": "#d97706"
  },
  "explanation": [
    "Detected raster target '1080p horizontal' -> 1920x1080 PNG.",
    "Detected width '200 units wide' and aspect 'horizontal' -> 200x112.5 rectangle.",
    "Detected palette 'autumn' -> orange fill #d97706."
  ],
  "warnings": [],
  "confidence": 0.91,
  "compile_engine": "deterministic-v1"
}
```

Reasoning included with the response gives customers a chance to spot a
misinterpretation before they spend a paid call generating the patch.

## Engine A — deterministic grammar (ships first, no LLM)

A tiny rule-based extractor catches the 80 % of useful phrases. Lives entirely
on Render in pure Python — zero external calls, no model weights, no licence
surface area. Roughly:

```text
mask              ::= shape size ["centered"]
shape             ::= "rectangle" | "square" | "circle" | "hexagon"
                    | "triangle" | "rounded rectangle"
size              ::= number "unit"s ("wide"|"tall"|"side"|"radius"|"diameter")
                    | aspect ratio "aspect"
aspect ratio      ::= "horizontal" | "vertical" | "square"
                    | "1080p" | "4k" | "social square" | "16:9" | "4:3"
palette           ::= named ("autumn", "ocean", "pastel", "monochrome", ...)
                    | hex code "#rrggbb"
format            ::= "png" | "jpg" | "svg" | "stl_zip" | "obj_zip" | "glb"
```

Rules are encoded as ordered regex matchers in `prompt/deterministic.py`. Each
matcher records what it consumed, returns a partial `PatchRequest`, and the
engine merges with a fixed precedence (`format` highest, `palette` lowest).
Unmatched tokens go into `warnings`. Confidence is a simple coverage ratio:
matched-tokens / non-stopword-tokens.

Failures (no shape detected, no size detected) return `422` with the same
error envelope used everywhere else, including the request id.

Cost: zero external API calls, ~5 ms per request.

## Engine B — BYO-LLM (optional, ships later)

For callers who want freeform language, the request can carry their own
provider key in a header (`X-LLM-Provider: openai`, `X-LLM-Key: sk-...`). The
service constructs a system prompt that includes:

- The current `PatchRequest` schema (as JSON Schema)
- The contents of `prompt/SYSTEM_PROMPT.md` (the "markdown file" workflow you
  mentioned)
- The deterministic engine's output as a starting draft

…and asks the model to produce a strict JSON object matching the schema. The
service validates with Pydantic before returning; failures are retried once
with the validation errors quoted back at the model.

Why BYO key:

- We don't carry an LLM bill or rate-limit per-customer.
- We don't store the customer's key — it's used once per request and never
  persisted.
- It's transparent: customers know exactly which provider they're calling.

Implementation cost is small: a thin httpx call plus a JSON-schema-aware
validator. Most of the work is content in `SYSTEM_PROMPT.md`.

## `prompt/SYSTEM_PROMPT.md`

A single markdown file checked into the repo that describes:

1. What this API does ("Spectre / Tile(1,1) tiling patches with masks and exporters").
2. The exact JSON shape the model must return.
3. Examples (good and bad) — at least one per mask type and one per format.
4. Boundaries the model must respect (no `coverage_half_extent`, no
   `retention`, no mask `center`, mask sizes in canonical units, raster sizes
   in pixels, palette is `svg_fill` plus optional `svg_stroke`).
5. Aliases for shape sizes (e.g., "200 wide" -> `width: 200`).

The file is the source of truth for both engines and the docs site. Updating
the docs and the engine is a single markdown edit.

## What ships before launch

- This document, so the idea is captured.
- A minimal stub endpoint that returns `501 Not Implemented` with a structured
  error pointing at this file. That keeps the URL reserved while making the
  decision visible.

## What ships after launch (when there's customer signal)

- `prompt/SYSTEM_PROMPT.md`
- `prompt/deterministic.py` (Engine A)
- `prompt/byo_llm.py` (Engine B)
- `POST /v1/prompt/compile` wired to both, with `mode` selecting which engine
  runs.
- A "Try a prompt" widget on `docs.html` that previews `request` and
  `explanation` before letting the user submit to `POST /v1/patch`.

## Why not punt it entirely

Even Engine A is useful by itself for design tools (Blender plugin, Figma
plugin, Adobe panel) because the integration code can call `/v1/prompt/compile`
with whatever text the user typed into a search box, then submit the
resulting `request`. That's a real reduction in client-side complexity
without anyone needing to run an LLM.

But none of that is launch-critical. Capture the idea here; build it once one
customer asks for it.
