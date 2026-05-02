# Attribution and licensing

## Mathematical provenance

Tilings are based on Tile(1,1) / **Spectre** theory as presented by Smith, Myers, Kaplan, and Goodman-Strauss, including the paper *A chiral aperiodic monotile* ([arXiv:2305.17743](https://arxiv.org/abs/2305.17743)).

## Reference implementation lineage

The substitution rules and affine placement logic used in `spectre_patch.core.spectre_t11` are derived from publicly shared material:

- Kaplan’s interactive web tooling: [Spectre explorer](https://cs.uwaterloo.ca/~csk/spectre/app.html).
- Widely circulated community ports such as [`shrx/spectre`](https://github.com/shrx/spectre) (Python, noted as ported from Kaplan’s JS).

Separate licenses may apply to each repository; mathematical definitions are reusable, but verbatim code carries the upstream terms. Clients redistributing **SVG meshes** or other derived meshes should cite the paper and tooling lineage appropriate to their jurisdiction and use-case (e.g., academic citations, README credits for assets).

This product emits `patch_version` and optional `generator_commit`/`build` strings so consumers can freeze reproducibility metadata.
