#!/usr/bin/env python3
"""Generate the static research wiki under site/research/wiki/."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1] / "site"
WIKI_ROOT = SITE_ROOT / "research" / "wiki"
RESEARCH_ROOT = SITE_ROOT / "research"
TODAY = date.today().isoformat()
BASE = "https://aperiodicgenerator.com/research/wiki"


def link(slug: str, label: str | None = None) -> str:
    text = label or slug.replace("-", " ").title()
    if slug == "index":
        href = "index.html"
    else:
        href = f"{slug}.html"
    return f'<a href="{href}">{html.escape(text)}</a>'


def cite(num: int) -> str:
    return f'<sup class="citation"><a href="bibliography.html#ref-{num}">[{num}]</a></sup>'


ASSET = "../../assets/research/wiki"

FIG_TILE_VARIANTS = f"""
<figure class="wiki-figure">
  <img src="{ASSET}/tilevariants-web.png" alt="Tile(1,1) and Spectre edge variants: straight, jagged, wavy, stepped, scalloped, and rounded silhouettes" width="1100" height="900" loading="lazy" decoding="async" />
  <figcaption>
    <strong>Tile(1,1) / Spectre variants.</strong> One aperiodic monotile footprint with many equivalent edge
    silhouettes — straight polygon, jagged, wavy, stepped, scalloped, and rounded forms. All tile the same
    way; only the boundary decoration changes.
  </figcaption>
</figure>
"""

FIG_TILING_ARRAY = f"""
<figure class="wiki-figure wiki-figure-gif">
  <img src="{ASSET}/tiling-array-zoom.gif" alt="Animated zoom between a dense aperiodic monotile array and a magnified tile view" width="480" height="480" loading="lazy" decoding="async" />
  <figcaption>
    <strong>Tiling array.</strong> A dense Spectre / Tile(1,1) patch oscillates between field scale and
    near-tile magnification — the same array read as texture from afar and as individual tiles up close.
    <a href="{ASSET}/tiling-array-web.jpg">Full resolution still</a>
  </figcaption>
</figure>
"""

FIG_HAT_TILE = f"""
<figure class="wiki-figure">
  <img src="{ASSET}/hat-monotile-commons.png" alt="Hat aperiodic monotile construction from hexagon symmetry lines" width="1100" height="930" loading="lazy" decoding="async" />
  <figcaption>
    <strong>Hat monotile.</strong> The Hat shape and its construction from hexagon symmetry lines.
    Diagram by <a href="https://commons.wikimedia.org/wiki/User:Gringer" rel="noopener noreferrer">Gringer</a>,
    <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener noreferrer">CC BY-SA 4.0</a>;
    based on Smith, Myers, Kaplan &amp; Goodman-Strauss (2023).
  </figcaption>
</figure>
"""

FIG_SPECTRE_PATCH = f"""
<figure class="wiki-figure">
  <img src="{ASSET}/spectre-tiling-commons.jpg" alt="Zoomed aperiodic tiling patch by Tile(1,1) with odd tiles shaded" width="1400" height="1290" loading="lazy" decoding="async" />
  <figcaption>
    <strong>Spectre / Tile(1,1) patch.</strong> A zoomed substitution patch with alternating tile handedness
    highlighted. Sample image from Kaplan et al.,
    <a href="https://cs.uwaterloo.ca/~csk/spectre/" rel="noopener noreferrer">CC BY 4.0</a>.
  </figcaption>
</figure>
"""

@dataclass
class Section:
    heading: str
    level: int
    body: str


@dataclass
class Article:
    slug: str
    title: str
    summary: str
    categories: list[str]
    see_also: list[str] = field(default_factory=list)
    infobox: dict[str, str] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    is_main: bool = False


ARTICLES: list[Article] = [
    Article(
        slug="index",
        title="Main Page",
        summary="The aperiodic monotile research wiki — concepts, mathematics, and application frontiers.",
        categories=["Research"],
        is_main=True,
        sections=[
            Section(
                "Welcome",
                2,
                f"""
<p>
  Welcome to the <strong>Aperiodic Monotile Research Wiki</strong>, a field guide to the geometry,
  mathematics, and emerging applications of aperiodic monotiles — single shapes that tile the plane
  forever without ever repeating.
</p>
<p>
  This wiki is maintained by the team behind
  <a href="../../index.html">Aperiodic Monotile Generator</a>. It distills peer-reviewed literature,
  tooling lineage, and practical workflows into cross-linked articles you can cite, share, and build on.
</p>
{FIG_TILE_VARIANTS}
{FIG_TILING_ARRAY}
""",
            ),
            Section(
                "Featured articles",
                2,
                f"""
<ul class="wiki-feature-list">
  <li>{link("aperiodic-monotile", "Aperiodic monotile")} — the core definition and why it matters</li>
  <li>{link("spectre-tile", "Spectre tile")} — the strictly chiral monotile discovered in 2023</li>
  <li>{link("hat-tile", "Hat tile")} — the first aperiodic monotile, March 2023</li>
  <li>{link("substitution-tiling", "Substitution tiling")} — how finite patches grow into infinite tilings</li>
  <li>{link("moire-and-aliasing", "Moiré and aliasing")} — layered arrays, phason rivers, and moiré navigation</li>
</ul>
""",
            ),
            Section(
                "Browse by category",
                2,
                """
