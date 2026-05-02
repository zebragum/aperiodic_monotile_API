"""Property-style fuzz smoke for planar affines."""

from hypothesis import assume, given, strategies as st

import numpy as np

from spectre_patch.geometry_affine import compose_world_affine, similarity_client


@given(st.floats(min_value=0.05, max_value=5.0), st.floats(-180, 180), st.floats(-32, 32), st.floats(-32, 32))
def test_compose_finishes(scale, theta, tx, ty):
    rng = np.random.default_rng(0)
    base = rng.normal(size=(6,))
    M = compose_world_affine(
        canonical_gen6=base,
        scale=scale,
        rotation_deg=float(theta),
        tx=float(tx),
        ty=float(ty),
    )
    assume(bool(np.all(np.isfinite(M))))

    Cli = similarity_client(scale, theta, tx, ty)
    assume(bool(np.all(np.isfinite(Cli))))