<div class="wiki-category-grid">
  <article>
    <h3>Concepts</h3>
    <ul>
      <li>Aperiodic order, monohedral tilings, chiral vs achiral tiles</li>
    </ul>
  </article>
  <article>
    <h3>Mathematics</h3>
    <ul>
      <li>Spectre, Hat, Tile(1,1), substitution rules, undecidability</li>
    </ul>
  </article>
  <article>
    <h3>Applications</h3>
    <ul>
      <li>Graphics, design, fabrication, education, and research frontiers</li>
    </ul>
  </article>
  <article>
    <h3>References</h3>
    <ul>
      <li>Curated arXiv bibliography with stable citation anchors</li>
    </ul>
  </article>
</div>
""",
            ),
            Section(
                "Application guides",
                2,
                f"""
<ul class="wiki-feature-list">
  <li>{link("computer-graphics", "Computer graphics")}</li>
  <li>{link("design-and-architecture", "Design, art, and architecture")}</li>
  <li>{link("materials-and-fabrication", "Materials and fabrication")}</li>
  <li>{link("education", "Education")}</li>
  <li>{link("signal-processing", "Signal processing and imaging")}</li>
  <li>{link("waves-and-photonics", "Waves, acoustics, and photonics")}</li>
  <li>{link("materials-science", "Materials science and fluids")}</li>
  <li>{link("robotics-and-mobility", "Robotics and mobility")}</li>
  <li>{link("biology-and-medicine", "Biology and medicine")}</li>
  <li>{link("algorithms-and-machine-learning", "Algorithms and machine learning")}</li>
</ul>
""",
            ),
        ],
    ),
    Article(
        slug="aperiodic-monotile",
        title="Aperiodic monotile",
        summary="A single shape that tiles the plane without any repeating translational pattern.",
        categories=["Concepts", "Mathematics"],
        see_also=["spectre-tile", "hat-tile", "substitution-tiling"],
        infobox={
            "Also called": "Einstein problem solution, monotile",
            "Dimension": "Planar (2D)",
            "Key property": "Tiles the plane, never periodically",
            "First example": "Hat tile (2023)",
            "Chiral example": "Spectre tile (2023)",
        },
        sections=[
            Section(
                "Definition",
                2,
                f"""
<p>
  An <strong>aperiodic monotile</strong> is a single closed topological disk in the plane whose congruent copies
  can tile the entire plane, but <em>only</em> in non-periodic arrangements. Unlike Penrose kite-and-dart sets
  or other multi-tile aperiodic systems, a monotile uses one shape — though reflected copies may be required
  depending on the tile's chirality.{cite(1)}{cite(3)}
</p>
<p>
  The long-standing <strong>einstein problem</strong> asked whether such a shape exists. David Smith, Joseph
  Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss answered it in March 2023 with the Hat tile,
  followed months later by the strictly chiral Spectre tile.{cite(1)}
</p>
{FIG_TILE_VARIANTS}
""",
            ),
            Section(
                "Ordered without repeating",
                2,
                """
<p>
  Aperiodic tilings are not random. They are highly structured: every tile sits in a deterministic hierarchy
  produced by substitution rules. Patches can be regenerated from a seed, scaled, and exported with stable
  tile IDs — making them reproducible geometric datasets, not noise.
</p>
<p>
  That combination — global order, local variety, no translational repetition — is what makes monotile
  geometry interesting for graphics, materials, education, and algorithmic research.
</p>
{FIG_TILING_ARRAY}
""",
            ),
            Section(
                "Weak vs strict chirality",
                2,
                f"""
<p>
  The Hat tile is asymmetric: every tiling mixes unreflected and reflected copies. Some authors treat this
  as a two-shape system; standard tiling literature counts reflected congruent copies as the same tile.{cite(1)}
</p>
<p>
  The Spectre tile is a <strong>strictly chiral</strong> aperiodic monotile: it admits only homochiral
  non-periodic tilings, even when reflections are allowed. That distinction matters for physical fabrication
  where mirrored parts are costly or impossible.{cite(1)}{cite(6)}
</p>
""",
            ),
        ],
    ),
    Article(
        slug="spectre-tile",
        title="Spectre tile",
        summary="A strictly chiral aperiodic monotile, also known as Tile(1,1), discovered in 2023.",
        categories=["Mathematics", "Concepts"],
        see_also=["aperiodic-monotile", "hat-tile", "substitution-tiling"],
        infobox={
            "Also known as": "Tile(1,1), Spectre",
            "Announced": "May 2023",
            "Authors": "Smith, Myers, Kaplan, Goodman-Strauss",
            "Chirality": "Strictly chiral",
            "Paper": "arXiv:2305.17743",
        },
        sections=[
            Section(
                "Overview",
                2,
                f"""
<p>
  The <strong>Spectre</strong> is a 13-sided polygon (Tile(1,1)) that tiles the plane aperiodically using
  only orientation-preserving copies — no reflected tiles are needed. It was introduced in
  <em>A chiral aperiodic monotile</em> as the solution to the strictly chiral einstein problem.{cite(1)}
</p>
{FIG_TILE_VARIANTS}
{FIG_SPECTRE_PATCH}
""",
            ),
            Section(
                "Substitution structure",
                2,
                f"""
<p>
  Like other modern aperiodic tiles, Spectre patches are generated by substitution: a finite set of
  metatiles refines into smaller copies until a target region is filled. Public tooling — including Kaplan's
  <a href="https://cs.uwaterloo.ca/~csk/spectre/app.html" rel="noopener noreferrer">Spectre explorer</a>
  and community ports — implements these rules for interactive exploration and export.{cite(1)}
</p>
<p>
  The Aperiodic Monotile Generator API packages this mathematics for production workflows: clipped patches,
  stable tile transforms, and exporters (SVG, STL, GLB, CSV, JSON).
</p>
""",
            ),
            Section(
                "Relationship to the Hat",
                2,
                f"""
<p>
  The Spectre construction refines the Hat discovery by removing the need for mirrored tiles. Researchers
  have also studied conversions between Tile(1,1) tilings and other aperiodic layouts.{cite(7)}
  Kaplan's historical survey traces the full path from Penrose tiles to modern monotiles.{cite(3)}
</p>
""",
            ),
        ],
    ),
    Article(
        slug="hat-tile",
        title="Hat tile",
        summary="The first aperiodic monotile, an asymmetric 13-gon announced in March 2023.",
        categories=["Mathematics", "Concepts"],
        see_also=["aperiodic-monotile", "spectre-tile"],
        infobox={
            "Announced": "March 2023",
            "Authors": "Smith, Myers, Kaplan, Goodman-Strauss",
            "Sides": "13",
            "Reflections": "Required in every tiling",
            "Paper": "arXiv:2303.10798",
        },
        sections=[
            Section(
                "Discovery",
                2,
                f"""
<p>
  The <strong>Hat</strong> is an asymmetric polygon that admits tilings of the plane, but none that are
  periodic. It was the first shape proven to solve the einstein problem — tiling with a single prototile
  subject to standard monohedral definitions that allow reflected copies.{cite(1)}
</p>
{FIG_HAT_TILE}
""",
            ),
            Section(
                "Why reflections matter",
                2,
                f"""
<p>
  Every known Hat tiling mixes unreflected and reflected tiles. Whether that counts as a true monotile
  sparked public debate; the authors and standard references (Grünbaum &amp; Shephard) treat reflected
  congruent copies as the same tile shape.{cite(1)}{cite(3)}
</p>
<p>
  The subsequent Spectre tile answered the stricter question: a shape that tiles aperiodically without
  any reflected copies at all.
</p>
""",
            ),
        ],
    ),
    Article(
        slug="substitution-tiling",
        title="Substitution tiling",
        summary="A hierarchical method that refines metatiles to produce arbitrarily large aperiodic patches.",
        categories=["Mathematics", "Concepts"],
        see_also=["aperiodic-monotile", "spectre-tile"],
        infobox={
            "Used by": "Spectre, Hat, Penrose systems",
            "Output": "Deterministic tile placements",
            "Key idea": "Inflation / deflation rules",
        },
        sections=[
            Section(
                "How substitution works",
                2,
                f"""
<p>
  <strong>Substitution tilings</strong> start from a small set of metatiles and repeatedly replace each
  metatile with a scaled copy of the full set. After finitely many steps, the limit produces an infinite
  tiling whose local structure is hierarchical but never repeats periodically.{cite(3)}
</p>
{FIG_TILING_ARRAY}
""",
            ),
            Section(
                "Practical generation",
                2,
                """
<p>
  For engineering and graphics, substitution is stopped once a patch covers a requested mask (rectangle,
  circle, custom polygon). Each tile receives an ID, transform, and adjacency data — turning abstract
  mathematics into reproducible geometry files.
</p>
""",
            ),
        ],
    ),
    Article(
        slug="moire-and-aliasing",
        title="Moiré and aliasing",
        summary="Layered aperiodic arrays produce moiré landscapes, phason rivers, and a navigable perceived 3D space.",
        categories=["Concepts", "Computer graphics", "Research frontiers"],
        see_also=["computer-graphics", "signal-processing", "aperiodic-monotile"],
        infobox={
            "Core effect": "Beat interference between layered arrays",
            "Controls": "Translation (tx, ty), rotation",
            "Near-alignment": "Rosette cells, depth-like navigation",
            "Large rotation": "Phason rivers (open research)",
            "Regular grids": "High risk of moiré",
        },
        sections=[
            Section(
                "The artifact problem",
                2,
                """
<p>
  Regular grids and repeating textures create moiré interference when sampled, displayed, or printed at
  certain scales. Random noise avoids repetition but sacrifices structure and reproducibility.
</p>
<p>
  Aperiodic monotile patches offer a third family: <strong>ordered but non-repeating</strong> layouts that
  reduce obvious periodic beats while remaining deterministic and seed-stable.
</p>
""",
            ),
            Section(
                "Layered arrays and beat patterns",
                2,
                """
<p>
  Moiré is not only a sampling accident. Take one aperiodic monotile array and <strong>layer a second copy
  on top</strong> — same seed, same tile scale, but offset by a small transform: a translation
  (<em>tx</em>, <em>ty</em>) and/or a rotation θ away from perfect alignment. Where the two structured
  layers agree locally, contrast cancels; where they disagree, macroscopic bright and dark regions appear.
  The result is a <strong>new visual field</strong> that was not present in either layer alone.
</p>
<p>
  Because both layers are aperiodic, the beat pattern does not settle into a simple repeating wallpaper.
  Instead it produces large-scale structures — cells, channels, and gradients — whose topology changes
  smoothly as you adjust the overlay parameters. The same deterministic patch can therefore encode a
  family of related moiré images, all reproducible from the same tile data.
</p>
""",
            ),
            Section(
                "Near-alignment: rosettes and perceived depth",
                3,
                """
<p>
  At very small rotations from pure alignment — on the order of <strong>one degree</strong> — the
  interference often organizes into radial <strong>rosette</strong> or cell-like structures: a bright or
  dark focal center surrounded by lobes that read almost like flowers or lenses. These are not random
  halos; they are the macroscopic signature of microscopic tile disagreement accumulating across the patch.
</p>
<figure class="wiki-figure">
  <img src="../../assets/research/wiki/aperiodicmoire-web.png" alt="Aperiodic moiré at 1° rotation: radial rosette cells emerging from layered monotile arrays" width="1400" height="1400" loading="lazy" decoding="async" />
  <figcaption>
    <strong>1° rotation.</strong> Two aperiodic monotile arrays overlaid with a 1° twist. Near-alignment
    produces large rosette cells with a strong central focal point — a moiré landscape that feels
    dimensional even though it is a flat 2D beat pattern.
    <a href="../../assets/research/wiki/aperiodicmoire.png">Full resolution</a>
  </figcaption>
</figure>
<p>
  Observers often describe this field as a <strong>navigable 3D space</strong>: nudging <em>tx</em> and
  <em>ty</em> pans across the moiré terrain, while small changes in rotation θ act like a zoom or
  dolly — the rosette cells expand, contract, and hand off to neighbors without ever repeating on a
  simple grid. The perceived depth is an optical effect, not true geometry, but it is stable and
  controllable — which makes it interesting for interfaces, data visualization, and spatial encoding.
</p>
""",
            ),
            Section(
                "Phason rivers",
                2,
                """
<p>
  At larger rotation offsets the beat field changes character. For example, at <strong>60°</strong> between
  layers, interference can organize into winding, channel-like structures — <strong>phason rivers</strong>
  — that flow in broad strokes across the patch. In quasicrystal physics, a <em>phason</em> is a type of
  structural rearrangement; here the term is used informally for these moiré channels: coherent pathways
  where the two arrays stay in partial registry over long distances before shearing apart.
</p>
<figure class="wiki-figure">
  <img src="../../assets/research/wiki/aperiodicrivers-web.png" alt="Phason rivers at 60° rotation: winding moiré channels across layered aperiodic arrays" width="1400" height="1400" loading="lazy" decoding="async" />
  <figcaption>
    <strong>60° rotation.</strong> The same layered arrays with a 60° relative twist. Interference
    concentrates into jagged, river-like channels — phason rivers — that cross the field in broad
    horizontal and vertical strokes.
    <a href="../../assets/research/wiki/aperiodicrivers.png">Full resolution</a>
  </figcaption>
</figure>
<p>
  Unlike the near-aligned rosettes, phason rivers are <strong>not intuitive</strong>. Their paths, branch
  points, and sensitivity to tiny parameter changes are not yet well characterized for aperiodic monotile
  arrays. Which rotations produce stable rivers? Do rivers form a navigable network or fragment under
  translation? Can they encode data or serve as routing channels? These questions are <strong>open research
  frontiers</strong> — worthy of systematic study now that monotile patches can be generated and overlaid
  reproducibly.
</p>
""",
            ),
            Section(
                "Navigation as a control space",
                2,
                """
<p>
  Treat the overlay parameters as a three-degree-of-freedom control space:
</p>
<ul>
  <li><strong>tx, ty</strong> — translate the upper layer; the moiré field scrolls, revealing new river
  segments or rosette cells.</li>
  <li><strong>Rotation θ</strong> — twist the upper layer; at small θ the effect reads as zoom or
  magnification through the cell structure; at larger θ the topology shifts toward river networks.</li>
</ul>
<p>
  Because the underlying arrays are deterministic, every position in (<em>tx</em>, <em>ty</em>, θ) maps to
  a unique, reproducible moiré image. That makes the beat field a candidate for <strong>indexed visual
  storage</strong>, generative art, and experimental interfaces where a user explores a perceived 3D
  landscape by steering three continuous parameters.
</p>
""",
            ),
            Section(
                "Where it shows up",
                2,
                f"""
<ul>
  <li>Texture mapping, decals, hatching, and stippling in real-time graphics</li>
  <li>Procedural scatter and environment layout in Blender or game engines</li>
  <li>Print and fabrication pipelines where halftone grids interact with material grain</li>
  <li>Layered aperiodic moiré as a research substrate for phason rivers and spatial encoding</li>
</ul>
<p>See {link("computer-graphics", "Computer graphics")} and {link("signal-processing", "Signal processing and imaging")} for workflow detail.</p>
""",
            ),
        ],
    ),
    Article(
        slug="computer-graphics",
        title="Computer graphics",
        summary="Using aperiodic monotile patches for scenes, textures, meshes, and sampling studies.",
        categories=["Applications"],
        see_also=["moire-and-aliasing", "design-and-architecture"],
        infobox={"Status": "Immediately practical", "Formats": "SVG, GLB, STL, PNG, JSON"},
        sections=[
            Section("Overview", 2, f"""
<p>Replace obvious grid structure with deterministic non-repeating geometry for scenes, masks, meshes,
samplers, and materials. Aperiodic layouts are especially interesting when repetition causes aliasing,
moiré, texture tiling, or visible procedural seams.{cite(4)}{cite(9)}</p>
<ul><li>Procedural worlds and environment scatter</li>
<li>Texture mapping, decals, hatching, stippling, and anti-moiré patterns</li>
<li>Meshes, subdivision experiments, ray/path tracing layouts, and sampling studies</li></ul>
"""),
        ],
    ),
    Article(
        slug="design-and-architecture",
        title="Design, art, and architecture",
        summary="Repeat-free ornamental surfaces, facades, textiles, and spatial studies.",
        categories=["Applications"],
        see_also=["computer-graphics", "materials-and-fabrication"],
        infobox={"Status": "Immediately practical", "Exports": "Vector SVG, fabrication meshes"},
        sections=[
            Section("Overview", 2, f"""
<p>Make surfaces that feel intentional without becoming wallpaper. Designers can fill any region with
geometry that stays coherent across scale, works as a vector asset, and can become a real fabricated object.{cite(1)}{cite(3)}{cite(11)}</p>
<ul><li>Generative sculpture, ornamental tilings, impossible forms, and visual illusions</li>
<li>Facades, screens, ventilation geometry, textiles, inlays, and packaging</li>
<li>Lightweight shells, tensile structures, and spatial studies for built environments</li></ul>
"""),
        ],
    ),
    Article(
        slug="materials-and-fabrication",
        title="Materials and fabrication",
        summary="From relief panels to STL toolpaths — one patch, many physical outputs.",
        categories=["Applications"],
        see_also=["design-and-architecture", "materials-science"],
        infobox={"Exports": "SVG, STL, GLB, CSV, JSON", "Status": "Immediately practical"},
        sections=[
            Section("Overview", 2, f"""
<p>Export the same region as SVG, STL, glTF, CSV, or JSON. One design can become a relief panel, a printed
texture, an instanced mesh, or a dataset of tile transforms.{cite(1)}{cite(6)}{cite(10)}</p>
<ul><li>Toolpath and infill experiments</li>
<li>Support-free printing studies, topology optimization, and surface finishing</li>
<li>Architectural panels, molds, product surfaces, screens, and repeat-free decoration</li></ul>
"""),
        ],
    ),
    Article(
        slug="education",
        title="Education",
        summary="Teaching a fresh mathematical discovery through manipulable patches and physical models.",
        categories=["Applications"],
        see_also=["aperiodic-monotile", "substitution-tiling"],
        infobox={"Audience": "Classrooms, museums, workshops", "Status": "Immediately practical"},
        sections=[
            Section("Overview", 2, f"""
<p>Aperiodic monotiles are a rare chance to teach a fresh mathematical discovery through objects people can
manipulate. Use generated patches for explainers, workshops, classroom demos, and physical models.{cite(1)}{cite(3)}{cite(4)}</p>
<ul><li>Interactive geometry engines</li><li>VR exploration</li>
<li>Posters, exhibits, puzzles, and physical models of abstract spaces</li></ul>
"""),
        ],
    ),
    Article(
        slug="signal-processing",
        title="Signal processing and imaging",
        summary="Deterministic non-periodic sampling layouts for reconstruction and sensor geometry.",
        categories=["Research frontiers"],
        see_also=["moire-and-aliasing", "waves-and-photonics"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section("Overview", 2, f"""
<p>Regular sampling can create artifacts; random sampling can be hard to control. Aperiodic layouts offer
another family of deterministic patterns to test against reconstruction, denoising, compression, and imaging
pipelines.{cite(4)}{cite(2)}</p>
<ul><li>Sampling theory, compression, denoising, and reconstruction</li>
<li>Radar, sonar, MRI, CT, and sensor-array geometry experiments</li>
<li>Comparisons with grids, jittered samples, blue-noise patterns, and quasi-periodic layouts</li></ul>
"""),
        ],
    ),
    Article(
        slug="waves-and-photonics",
        title="Waves, acoustics, and photonics",
        summary="Non-repeating tiled surfaces for scattering, diffraction, and waveguide studies.",
        categories=["Research frontiers"],
        see_also=["materials-science", "signal-processing"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section("Overview", 2, f"""
<p>When waves meet structure, geometry matters. Non-repeating tiled surfaces can become candidate layouts
for scattering, focusing, diffusion, diffraction, beam shaping, and waveguide studies.{cite(2)}{cite(1)}</p>
<ul><li>Acoustic panels, speaker geometry, concert halls, ultrasound focusing, and acoustic lenses</li>
<li>Lens design, diffraction control, waveguides, holography, beam shaping, and photonic layouts</li>
<li>Simulation-ready polygons for comparing periodic, random, and aperiodic boundaries</li></ul>
"""),
        ],
    ),
    Article(
        slug="materials-science",
        title="Materials science and fluids",
        summary="Metamaterials, lattices, electrodes, exchangers, and porous media candidates.",
        categories=["Research frontiers"],
        see_also=["materials-and-fabrication", "waves-and-photonics"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section("Overview", 2, f"""
<p>Engineers often tune performance by changing geometry: pores, channels, lattices, surfaces, electrodes,
exchangers, and support structures. Aperiodic arrays give researchers a new way to produce controlled
non-periodic candidates at many scales.{cite(2)}{cite(5)}{cite(8)}</p>
<ul><li>Metamaterials, auxetic lattices, acoustic cloaking, photonic crystals, and programmable matter</li>
<li>Battery electrodes, fuel cells, solar concentrators, thermal exchangers, and porous media</li>
<li>Drag reduction, turbulence control, microfluidics, blood-flow modeling, and surface textures</li></ul>
"""),
        ],
    ),
    Article(
        slug="robotics-and-mobility",
        title="Robotics and mobility",
        summary="Deterministic test surfaces, navigation substrates, and spatial indexing for experiments.",
        categories=["Research frontiers"],
        see_also=["algorithms-and-machine-learning"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section("Overview", 2, f"""
<p>Robots and vehicles interact with surfaces, fields, and maps. A deterministic aperiodic layout can
become a repeatable test surface, navigation substrate, grasping texture, or spatial index for experiments.{cite(10)}{cite(8)}</p>
<ul><li>Motion planning, terrain navigation, SLAM, geodesics, spherical grids, and drone path planning</li>
<li>Grasping surfaces, soft robotics, deployable structures, tire tread, road surfaces, and rail geometry</li>
<li>Aerodynamic surfaces, heat shields, turbine blades, deployable antennas, and folding structures</li></ul>
"""),
        ],
    ),
    Article(
        slug="biology-and-medicine",
        title="Biology and medicine",
        summary="Geometric scaffolds for packing, growth, folding, and implant design studies.",
        categories=["Research frontiers"],
        see_also=["materials-science"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section("Overview", 2, f"""
<p>Natural systems are full of packing, branching, growth, folding, and surface constraints. Aperiodic
monotile patches are not biological models by default, but they can serve as clean geometric scaffolds
for asking better questions.{cite(2)}{cite(5)}</p>
<ul><li>Morphogenesis, shell growth, protein folding, cellular packing, and neural geometry</li>
<li>Implants, prosthetics, vascular stents, tissue scaffolds, and surgical planning</li>
<li>Crystal structures, catalysts, zeolites, molecular cages, and drug-binding geometry studies</li></ul>
"""),
        ],
    ),
    Article(
        slug="algorithms-and-machine-learning",
        title="Algorithms and machine learning",
        summary="Structured non-repeating benchmark geometry for spatial algorithms and geometric ML.",
        categories=["Research frontiers"],
        see_also=["robotics-and-mobility", "signal-processing"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section("Overview", 2, f"""
<p>Because every patch can be regenerated with stable IDs and transforms, the geometry can become a
benchmark input: structured, non-repeating, and harder to memorize than a regular grid. Cryptographic uses
should be treated as research only unless formally reviewed.{cite(7)}{cite(9)}{cite(11)}</p>
<ul><li>Spatial indexing, nearest-neighbor search, graph embeddings, and geometric hashing</li>
<li>Geometric deep learning, manifolds, latent spaces, equivariant models, and physical-system priors</li>
<li>Lattice-inspired experiments, geometric trapdoors, high-dimensional hardness ideas, and quantum-code layouts</li></ul>
"""),
        ],
    ),
    Article(
        slug="bibliography",
        title="Bibliography",
        summary="Selected references cited across the wiki.",
        categories=["References"],
        see_also=["aperiodic-monotile", "spectre-tile"],
        sections=[
            Section("Selected references", 2, """
<ol class="references-list">
  <li id="ref-1">David Smith, Joseph Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss,
    <a href="https://arxiv.org/abs/2305.17743" rel="noopener noreferrer">A chiral aperiodic monotile</a>.</li>
  <li id="ref-2">Yuto Moritake, Masato Takiguchi, Takuma Aihara, and Masaya Notomi,
    <a href="https://arxiv.org/abs/2506.07561" rel="noopener noreferrer">Chiral Diffraction from Aperiodic Monotile Lattice</a>.</li>
  <li id="ref-3">Craig S. Kaplan,
    <a href="https://arxiv.org/abs/2509.12216" rel="noopener noreferrer">The Path to Aperiodic Monotiles</a>.</li>
  <li id="ref-4"><a href="https://arxiv.org/abs/2603.30006" rel="noopener noreferrer">Enabling fundamental understanding of Nature with novel binning methods for 2D histograms</a>.</li>
  <li id="ref-5">Shigeki Akiyama and Yuto Araki,
    <a href="https://arxiv.org/abs/2506.19362" rel="noopener noreferrer">Sturmian lattices and aperiodic tile sets</a>.</li>
  <li id="ref-6"><a href="https://arxiv.org/abs/2502.15608" rel="noopener noreferrer">Homochiral inflation for the aperiodic monotile Tile(1,1)</a>.</li>
  <li id="ref-7"><a href="https://arxiv.org/abs/2307.08184" rel="noopener noreferrer">Converting non-periodic tilings with Tile(1,1) into tilings with a chiral aperiodic monotile</a>.</li>
  <li id="ref-8"><a href="https://arxiv.org/abs/2504.11710" rel="noopener noreferrer">Tilings from Tops of Overlapping Iterated Function Systems</a>.</li>
  <li id="ref-9"><a href="https://arxiv.org/abs/2603.00911" rel="noopener noreferrer">On the Exact Algorithmic Extraction of Finite Tesselations Through Prime Extraction of Minimal Rectangular Generators</a>.</li>
  <li id="ref-10"><a href="https://arxiv.org/abs/2603.13856" rel="noopener noreferrer">OrigamiBench: An Interactive Environment to Synthesize Flat-Foldable Origamis</a>.</li>
  <li id="ref-11"><a href="https://arxiv.org/abs/2409.15880" rel="noopener noreferrer">Aperiodic monotiles: from geometry to groups</a>.</li>
</ol>
"""),
        ],
    ),
]

NAV_GROUPS = [
    ("Concepts", ["aperiodic-monotile", "moire-and-aliasing"]),
    ("Mathematics", ["spectre-tile", "hat-tile", "substitution-tiling"]),
    ("Applications", [
        "computer-graphics", "design-and-architecture", "materials-and-fabrication", "education",
    ]),
    ("Research frontiers", [
        "signal-processing", "waves-and-photonics", "materials-science",
        "robotics-and-mobility", "biology-and-medicine", "algorithms-and-machine-learning",
    ]),
    ("Meta", ["bibliography"]),
]

ARTICLE_BY_SLUG = {a.slug: a for a in ARTICLES}


def render_nav(current: str) -> str:
    parts = ['<nav class="wiki-nav" aria-label="Wiki navigation">']
    parts.append(f'<p class="wiki-nav-title"><a href="index.html">Wiki</a></p>')
    for group, slugs in NAV_GROUPS:
        parts.append(f'<p class="wiki-nav-group">{html.escape(group)}</p><ul>')
        for slug in slugs:
            article = ARTICLE_BY_SLUG[slug]
            active = ' class="is-active"' if slug == current else ""
            parts.append(f'<li{active}><a href="{slug}.html">{html.escape(article.title)}</a></li>')
        parts.append("</ul>")
    parts.append("</nav>")
    return "\n".join(parts)


def render_toc(sections: list[Section]) -> str:
    items = [s for s in sections if s.level == 2]
    if not items:
        return ""
    lines = ['<nav class="wiki-toc" aria-label="Table of contents">', "<p>Contents</p>", "<ol>"]
    for i, section in enumerate(items):
        sid = f"section-{i}"
        lines.append(f'<li><a href="#{sid}">{html.escape(section.heading)}</a></li>')
    lines.extend(["</ol>", "</nav>"])
    return "\n".join(lines)


def render_infobox(article: Article) -> str:
    if not article.infobox:
        return ""
    rows = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{v}</td></tr>"
        for k, v in article.infobox.items()
    )
    return f"""
<aside class="wiki-infobox" aria-label="Article summary">
  <p class="wiki-infobox-title">{html.escape(article.title)}</p>
  <table>{rows}</table>
</aside>
"""


def render_article_body(article: Article) -> str:
    chunks: list[str] = []
    section_index = 0
    for section in article.sections:
        sid = ""
        if section.level == 2:
            sid = f' id="section-{section_index}"'
            section_index += 1
        tag = f"h{section.level}"
        chunks.append(
            f"<{tag}{sid}>{html.escape(section.heading)}</{tag}>\n{section.body.strip()}"
        )
    if article.see_also:
        links = ", ".join(link(s, ARTICLE_BY_SLUG[s].title) for s in article.see_also if s in ARTICLE_BY_SLUG)
        chunks.append(f'<h2>See also</h2><p>{links}</p>')
    if article.categories:
        cats = " · ".join(
            f'<a href="index.html#category-{html.escape(c.lower().replace(" ", "-"))}">{html.escape(c)}</a>'
            for c in article.categories
        )
        chunks.append(f'<p class="wiki-categories"><strong>Categories:</strong> {cats}</p>')
    return "\n".join(chunks)


def render_page(article: Article) -> str:
    canonical = f"{BASE}/" if article.slug == "index" else f"{BASE}/{article.slug}.html"
    page_title = "Research Wiki" if article.is_main else f"{article.title} | Research Wiki"
    crumbs = '<a href="../index.html">Research</a> · <a href="index.html">Wiki</a>'
    if article.slug != "index":
        crumbs += f' · <span aria-current="page">{html.escape(article.title)}</span>'

    toc = render_toc(article.sections)
    infobox = render_infobox(article) if not article.is_main else ""

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(page_title)} | Aperiodic Monotile Generator</title>
    <meta name="description" content="{html.escape(article.summary)}" />
    <link rel="canonical" href="{canonical}" />
    <meta name="robots" content="index,follow" />
    <link rel="stylesheet" href="../../styles.css" />
    <link rel="stylesheet" href="wiki.css" />
  </head>
  <body class="wiki-body">
    <header class="site-header">
      <a class="brand" href="../../index.html">
        <img class="brand-mark" src="../../assets/brand-mark.svg" alt="" width="32" height="32" decoding="async" />
        <span>Aperiodic Monotile Generator</span>
      </a>
      <nav class="nav" aria-label="Primary navigation">
        <a href="../../index.html">Home</a>
        <a href="../../docs.html">Docs</a>
        <a href="../index.html" aria-current="page">Research</a>
        <a href="index.html">Wiki</a>
      </nav>
      <div class="header-actions">
        <a class="button secondary small" href="../../docs.html#access">Get Access</a>
      </div>
    </header>

    <div class="wiki-toolbar">
      <div class="wiki-toolbar-inner">
        <a href="index.html">Main Page</a>
        <button type="button" class="wiki-random" data-wiki-random>Random article</button>
        <form class="wiki-search-form" role="search" action="index.html" method="get">
          <label class="visually-hidden" for="wiki-search">Search wiki</label>
          <input id="wiki-search" name="q" type="search" placeholder="Search the wiki" autocomplete="off" />
          <button type="submit">Search</button>
        </form>
      </div>
    </div>

    <div class="wiki-shell">
      {render_nav(article.slug)}
      <article class="wiki-article">
        <p class="wiki-breadcrumbs">{crumbs}</p>
        <header class="wiki-header">
          <h1 class="wiki-title">{html.escape(article.title)}</h1>
          <p class="wiki-tagline">{html.escape(article.summary)}</p>
        </header>
        {toc}
        <div class="wiki-content">
          {infobox}
          {render_article_body(article)}
        </div>
        <footer class="wiki-footer-meta">
          <p>Last updated {TODAY}. Content is curated from peer-reviewed sources cited in each article.</p>
        </footer>
      </article>
    </div>

    <footer class="footer">
      <p>
        <a href="../../index.html">Home</a> ·
        <a href="../index.html">Research</a> ·
        <a href="index.html">Wiki</a> ·
        <a href="../../docs.html">Docs</a> ·
        <a href="../../attribution.html">Attribution</a>
      </p>
    </footer>
    <script src="wiki.js" defer></script>
  </body>
</html>
"""


def render_research_hub() -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Research | Aperiodic Monotile Generator</title>
    <meta name="description" content="Research hub for aperiodic monotile papers, datasets, interactive demos, and the field guide wiki." />
    <link rel="canonical" href="https://aperiodicgenerator.com/research/" />
    <link rel="stylesheet" href="../styles.css" />
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="../index.html">
        <img class="brand-mark" src="../assets/brand-mark.svg" alt="" width="32" height="32" decoding="async" />
        <span>Aperiodic Monotile Generator</span>
      </a>
      <nav class="nav" aria-label="Primary navigation">
        <a href="../index.html">Home</a>
        <a href="../docs.html">Docs</a>
        <a href="index.html" aria-current="page">Research</a>
        <a href="wiki/index.html">Wiki</a>
      </nav>
      <div class="header-actions">
        <a class="button secondary small" href="../docs.html#access">Get Access</a>
      </div>
    </header>
    <main>
      <section class="section docs-hero">
        <p class="eyebrow">Research</p>
        <h1>Original work, datasets, and field notes on aperiodic monotiles.</h1>
        <p class="hero-text">
          This hub will host papers, datasets, and interactive research demos. For now, explore the
          <strong>Research Wiki</strong> — a cross-linked field guide to the mathematics and application
          frontiers of aperiodic monotile geometry.
        </p>
        <div class="hero-actions">
          <a class="button" href="wiki/index.html">Open the wiki</a>
          <a class="button secondary" href="../use-cases/applications.html">Legacy field guide</a>
        </div>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">Collections</p>
          <h2>What lives here.</h2>
        </div>
        <div class="domain-catalog">
          <article class="domain-block">
            <h3><a href="wiki/index.html">Wiki</a> <span class="research-badge is-live">Live</span></h3>
            <p>Cross-linked articles on monotile concepts, mathematics, practical applications, and a curated bibliography.</p>
          </article>
          <article class="domain-block is-muted">
            <h3>Original papers <span class="research-badge">Soon</span></h3>
            <p>Preprints and notes produced by the Aperiodic Generator research program.</p>
          </article>
          <article class="domain-block is-muted">
            <h3>Datasets <span class="research-badge">Soon</span></h3>
            <p>Reproducible patch corpora, transform tables, and benchmark masks for experiments.</p>
          </article>
          <article class="domain-block is-muted">
            <h3>Interactive demos <span class="research-badge">Soon</span></h3>
            <p>Browser-native explorations of substitution rules, diffraction, and physical simulations.</p>
          </article>
        </div>
      </section>
    </main>
    <footer class="footer">
      <p><a href="../index.html">Home</a> · <a href="wiki/index.html">Wiki</a> · <a href="../docs.html">Docs</a> · <a href="../attribution.html">Attribution</a></p>
    </footer>
  </body>
</html>
"""


def write_wiki_assets() -> None:
    wiki_js = r"""(() => {
  const indexUrl = "search-index.json";

  async function loadIndex() {
    const res = await fetch(indexUrl);
    if (!res.ok) return [];
    return res.json();
  }

  function pickRandom(items) {
    if (!items.length) return null;
    const pool = items.filter((item) => item.slug !== "index");
    return pool[Math.floor(Math.random() * pool.length)];
  }

  document.querySelector("[data-wiki-random]")?.addEventListener("click", async () => {
    const items = await loadIndex();
    const choice = pickRandom(items);
    if (choice) window.location.href = `${choice.slug}.html`;
  });

  const params = new URLSearchParams(window.location.search);
  const query = (params.get("q") || "").trim().toLowerCase();
  if (!query) return;

  loadIndex().then((items) => {
    const matches = items
      .map((item) => {
        const hay = `${item.title} ${item.summary} ${(item.categories || []).join(" ")}`.toLowerCase();
        const score = hay.includes(query) ? (item.title.toLowerCase().startsWith(query) ? 3 : 1) : 0;
        return { item, score };
      })
      .filter((row) => row.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((row) => row.item);

    const host = document.querySelector(".wiki-content");
    if (!host) return;

    const box = document.createElement("section");
    box.className = "wiki-search-results";
    box.innerHTML = `<h2 id="search-results">Search results for “${query.replace(/"/g, "&quot;")}”</h2>`;
    const list = document.createElement("ul");
    list.className = "wiki-feature-list";

    if (!matches.length) {
      list.innerHTML = "<li>No articles matched. Try a shorter keyword.</li>";
    } else {
      matches.forEach((item) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = `${item.slug}.html`;
        a.textContent = item.title;
        li.appendChild(a);
        const p = document.createElement("p");
        p.textContent = item.summary;
        li.appendChild(p);
        list.appendChild(li);
      });
    }

    box.appendChild(list);
    host.prepend(box);
    document.querySelector(".wiki-title")?.focus?.();
  });
})();
"""
    (WIKI_ROOT / "wiki.js").write_text(wiki_js, encoding="utf-8")

    search_index = [
        {
            "slug": a.slug,
            "title": a.title,
            "summary": a.summary,
            "categories": a.categories,
        }
        for a in ARTICLES
    ]
    (WIKI_ROOT / "search-index.json").write_text(
        json.dumps(search_index, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    WIKI_ROOT.mkdir(parents=True, exist_ok=True)
    RESEARCH_ROOT.mkdir(parents=True, exist_ok=True)

    for article in ARTICLES:
        out = WIKI_ROOT / ("index.html" if article.slug == "index" else f"{article.slug}.html")
        out.write_text(render_page(article), encoding="utf-8")
        print(f"wrote {out.relative_to(SITE_ROOT)}")

    (RESEARCH_ROOT / "index.html").write_text(render_research_hub(), encoding="utf-8")
    print(f"wrote {RESEARCH_ROOT.relative_to(SITE_ROOT)}/index.html")

    write_wiki_assets()
    print("wrote research/wiki assets")


if __name__ == "__main__":
    main()
