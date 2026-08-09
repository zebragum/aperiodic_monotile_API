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
BASE = "https://untiling.com/research/wiki"


def link(slug: str, label: str | None = None) -> str:
    text = label or slug.replace("-", " ").title()
    if slug == "index":
        href = "index.html"
    else:
        href = f"{slug}.html"
    return f'<a href="{href}">{html.escape(text)}</a>'


def cite(num: int) -> str:
    return f'<sup class="citation"><a href="bibliography.html#ref-{num}">[{num}]</a></sup>'


# --------------------------------------------------------------------------- #
# Bibliography: every paper in the local sources/ corpus, numbering stable.
# --------------------------------------------------------------------------- #

REFERENCES: list[dict] = [
    dict(n=1, authors="David Smith, Joseph Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss",
         title="An aperiodic monotile", arxiv="2303.10798",
         note="The Hat: the first solution to the einstein problem."),
    dict(n=2, authors="David Smith, Joseph Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss",
         title="A chiral aperiodic monotile", arxiv="2305.17743",
         note="Tile(1,1) and the Spectre family: aperiodicity without reflections."),
    dict(n=3, authors="Craig S. Kaplan",
         title="The Path to Aperiodic Monotiles", arxiv="2509.12216",
         note="Historical survey from Penrose kites and darts to the Hat and Spectre."),
    dict(n=4, authors="Shigeki Akiyama and Yoshiaki Araki",
         title="An alternative proof for an aperiodic monotile", arxiv="2307.12322",
         note="Independent aperiodicity proof for the Hat."),
    dict(n=5, authors="Ulrich Reitebuch",
         title="Direct Construction of Aperiodic Tilings with the Hat Monotile", arxiv="2306.06512", note=""),
    dict(n=6, authors="Joshua E. S. Socolar",
         title="Quasicrystalline structure of the Hat monotile tilings", arxiv="2305.01174",
         note="Connects Hat tilings to quasicrystal diffraction structure."),
    dict(n=7, authors="Tinka Bruneau and Michael F. Whittaker",
         title="Planar aperiodic tile sets: from Wang tiles to the Hat and Spectre monotiles",
         arxiv="2310.06759", note=""),
    dict(n=8, authors="James Smith",
         title="Turtles, Hats and Spectres: Aperiodic structures on a Rhombic tiling", arxiv="2403.01911", note=""),
    dict(n=9, authors="Thierry Coulbois, Anahí Gajardo, Pierre Guillon, and Victor Lutfalla",
         title="Aperiodic monotiles: from geometry to groups", arxiv="2409.15880",
         note="Group-theoretic structure behind monotile tilings."),
    dict(n=10, authors="Marianne Imperor-Clerc and Jean-François Sadoc",
         title="Homochiral inflation for the aperiodic monotile Tile(1,1)", arxiv="2502.15608",
         note="Single-handed substitution rules for Tile(1,1)."),
    dict(n=11, authors="Arnaud Chéritat",
         title="Observations on the hex clusters of the Spectre tilings", arxiv="2407.05359",
         note="Cluster structure inside Spectre tilings."),
    dict(n=12, authors="Shiying Dong",
         title="Fibonacci and Lucas Sequences in Aperiodic Monotile Supertiles", arxiv="2404.19621",
         note="Tile counts across substitution generations."),
    dict(n=13, authors="Shigeki Akiyama, Tadahisa Hamada, and Katsuki Ito",
         title="Sturmian lattices and Aperiodic tile sets", arxiv="2506.19362", note=""),
    dict(n=14, authors="Michael F. Barnsley and Corey de Wit",
         title="Tilings from Tops of Overlapping Iterated Function Systems", arxiv="2504.11710", note=""),
    dict(n=15, authors="Teruhisa Sugimoto",
         title="Aperiodic sets of three types of convex polygons", arxiv="2404.00534", note=""),
    dict(n=16, authors="Teruhisa Sugimoto",
         title="Converting non-periodic tilings with Tile(1,1) into tilings with three types of pentagons, I",
         arxiv="2307.08184", note=""),
    dict(n=17, authors="Craig S. Kaplan",
         title="Detecting Isohedral Polyforms with a SAT Solver", arxiv="2406.16407",
         note="Computational search methods for tiling properties."),
    dict(n=18, authors="Sam Coates",
         title="Designing aperiodic to periodic interfaces", arxiv="2404.11378",
         note="How aperiodic and periodic regions can meet in one surface."),
    dict(n=19, authors="Yuto Moritake, Masato Takiguchi, Takuma Aihara, and Masaya Notomi",
         title="Chiral Diffraction from Aperiodic Monotile Lattice", arxiv="2506.07561",
         note="Experimental photonics on a fabricated Spectre lattice."),
    dict(n=20, authors="Justin Schirmann, Selma Franca, Felix Flicker, and Adolfo G. Grushin",
         title="Physical properties of an Aperiodic monotile: Graphene-like features, chirality and zero-modes",
         arxiv="2307.11054",
         note="Electronic and vibrational behavior on the Hat lattice."),
    dict(n=21, authors="Yutaka Okabe, Komajiro Niizeki, and Yoshiaki Araki",
         title="Ising model on the aperiodic Smith hat", arxiv="2402.11331",
         note="Statistical mechanics on the Hat lattice."),
    dict(n=22, authors="Shobhna Singh and Felix Flicker",
         title="Exact Solution to the Quantum and Classical Dimer Models on the Spectre Aperiodic Monotiling",
         arxiv="2309.14447",
         note="Combinatorial physics on Spectre adjacency structure."),
    dict(n=23, authors="Rachel Greenfeld",
         title="Translational tilings: structured or wild?", arxiv="2509.25576", note=""),
    dict(n=24, authors="Chao Yang and Zhujun Zhang",
         title="Undecidability of Translational Tiling with Three Tiles", arxiv="2412.10646",
         note="Fundamental limits of tiling computation."),
    dict(n=25, authors="Sushish Baral, Paulo Garcia, and Warisa Sritriratanarak",
         title="On the Exact Algorithmic Extraction of Finite Tesselations Through Prime Extraction of Minimal Representative Forms",
         arxiv="2603.00911", note=""),
    dict(n=26, authors="Naaisha Agarwal, Yihan Wu, Yichang Jian, Yifei Peng, Yao-Xiang Ding, Nishad Mansoor, Yikuan Hu, Mohan Li, Wang-Zhou Dai, and Emanuele Sansone",
         title="OrigamiBench: An Interactive Environment to Synthesize Flat-Foldable Origamis", arxiv="2603.13856", note=""),
    dict(n=27, authors="I. Vaiman",
         title="Enabling fundamental understanding of Nature with novel binning methods for 2D histograms",
         arxiv="2603.30006",
         note="Non-square binning geometries for data analysis."),
    dict(n=28, authors="Saksham Sharma",
         title="Proof of Aperiodicity of hat tile using the Golden Ratio", arxiv="2403.09640", note=""),
    dict(n=29, authors="Henning U. Voss",
         title="A tiling algorithm for the aperiodic monotile Tile(1,1)", arxiv="2406.05236", note=""),
    dict(n=30, authors="Henning U. Voss and Douglas J. Ballon",
         title="Quasilattices of the Spectre monotile", arxiv="2502.06926", note=""),
    dict(n=31, authors="Michael Baake, Franz Gähler, and Lorenzo Sadun",
         title="Dynamics and topology of the Hat family of tilings", arxiv="2305.05639",
         doi="10.1007/s11856-025-2780-8",
         note="CAP model set, cohomology, and a 4D-to-2D cut-and-project construction."),
    dict(n=32, authors="Michael Baake, Franz Gähler, Jan Mazáč, and Lorenzo Sadun",
         title="On the Long-Range Order of the Spectre Tilings", arxiv="2411.15503",
         doi="10.1007/s00454-025-00756-z",
         note="CASPr model set, Rauzy-fractal windows, and pure-point diffraction."),
    dict(n=33, authors="Craig S. Kaplan, Michael O’Keeffe, and Michael M. J. Treacy",
         title="Periodic diffraction from an aperiodic monohedral tiling",
         doi="10.1107/S2053273323009506",
         note="Hat vertex diffraction on an underlying periodic framework."),
    dict(n=34, authors="Craig S. Kaplan, Michael O’Keeffe, and Michael M. J. Treacy",
         title="Periodic diffraction from an aperiodic monohedral tiling — the Spectre tiling. Addendum",
         doi="10.1107/S2053273324008945",
         note="Spectre diffraction is non-periodic with chiral sixfold point symmetry."),
    dict(n=35, authors="Michael Baake, Franz Gähler, Jan Mazáč, and Andrew J. Mitchell",
         title="Diffraction of the Hat and Spectre tilings and some of their relatives",
         arxiv="2502.03268", doi="10.1063/5.0264955",
         note="Exact Fourier–Bohr amplitudes from CAP and CASPr model sets."),
    dict(n=36, authors="Michael Baake, Franz Gähler, Anna Klick, Neil Mañibo, and Jan Mazáč",
         title="Renormalisation techniques for inflation systems and some of their applications",
         arxiv="2606.19645",
         note="Exact renormalization machinery applied to Hat and Spectre diffraction."),
    dict(n=37, authors="Aurélien Mordret and Adolfo G. Grushin",
         title="Beating the aliasing limit with aperiodic monotile arrays",
         arxiv="2408.16476", doi="10.1103/PhysRevApplied.23.034021",
         note="Hat-family sensor arrays outperform tested periodic and aperiodic baselines."),
    dict(n=38, authors="Yunfei Qiang, Xiaochuan Fang, Rui-Xin Wu, Qian Chen, and Wei Wang",
         title="Application of Aperiodic Einstein Monotile in Phased Arrays With Limited Beam Scanning Range",
         doi="10.1109/OJAP.2024.3499738",
         note="Simulated Hat phased arrays with low grating lobes and 90% aperture efficiency."),
    dict(n=39, authors="Hector Roche Carrasco, Justin Schirmann, Aurélien Mordret, and Adolfo G. Grushin",
         title="A Family of Aperiodic Tilings with Tunable Quantum Geometric Tensor",
         arxiv="2505.13304", doi="10.1103/dzqm-9kwj",
         note="Tile-shape geometry tunes topological phases and quantum metric."),
    dict(n=40, authors="Sergey Alyatkin, Yaroslav V. Kartashov, Kirill Sitnik, Philipp Grigoryev, and Pavlos G. Lagoudakis",
         title="Observation of an aperiodic polariton monotile", arxiv="2605.13206",
         note="Experimental polariton realization with Bragg peaks and long-range coherence."),
    dict(n=41, authors="Valtýr Kári Daníelsson and Helgi Sigurðsson",
         title="Critical states and anomalous wave transport in an aperiodic polariton monotile",
         arxiv="2605.29023",
         note="Predicted critical states and anomalous transport in a Hat optical lattice."),
    dict(n=42, authors="Daniel John Clarke, Francesca Carter, Iestyn Jowers, and Richard James Moat",
         title="An isotropic zero Poisson’s ratio metamaterial based on the aperiodic Hat monotile",
         doi="10.1016/j.apmt.2023.101959",
         note="Experiment and simulation on printed Hat honeycombs."),
    dict(n=43, authors="Romain Rieger and Alexandre Danescu",
         title="Macroscopic elasticity of the hat aperiodic tiling", arxiv="2312.14669",
         doi="10.1016/j.mechmat.2024.104988",
         note="Hat lattice converges toward isotropic continuum elasticity."),
    dict(n=44, authors="Richard J. Moat, Daniel John Clarke, Francesca Carter, Dan Rust, and Iestyn Jowers",
         title="A class of aperiodic honeycombs with tuneable mechanical properties",
         doi="10.1016/j.apmt.2024.102127",
         note="Hat-family geometry independently tunes modulus and Poisson ratio."),
    dict(n=45, authors="Mohamed M. Naji and Rashid K. Abu Al-Rub",
         title="Effective elastic properties of novel aperiodic monotile-based lattice metamaterials",
         doi="10.1016/j.matdes.2024.113102",
         note="Comparative Hat, Turtle, and Spectre lattice mechanics."),
    dict(n=46, authors="Jiyoung Jung, Ailin Chen, and Grace X. Gu",
         title="Aperiodicity is all you need: Aperiodic monotiles for high-performance composites",
         arxiv="2309.05819", doi="10.1016/j.mattod.2023.12.015",
         note="Printed composites outperform tested honeycomb controls in stiffness, strength, and toughness."),
    dict(n=47, authors="Jiyoung Jung, Kundo Park, and Grace X. Gu",
         title="Exploring the mechanical properties of aperiodic monotile composite family through Gaussian process regression",
         doi="10.1016/j.eml.2025.102370", note=""),
    dict(n=48, authors="Jiyoung Jung, Kundo Park, and Grace X. Gu",
         title="Strength through curvature: Engineering multi-phase materials based on chiral aperiodic monotile patterns",
         doi="10.1016/j.compstruct.2025.119131", note=""),
    dict(n=49, authors="Hongru Zhang, Yuanpeng Liu, Jiaming Ma, Ngoc San Ha, and Yi Min Xie",
         title="High-performance composites with bio-inspired interlocking aperiodic monotiles",
         doi="10.1016/j.compositesb.2026.113562",
         note="Experimental interlocking composite with twentyfold fracture-resistance gain over honeycomb."),
    dict(n=50, authors="Reymond Akpanya, Tom Frederik Görtzen, Yuanpeng Liu, Sascha Stüttgen, Daniel Robertz, Yi Min Xie, and Alice Catherine Niemeyer",
         title="Constructing Topological Interlocking Assemblies Based on an Aperiodic Monotile",
         url="https://publications.rwth-aachen.de/record/1006945",
         note="Three-dimensional identical blocks constrained to aperiodic interlocking assemblies."),
    dict(n=51, authors="Hugo Hiu Chak Cheng and Gary P. T. Choi",
         title="Monotile kirigami", arxiv="2604.19586",
         note="Deployable periodic and aperiodic monotile kirigami constructions."),
    dict(n=52, authors="Haitao Gao and Aaryash Bharadwaj",
         title="Percolation Critical Probability of Aperiodic Smith Hat Tile(1,√3)",
         arxiv="2604.21165", note="Monte Carlo site and bond percolation thresholds."),
    dict(n=53, authors="Sébastien Labbé and Peter Selinger",
         title="A construction of the hat tilings by a Markov partition", arxiv="2604.20964",
         note="Explicit torus Markov partition with fractal boundaries."),
    dict(n=54, authors="Arnaud Chéritat and Nan Ma",
         title="4D lift of the tilings by the Smith et al. aperiodic monotile",
         url="https://www.math.univ-toulouse.fr/~cheritat/2023-monotile/4D-lift/",
         note="Nan Ma’s coherent R⁴ edge lift, exposition and interactive projections."),
    dict(n=55, authors="Josep Batle and Adam Bednorz",
         title="Quantum error-correcting codes from aperiodic monotiles: the Hat and the Spectre",
         arxiv="2607.15326",
         note="Li–Boyle QECCs extended to Hat and Spectre; local recoverability and SE(2) classical-bit storage."),
    dict(n=56, authors="Rachel Greenfeld and Terence Tao",
         title="Undecidability of translational monotilings",
         doi="10.4171/jems/1673",
         note="Algorithmic undecidability of translational monotiles in ℤᵈ for d≥3."),
    dict(n=57, authors="Teruhisa Sugimoto",
         title="Converting non-periodic tilings with Tile(1, 1) into tilings with three types of pentagons, II",
         url="https://jxiv.jst.go.jp/index.php/jxiv/preprint/view/1282",
         note="Part II: Tile(1,1) to three-pentagon tilings after rhombus subdivision."),
    dict(n=58, authors="Chao Yang and Zhujun Zhang",
         title="Translational Aperiodic Sets of 7 Polyominoes",
         arxiv="2412.17382",
         note="Smallest known translational aperiodic polyomino set; cites Hat discovery."),
    dict(n=59, authors="Chao Yang and Zhujun Zhang",
         title="On the Undecidability of Tiling the 3-dimensional Space with a Set of 3 Polycubes",
         arxiv="2508.00192",
         note="Translational undecidability in 3D with only three polycubes."),
    dict(n=60, authors="Stephen Daynes",
         title="Mechanical behaviour of aperiodic monotile minimal surface metamaterials",
         doi="10.1016/j.tws.2026.114788",
         note="TPMS cells on Hat, Turtle, and Spectre lattices; stiffness–density trade-offs."),
    dict(n=61, authors="Sankarganesh P., Vinothkumar G., and P. G. Kubendran Amos",
         title="Evolving Einstein: The instability of aperiodic monotile as a polycrystalline microstructure",
         doi="10.1016/j.mtla.2025.102517",
         note="Phase-field polycrystalline evolution on Hat-family lattice topology."),
    dict(n=62, authors="Amin Montazeri, Mohammad Reza Ghaffari, and co-authors",
         title="Aperiodic ordered lattices with semi Re-entrant einstein monotile",
         doi="10.1016/j.euromechsol.2025.105830",
         note="Re-entrant lattice inspired by einstein geometry; band-gap FEA (not Smith tile shape)."),
    dict(n=63, authors="Sidney Holden and Geoffrey Vasil",
         title="A continuum limit for dense spatial networks",
         arxiv="2301.07086",
         note="Homogenization framework with Hat monotile as a convergence example."),
    dict(n=64, authors="Yuanpeng Liu, Jiaming Ma, and co-authors",
         title="Aperiodic-unit-cell microlattices",
         doi="10.1002/smll.202307369",
         note="Einstein-inspired 3D microlattices; progressive collapse vs honeycomb (geometry-inspired)."),
    dict(n=65, authors="Yuanpeng Liu and co-authors",
         title="Aperiodic interpenetrating-phase composites",
         doi="10.1002/adfm.202406890",
         note="3D-printed monotile-inspired Ti–epoxy lattice; high specific energy absorption."),
    dict(n=66, authors="Iestyn Jowers and Richard J. Moat",
         title="What Lies Beneath a Family of Aperiodic Monotilings",
         url="https://archive.bridgesmathart.org/2025/bridges2025-169.html",
         note="Bridges 2025: vertex arrangements and subsidiary polygon systems in the Hat family."),
    dict(n=67, authors="David Richeson",
         title="Fold-and-Cut Lines for the Hat, Turtle, and Spectre Tiles",
         url="https://archive.bridgesmathart.org/2025/bridges2025-567.html",
         note="Bridges 2025: one-cut paper construction crease patterns."),
    dict(n=68, authors="Hanan Keren, Shlomi Levi, and Alon Leib",
         title="Aperiodic Monotile Phased Array Antenna and System with No Grating Lobes",
         url="https://patents.google.com/patent/US20240396208A1/en",
         note="US patent application: Hat polykite phased-array geometry (proposal, not lab validation)."),
    dict(n=69, authors="Vincent van Dongen",
         title="Lifted Aperiodic Hat and Turtle",
         url="https://hal.science/hal-04090715",
         note="3D polyhedral wall modules from Hat/Turtle outlines (architectural lift, not Ma’s ℝ⁴ lift)."),
    dict(n=70, authors="Shobhna Singh",
         title="Constrained models in aperiodic systems",
         url="https://orca.cardiff.ac.uk/id/eprint/181483/",
         note="Cardiff PhD thesis: Spectre dimer models, optimization, and quasicrystalline graphs."),
    dict(n=71, authors="Miki Imura",
         title="A Family of Non-Periodic Tilings, Describable Using Elementary Tools and Exhibiting a New Kind of Structural Regularity",
         arxiv="2506.07638",
         note="Modulo Krinkle monohedral tiles: elementary non-periodic (often spiral) tilings; not an einstein."),
]

WEB_RESOURCES = [
    dict(label="Kaplan et al., <em>An aperiodic monotile</em> project page — interactive patch builders, source code, and CC&nbsp;BY sample images",
         url="https://cs.uwaterloo.ca/~csk/hat/"),
    dict(label="Kaplan et al., <em>A chiral aperiodic monotile</em> project page — Tile(1,1) patch app and Spectre SVG outlines for cutting and printing",
         url="https://cs.uwaterloo.ca/~csk/spectre/"),
    dict(label="christianp/aperiodic-monotile — OpenSCAD, STL, and SVG files for fabricating Hat, Turtle, and Spectre tiles",
         url="https://github.com/christianp/aperiodic-monotile"),
    dict(label="Printables: Spectre chiral aperiodic monotile — parametric 3D-printable tiles with this-way-up orientation grids",
         url="https://www.printables.com/model/520972-spectre-chiral-aperiodic-monotile"),
    dict(label="National Museum of Mathematics: The Hat and the Spectre — exhibits and the Einstein Mad Hat competition",
         url="https://momath.org/the-hat/"),
    dict(label="Nan Ma, aperiodic-monotile-4d — original Wolfram Language code and projection experiments (no license; link only)",
         url="https://github.com/nanma80/aperiodic-monotile-4d"),
    dict(label="Arnaud Chéritat and Nan Ma, interactive 4D projection applet — CC BY-SA",
         url="https://www.math.univ-toulouse.fr/~cheritat/AppletsDivers/Monotile-4D-lift/3-outlines/"),
    dict(label="Simon Tatham, Combinatorial Coordinates for the Aperiodic Spectre Tiling",
         url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-spectre/"),
    dict(label="Christian Lawson-Perfect et al., multi-format monotile assets — CC0 SVG, DXF, OpenSCAD, and STL",
         url="https://github.com/christianp/aperiodic-monotile"),
    dict(label="Infinite Spectres — MIT-licensed Rust/WebGPU deep-zoom viewer",
         url="https://github.com/necocen/spectre"),
    dict(label="Tilings Encyclopedia: Spectre — institutional patch and reference record",
         url="https://tilings.math.uni-bielefeld.de/substitution/spectre/"),
    dict(label="Large Spectre Tiling — 488-piece hierarchical group activity",
         url="https://www.gathering4gardner.org/large-spectre-tiling/"),
    dict(label="Terracing with Spectres — built CNC-waterjet limestone terrace and process archive",
         url="https://anarchive.fo.am/silver/spectres/"),
    dict(label="Hats in Grout — practical fabrication and installation geometry",
         url="https://archive.bridgesmathart.org/2024/bridges2024-389.html"),
    dict(label="OEIS A363348 — recursive turn sequence for drawing an infinite Hat tiling",
         url="https://oeis.org/A363348"),
]

WEB_RESOURCE_SECTIONS: list[tuple[str, list[dict]]] = [
    ("Official project pages and discoverer accounts", [
        dict(label="Kaplan, <em>Aperiodic Monotiles</em> — discovery chronology and community links",
             url="https://isohedral.ca/aperiodic-monotiles/"),
        dict(label="David Smith, Hedraweb — discoverer blog and physical experiments",
             url="https://hedraweb.blogspot.com/"),
        dict(label="David Smith, <em>The Special One</em> — first-person Tile(1,1) / Spectre story",
             url="https://hedraweb.wordpress.com/2023/06/02/the-special-one/"),
        dict(label="Joseph Myers — publications and preprints",
             url="https://www.polyomino.org.uk/publications/"),
        dict(label="Chaim Goodman-Strauss — papers and notes",
             url="https://chaimgoodmanstrauss.com/papers/"),
        dict(label="Combinatorial Theory — Hat paper (open access)",
             url="https://doi.org/10.5070/c64163843"),
        dict(label="Combinatorial Theory — Spectre paper (open access)",
             url="https://doi.org/10.5070/c64264241"),
    ]),
    ("Generators, code, and datasets", [
        dict(label="isohedral/hatviz — official Hat patch builder (BSD-3-Clause)",
             url="https://github.com/isohedral/hatviz"),
        dict(label="isohedral/hatvalidate — computer-assisted aperiodicity verification",
             url="https://github.com/isohedral/hatvalidate"),
        dict(label="henningle/TileOneOne — reference Tile(1,1) MATLAB generator (MIT)",
             url="https://github.com/henningle/TileOneOne"),
        dict(label="jsm28/AperiodicMonotilesLean — Lean formalization staging repo",
             url="https://github.com/jsm28/AperiodicMonotilesLean"),
        dict(label="reversi-fun/symbolic-spectre-tiles — symbolic coordinates and CSV/SVG export (MPL-2.0)",
             url="https://github.com/reversi-fun/symbolic-spectre-tiles"),
        dict(label="ctkrug/monotile — infinite Spectre pan/zoom studio",
             url="https://apps.charliekrug.com/monotile/"),
        dict(label="Ricky Reusser — WebGPU aperiodic monotile rendering notebook",
             url="https://rreusser.github.io/notebooks/aperiodic-monotile/"),
        dict(label="Ricky Reusser — deep-zoom aperiodic monotile notebook",
             url="https://rreusser.github.io/notebooks/zooming-aperiodic-monotile/"),
        dict(label="James Smith — AperiodicCube 3D interactive demo",
             url="https://jpdsmith.github.io/AperiodicCube/"),
        dict(label="Simon Tatham — coordinate algorithms for Hat tilings",
             url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-tilings/"),
        dict(label="Simon Tatham — finite-state transducers for Hat and Spectre",
             url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-transducers/"),
        dict(label="Simon Tatham — refinable frontier (H7/H8 and Spectre hex types)",
             url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-refine/"),
        dict(label="Jaap Scherphuis — PolyForm Puzzle Solver (discovery-era search tool)",
             url="https://www.jaapsch.net/puzzles/polysolver.htm"),
        dict(label="Spectre Tiling Playground — manual editor with TILE coordinate format",
             url="https://bnaskrecki.faculty.wmi.amu.edu.pl/spectre/"),
        dict(label="Beach Spectre Practise — touch-friendly substitution trainer",
             url="https://beach-spectre-practise.think.somethingorotherwhatever.com/"),
    ]),
    ("Institutional references and OEIS", [
        dict(label="Tilings Encyclopedia — Hat substitution record",
             url="https://tilings.math.uni-bielefeld.de/substitution/hat/"),
        dict(label="Tilings Encyclopedia — CAP representative",
             url="https://tilings.math.uni-bielefeld.de/substitution/cap/"),
        dict(label="Tilings Encyclopedia — aperiodic monotile glossary",
             url="https://tilings.math.uni-bielefeld.de/glossary/aperiodic-monotile/"),
        dict(label="OEIS A363445 — Hat perimeter fractal turn sequence",
             url="https://oeis.org/A363445"),
        dict(label="OEIS A397115–A397123 — Spectre hierarchical cluster counts (2026)",
             url="https://oeis.org/A397115"),
    ]),
    ("Museums, competitions, and workshops", [
        dict(label="UKMT Einstein Mad Hat Awards — competition archive",
             url="https://ukmt.org.uk/hat-awards"),
        dict(label="Hatfest — Oxford / Grimm Network conference archive",
             url="https://sites.google.com/view/thegrimmnetwork/hatfest"),
        dict(label="Cambridge Faculty of Mathematics — Tip of the Hat celebration",
             url="https://www.maths.cam.ac.uk/features/tip-hat-celebrating-aperiodic-monotile-discovery"),
        dict(label="Marcello Seri — Spectres, Hats and Maths workshop kits (CC BY 4.0)",
             url="https://academic.mseri.me/pe.htm"),
        dict(label="Bridges 2024 — Group activity to build a Spectre tiling",
             url="https://archive.bridgesmathart.org/2024/bridges2024-385.html"),
        dict(label="Numberphile — Discovery of the Aperiodic Monotile",
             url="https://www.youtube.com/watch?v=_ZS3Oqg1AX0"),
        dict(label="Quanta — Hobbyist finds maths elusive Einstein tile",
             url="https://www.quantamagazine.org/hobbyist-finds-maths-elusive-einstein-tile-20230404/"),
    ]),
    ("Fabrication, installations, and products", [
        dict(label="Beach Spectres — public sand-tiling project and how-to guides",
             url="https://beachspectres.com/"),
        dict(label="Printables — Einstein Tiles family (Hat, Tile(1,1), Spectre variants)",
             url="https://www.printables.com/model/574374-einstein-tiles-original-and-chiral"),
        dict(label="Spirko/SpectreOpenSCAD — parametric Spectre STL generator (GPL-3.0)",
             url="https://github.com/Spirko/SpectreOpenSCAD"),
        dict(label="vmagnin/hat_polykite — laser-cut Hat and Tile(1,1) sheets",
             url="https://github.com/vmagnin/hat_polykite"),
        dict(label="Nervous System — wooden Spectre puzzle (111 pieces)",
             url="https://n-e-r-v-o-u-s.com/shop/product.php?code=409"),
    ]),
]


def render_web_resources_html(*, compact: bool = False) -> str:
    parts: list[str] = []
    for heading, items in WEB_RESOURCE_SECTIONS:
        level = 3 if compact else 2
        parts.append(f'<h{level}>{html.escape(heading)}</h{level}>')
        parts.append('<ul class="references-list references-web">')
        for item in items:
            parts.append(
                f'<li><a href="{item["url"]}" rel="noopener noreferrer">{item["label"]}</a></li>'
            )
        parts.append("</ul>")
    parts.append(
        '<h3>Curated quick links</h3>'
        if compact
        else '<h2 id="section-quick">Curated quick links</h2>'
    )
    parts.append('<ul class="references-list references-web">')
    for item in WEB_RESOURCES:
        parts.append(
            f'<li><a href="{item["url"]}" rel="noopener noreferrer">{item["label"]}</a></li>'
        )
    parts.append("</ul>")
    return "".join(parts)


def render_references_html() -> str:
    items = []
    for r in REFERENCES:
        authors = f"{html.escape(r['authors'])}, " if r["authors"] else ""
        note = f' <span class="ref-note">— {html.escape(r["note"])}</span>' if r["note"] else ""
        href = (
            f"https://doi.org/{r['doi']}" if r.get("doi")
            else f"https://arxiv.org/abs/{r['arxiv']}" if r.get("arxiv")
            else r.get("url", "#")
        )
        identifier = (
            f" DOI:{r['doi']}." if r.get("doi")
            else f" arXiv:{r['arxiv']}." if r.get("arxiv")
            else ""
        )
        items.append(
            f'<li id="ref-{r["n"]}">{authors}'
            f'<a href="{href}" rel="noopener noreferrer">{html.escape(r["title"])}</a>.'
            f'{identifier}{note}</li>'
        )
    return (
        '<ol class="references-list">' + "".join(items) + "</ol>"
        + render_web_resources_html()
    )


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #

ASSET = "../../assets/research/wiki"


def fig(asset: str, alt: str, caption: str, *, width: int | None = None, extra_class: str = "") -> str:
    klass = "wiki-figure"
    if extra_class:
        klass += f" {extra_class}"
    width_attr = f' width="{width}"' if width else ""
    return f"""
<figure class="{klass}">
  <img src="{ASSET}/{html.escape(asset)}" alt="{html.escape(alt)}"{width_attr} loading="lazy" decoding="async" />
  <figcaption>{caption}</figcaption>
</figure>
"""


def fig_thumb(
    asset: str,
    alt: str,
    caption: str,
    *,
    width: int | None = None,
    side: str = "left",
    size: str = "",
) -> str:
    """Wikipedia-style floating thumbnail (text wraps around it)."""

    classes = [f"wiki-figure-float-{side}"]
    if size:
        classes.append(f"wiki-figure-{size}")
    return fig(asset, alt, caption, width=width, extra_class=" ".join(classes))


def fig_video(asset: str, caption: str, *, poster: str | None = None, extra_class: str = "") -> str:
    klass = "wiki-figure wiki-figure-video"
    if extra_class:
        klass += f" {extra_class}"
    poster_attr = f' poster="{ASSET}/{poster}"' if poster else ""
    return f"""
<figure class="{klass}">
  <video autoplay loop muted playsinline{poster_attr} aria-label="{html.escape(caption)}">
    <source src="{ASSET}/{html.escape(asset)}" type="video/mp4" />
  </video>
  <figcaption>{caption}</figcaption>
</figure>
"""


FIG_TILE_VARIANTS = fig(
    "tilevariants-web.png",
    "Tile(1,1) and Spectre edge variants: straight, jagged, wavy, stepped, scalloped, and rounded silhouettes",
    "<strong>Tile(1,1) / Spectre variants.</strong> One aperiodic monotile footprint with many equivalent edge "
    "silhouettes — straight polygon, jagged, wavy, stepped, scalloped, and rounded forms. All tile the same "
    "way; only the boundary decoration changes.",
    width=1100,
)
FIG_MIKI_IMURA = fig_thumb(
    "miki-imura-modulo-krinkle.png",
    "Miki Imura Modulo Krinkle monotile: equilateral polygon with zig-zag sides and labeled angles",
    "<strong>Miki Imura monotile</strong> (Modulo Krinkle). An equilateral monohedral tile that can assemble "
    "into striking non-periodic patterns (often spirals). Unlike Hat / Spectre, it also admits periodic "
    "tilings, so it is not an aperiodic monotile in the einstein sense.",
    width=220,
    side="left",
    size="sm",
)
FIG_TILING_ARRAY = fig_video(
    "tiling-array-zoom.mp4",
    "<strong>Tiling array.</strong> A steady camera zoom into a dense Spectre / Tile(1,1) field and back out "
    "— the same real generated patch read as texture at a distance and as individual tiles up close. "
    f'<a href="{ASSET}/tiling-array-web.jpg">Full-resolution still</a>',
)
FIG_HIERARCHY = fig_video(
    "substitution-hierarchy.mp4",
    "<strong>The substitution hierarchy, animated.</strong> One Tile(1,1) grows into a cluster, then a "
    "supercluster, following the real substitution rules. Colors mark which first-generation cluster each "
    "tile belongs to, so the hierarchy stays visible as the patch expands. "
    f'<a href="{ASSET}/substitution-hierarchy-still.png">Supercluster still</a>',
)
FIG_HAT_TILE = fig(
    "hat-monotile-commons.png",
    "Hat aperiodic monotile construction from hexagon symmetry lines",
    "<strong>Hat monotile.</strong> The Hat shape and its construction from hexagon symmetry lines. "
    'Diagram by <a href="https://commons.wikimedia.org/wiki/User:Gringer" rel="noopener noreferrer">Gringer</a>, '
    '<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener noreferrer">CC BY-SA 4.0</a>; '
    "based on Smith, Myers, Kaplan &amp; Goodman-Strauss (2023).",
    width=1100,
)
FIG_SPECTRE_PATCH = fig(
    "spectre-tiling-commons.jpg",
    "Zoomed aperiodic tiling patch by Tile(1,1) with odd tiles shaded",
    "<strong>Spectre / Tile(1,1) patch.</strong> A zoomed substitution patch with alternating tile handedness "
    "highlighted. Sample image from Kaplan et al., "
    '<a href="https://cs.uwaterloo.ca/~csk/spectre/" rel="noopener noreferrer">CC BY 4.0</a>.',
    width=1400,
)
FIG_SPLIT = fig(
    "periodic-vs-aperiodic.jpg",
    "Split render: periodic hexagon floor on the left, aperiodic Spectre tile floor on the right, same glazed ceramic material",
    "<strong>Periodic vs aperiodic.</strong> Same glazed ceramic, same light, one seam. The hexagonal grid "
    "(left) repeats identically in every direction; the Spectre floor (right) is equally ordered but never "
    "repeats — every neighborhood is unique. Both are real geometry: an equal-area hex grid and a generated "
    "Tile(1,1) patch.",
    width=2048,
)
FIG_CG_SUNSET = fig(
    "computer-graphics-sunset.jpg",
    "Aperiodic monotile floor at sunset with terracotta tones stretching to the horizon",
    "<strong>Environmental scatter.</strong> Eye-height procedural ground plane — aperiodic monotile "
    "instances with warm PBR materials, useful for scenes that need ordered but non-repeating structure.",
    width=1400,
)
FIG_CG_BRASS = fig(
    "computer-graphics-brass.jpg",
    "Brass aperiodic monotile relief panel with beveled edges and dramatic lighting",
    "<strong>Material and lighting study.</strong> Instanced monotile meshes with metallic shading — "
    "the same patch data drives real-time previews, offline renders, and exported GLB assets.",
    width=1400,
)
FIG_ZELLIGE_EMERALD = fig(
    "design-zellige-emerald.jpg",
    "Emerald glazed ceramic Spectre tiles with handmade zellige-style glinting",
    "<strong>Glazed ceramic feature wall.</strong> Every Spectre tile is a physical chip with thickness, "
    "grout, and a slight random tilt, so the glaze glints tile-by-tile like handmade zellige. Rendered in "
    "Cycles from a generated Tile(1,1) patch.",
    width=1600,
)
FIG_ZELLIGE_SUNSET = fig(
    "design-zellige-sunset.jpg",
    "Warm ochre and slate glazed Spectre tile floor in raking light",
    "<strong>Warm palette study.</strong> The same generated patch, re-glazed. Because tile IDs are stable, "
    "a palette change is a data change — the geometry, grout lines, and layout never move.",
    width=1600,
)
FIG_FABRICATION_PANEL = fig(
    "materials-fabrication-panel.jpg",
    "Brass relief panel of aperiodic monotile tiles suitable for fabrication reference",
    "<strong>Physical output reference.</strong> The same patch exports to STL or GLB for molds, relief "
    "panels, CNC toolpaths, and printed textures.",
    width=1400,
)
FIG_EDU_RIPPLE = fig(
    "education-rainbow-ripple.jpg",
    "Rainbow-colored aperiodic monotile tiles rippling in concentric waves",
    "<strong>Geometry that invites play.</strong> A generated Spectre patch displaced by a radial wave and "
    "colored by angle — the kind of demo that makes a classroom lean in. Every tile is the same shape; the "
    "pattern still never repeats.",
    width=1600,
)
FIG_EDUCATION = fig(
    "education-colorful-patch.png",
    "Colorful labeled aperiodic monotile patch for classroom demonstration",
    "<strong>Classroom patch.</strong> Deterministic color per tile — ideal for posters, museum panels, "
    "and puzzles that show order without translational repetition.",
    width=1400,
)
FIG_SIGNAL = fig(
    "signal-processing-sampling.png",
    "Tile centroids as a deterministic non-periodic sampling layout",
    "<strong>Sampling layout.</strong> Each tile centroid is a reproducible sample point — an alternative "
    "to regular grids and jittered noise for imaging and sensor-array experiments.",
    width=1400,
)
FIG_WAVES = fig(
    "waves-photonics-diffraction.png",
    "Aperiodic tile array styled for wave and diffraction studies",
    "<strong>Simulation-ready boundaries.</strong> Polygonal cells for comparing how periodic, random, "
    "and aperiodic scatterers interact with waves.",
    width=1400,
)
FIG_MATERIALS_SCIENCE = fig(
    "materials-science-lattice.png",
    "Metallic aperiodic lattice visualization for metamaterial studies",
    "<strong>Lattice candidate.</strong> Controlled non-periodic pore and strut layouts for metamaterials, "
    "electrodes, exchangers, and porous-media experiments.",
    width=1400,
)
FIG_ROBOTICS_HORIZON = fig(
    "robotics-horizon-walk.jpg",
    "Eye-height view over an aperiodic monotile ground plane stretching to a sunset horizon",
    "<strong>A ground plane with no repeats.</strong> An eye-height camera over a generated monotile "
    "terrain. Because no two neighborhoods are identical, every camera frame carries a unique local "
    "signature — a property regular grids cannot offer.",
    width=1600,
)
FIG_BIOLOGY = fig(
    "biology-scaffold-patch.png",
    "Soft pastel aperiodic packing pattern as a geometric scaffold",
    "<strong>Geometric scaffold.</strong> Clean packing layouts for exploring cellular, branching, and "
    "surface-constrained design questions — not biological models by default.",
    width=1400,
)
FIG_ALGORITHMS = fig(
    "algorithms-graph-patch.png",
    "Tile adjacency graph overlaid on an aperiodic monotile patch",
    "<strong>Benchmark graph.</strong> Stable tile IDs and neighbor structure for spatial indexing, "
    "embeddings, and geometric machine-learning experiments.",
    width=1400,
)
FIG_MOIRE_1DEG = fig_thumb(
    "aperiodicmoire-web.png",
    "Aperiodic moiré at 1° rotation: radial rosette cells emerging from layered monotile arrays",
    "<strong>1° rotation.</strong> Two aperiodic monotile arrays overlaid with a 1° twist. Near-alignment "
    "produces large rosette cells with a strong central focal point — a moiré landscape that feels "
    "dimensional even though it is a flat 2D beat pattern. "
    f'<a href="{ASSET}/aperiodicmoire.png">Full resolution</a>',
    width=320,
    side="left",
)
FIG_MOIRE_60DEG = fig(
    "aperiodicrivers-web.png",
    "Phason rivers at 60° rotation: winding moiré channels across layered aperiodic arrays",
    "<strong>60° rotation.</strong> The same layered arrays with a 60° relative twist. Interference "
    "concentrates into jagged, river-like channels — phason rivers — that cross the field in broad "
    "horizontal and vertical strokes. "
    f'<a href="{ASSET}/aperiodicrivers.png">Full resolution</a>',
    width=1400,
)
FIG_ALIAS_COVER = fig_thumb(
    "aliasing-cover-web.jpg",
    "Dense checker-like landscape with strong sampling and aliasing artifacts",
    "<strong>Aliasing on a periodic lattice.</strong> When high-frequency regular structure meets "
    "limited resolution — a camera, a screen, a texture sampler — false low-frequency patterns appear. "
    f'<a href="{ASSET}/aliasing-cover.jpg">Full resolution</a>',
    width=320,
    side="left",
)
FIG_ALIAS_CLEAN = fig(
    "aliasing-monotile-clean-web.jpg",
    "Natural rolling landscape textured with aperiodic monotile packing without obvious aliasing bands",
    "<strong>Monotile packing without the bands.</strong> An aperiodic layout has no single dominant "
    "lattice frequency to lock onto the sample grid, so the surface reads as continuous structure "
    "rather than shimmering stripes.",
    width=1400,
)
FIG_ALIAS_CHECKER = fig(
    "aliasing-checker-artifacts-web.jpg",
    "Same scene style with checker / periodic shading showing strong aliasing and moiré-like bands",
    "<strong>Periodic shading with aliasing.</strong> The same kind of scene, but with repeating "
    "checker structure: at distance the pattern beats against the pixel grid and collapses into "
    "false bands, sparkle, and crawling edges.",
    width=1400,
)
FIG_4D_LIFT = fig(
    "four-dimensional-lift.png",
    "Real Tile(1,1) edge vectors lifted into two coordinate planes in four dimensions, then projected as Hat, Tile(1,1), and Turtle",
    "<strong>One path, a family of projections.</strong> Coral and teal edges lift into separate "
    "coordinate planes in ℝ⁴. The Hat, Tile(1,1), and Turtle are different linear projections of the "
    "same closed lifted path. Original diagram generated from this site's canonical Tile(1,1) geometry, "
    "following Chéritat and Ma’s construction.",
    width=1600,
)


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
    hero: str = ""


ARTICLES: list[Article] = [
    # ------------------------------------------------------------------ #
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
  It distills the peer-reviewed literature
  ({len(REFERENCES)} sources and counting), tooling lineage, and practical workflows into cross-linked
  articles you can cite, share, and build on.
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
  <li>{link("moire", "Moiré")} — layered arrays, phason rivers, and navigable beat patterns</li>
  <li>{link("aliasing", "Aliasing")} — sampling artifacts, periodic risk, and monotile resistance</li>
  <li>{link("spectre-tile", "Spectre tile")} — the strictly chiral monotile discovered in 2023</li>
  <li>{link("hat-tile", "Hat tile")} — the first aperiodic monotile, March 2023</li>
  <li>{link("substitution-tiling", "Substitution tiling")} — how one tile grows into an infinite hierarchy</li>
</ul>
""",
            ),
            Section(
                "Browse by category",
                2,
                """
<div class="wiki-category-grid">
  <a class="wiki-category-card" href="aperiodic-monotile.html">
    <h3>Concepts</h3>
    <p>Aperiodic order, moiré, aliasing, and monohedral tilings</p>
    <span class="wiki-category-cta">Start with Aperiodic monotile &rarr;</span>
  </a>
  <a class="wiki-category-card" href="spectre-tile.html">
    <h3>Mathematics</h3>
    <p>Spectre, Hat, Tile(1,1), substitution rules, undecidability</p>
    <span class="wiki-category-cta">Start with Spectre tile &rarr;</span>
  </a>
  <a class="wiki-category-card" href="computer-graphics.html">
    <h3>Applications</h3>
    <p>Graphics, design, fabrication, education, and research frontiers</p>
    <span class="wiki-category-cta">Start with Computer graphics &rarr;</span>
  </a>
  <a class="wiki-category-card" href="resources-and-tools.html">
    <h3>Resources</h3>
    <p>Generators, datasets, museums, fabrication files, OEIS, and built installations</p>
    <span class="wiki-category-cta">Browse resources &amp; tools &rarr;</span>
  </a>
  <a class="wiki-category-card" href="bibliography.html">
    <h3>References</h3>
    <p>{len(REFERENCES)} curated scholarly sources plus an automated discovery registry</p>
    <span class="wiki-category-cta">Open the bibliography &rarr;</span>
  </a>
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
    # ------------------------------------------------------------------ #
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
            "First example": "Hat tile (March 2023)",
            "Chiral example": "Spectre tile (May 2023)",
            "Open since": "1960s (Wang tiles era)",
        },
        sections=[
            Section(
                "Definition",
                2,
                f"""
<p>
  An <strong>aperiodic monotile</strong> is a single closed shape in the plane whose congruent copies
  can tile the entire plane, but <em>only</em> in non-periodic arrangements. Unlike Penrose kite-and-dart sets
  or other multi-tile aperiodic systems, a monotile uses one shape — though reflected copies may be required
  depending on whether each side is equal or not.{cite(1)}{cite(3)}
</p>
<p>
  The long-standing <strong>einstein problem</strong> (German <em>ein Stein</em>, "one stone") asked whether such
  a shape exists. David Smith, Joseph Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss answered it in
  March 2023 with the Hat tile,{cite(1)} followed two months later by the strictly chiral Spectre tile.{cite(2)}
  Independent proofs and alternative constructions followed within months,{cite(4)}{cite(5)} a measure of how
  much attention the discovery drew.
</p>
{FIG_TILE_VARIANTS}
""",
            ),
            Section(
                "Sixty years of near misses",
                2,
                f"""
<p>
  The road to the monotile runs through most of modern tiling theory.{cite(3)} Wang tiles (1960s) first linked
  tiling to logic: Berger proved the tiling problem undecidable by building aperiodic sets of over 20,000
  square tiles. Raphael Robinson cut that to six; Penrose reached two with the kite and dart in 1974. For
  nearly fifty years the count sat at two, with mathematicians unsure whether a single-shape solution existed
  at all. Recent work continues to map where the boundary of decidability lies — translational tiling
  becomes undecidable with as few as three tiles,{cite(24)} translational monotiles are undecidable in
  higher dimensions,{cite(56)} and the structured-versus-wild dichotomy for translational tilings remains
  an active frontier.{cite(23)}
</p>
<p>
  Adjacent discoveries continue: an aperiodic set of three <em>convex</em> polygons was found in 2024,{cite(15)}
  and SAT solvers are now used to search polyform space for shapes with prescribed tiling behavior.{cite(17)}
</p>
""",
            ),
            Section(
                "Ordered without repeating",
                2,
                f"""
<p>
  Aperiodic tilings are not random. They are among the most structured objects in geometry: every tile sits
  in a deterministic hierarchy produced by substitution rules,{cite(2)}{cite(10)} tile counts across
  generations follow Fibonacci-like recurrences,{cite(12)} and the diffraction structure of Hat tilings is
  quasicrystalline — sharp peaks, like a crystal, but with symmetries no crystal can have.{cite(6)}
</p>
<p>
  For practical work this means patches can be regenerated from a seed, scaled, and exported with stable
  tile IDs — reproducible geometric datasets, not noise. That combination of global order, local variety,
  and zero translational repetition is exactly what makes monotile geometry valuable as a design and
  engineering primitive: it fills space as reliably as a grid while guaranteeing that no two regions ever
  look the same.
</p>
{FIG_TILING_ARRAY}
""",
            ),
            Section(
                "Weak vs strict chirality",
                2,
                f"""
<p>
  The Hat tile is asymmetric: every tiling mixes unreflected and reflected copies. Some observers argued this
  makes it a two-shape system; standard tiling literature counts reflected congruent copies as the same
  tile.{cite(1)}{cite(3)}
</p>
<p>
  The Spectre tile closed the question. Tile(1,1) is <em>weakly</em> chiral — banning reflections by rule
  leaves only non-periodic tilings — and its curved-edge Spectre variants are <em>strictly</em> chiral: the
  geometry itself makes reflected copies unusable, so only single-handed non-periodic tilings exist.{cite(2)}
  That distinction matters physically. A glazed ceramic tile, a stamped metal panel, or an injection-molded
  part cannot be flipped; a shape that tiles without reflections is cheaper to manufacture and impossible to
  install wrong-side-up.
</p>
""",
            ),
            Section(
                "Miki Imura monotile",
                2,
                f"""
<p>
  Not every monotile that makes non-periodic patterns is an aperiodic monotile. In 2025,
  <strong>Miki Imura</strong> published a family of equilateral “Modulo Krinkle” tiles that tile the plane
  with a single shape and can form striking non-periodic arrangements — often spiral or ring-like —
  using only elementary modular-arithmetic constructions.{cite(71)}
</p>
<p>
  The catch, which Imura states explicitly: the same prototile also admits an ordinary periodic tiling.
  So it is a monohedral tile with rich non-periodic modes, not an einstein. It belongs on this page because
  the popular conversation lumps “one shape that tiles without repeating” together; the mathematical
  distinction is whether <em>every</em> tiling must be non-periodic, or only some of them.
</p>
{FIG_MIKI_IMURA}
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
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
            "Sides": "14 (equilateral)",
            "Chirality": "Strictly chiral (curved edges)",
            "Paper": "arXiv:2305.17743",
        },
        sections=[
            Section(
                "Overview",
                2,
                f"""
<p>
  The <strong>Spectre</strong> is a 14-sided equilateral polygon — Tile(1,1) in the Hat's shape continuum —
  that tiles the plane aperiodically using only translations and rotations. No reflected tiles are needed,
  and in the strict curved-edge form, none are even possible. It was introduced in <em>A chiral aperiodic
  monotile</em> as the solution to the "vampire einstein" problem: an aperiodic monotile that casts no
  mirror image.{cite(2)}
</p>
{FIG_TILE_VARIANTS}
<p>
  The straight-edged Tile(1,1) is subtle: allowed reflections give it a simple periodic tiling, so it is
  only aperiodic when reflections are forbidden by rule (<em>weakly chiral</em>). Modifying its edges with
  matching curves — any of the variant silhouettes above — removes that escape hatch and produces the
  strictly chiral Spectre family.{cite(2)}
</p>
""",
            ),
            Section(
                "Geometry and structure",
                2,
                f"""
<p>
  Spectre tilings hide a surprising amount of internal order. Every Spectre tiling decomposes into
  recognizable hexagonal clusters,{cite(11)} and the whole family can be derived from an underlying rhombic
  tiling shared with the Hat and Turtle.{cite(8)} The substitution system that generates Spectre patches
  admits a homochiral (single-handed) inflation rule,{cite(10)} and tile counts per generation follow
  Fibonacci and Lucas number patterns.{cite(12)} Group-theoretic analysis places these tilings in a broader
  algebraic framework.{cite(9)} Long-range order is now understood through CASPr model sets with five
  Rauzy-fractal windows and pure-point diffraction,{cite(32)} and crystallographic analysis confirms
  non-periodic diffraction with chiral sixfold point symmetry.{cite(34)}{cite(35)} Algorithmic quasilattice
  constructions and explicit tiling generators complement the substitution picture.{cite(29)}{cite(30)}
</p>
{FIG_SPECTRE_PATCH}
<p>
  Conversions between Tile(1,1) tilings and other aperiodic families are constructive: non-periodic
  Tile(1,1) tilings can be transformed into tilings by other chiral monotile shapes.{cite(16)} Sugimoto’s
  two-part program converts Tile(1,1) patches into three-pentagon tilings,{cite(16)}{cite(57)} Independent
  proof techniques — including Akiyama and Araki's alternative argument — confirmed aperiodicity through
  different routes.{cite(4)}
</p>
""",
            ),
            Section(
                "Substitution structure",
                2,
                f"""
<p>
  Like other modern aperiodic tiles, Spectre patches are generated by substitution: a finite set of
  metatiles refines into smaller copies until a target region is filled. See
  {link("substitution-tiling", "Substitution tiling")} for the full picture, including an animated walk
  up the hierarchy. Public tooling — Kaplan's
  <a href="https://cs.uwaterloo.ca/~csk/spectre/" rel="noopener noreferrer">Spectre explorer</a> and
  community ports — implements these rules for interactive exploration.{cite(2)}
</p>
{FIG_HIERARCHY}
<p>
  The Aperiodic Monotile API packages this mathematics for production workflows: clipped patches,
  stable tile IDs and transforms, and exporters (SVG, STL, GLB, CSV, JSON) — the exact pipeline used to
  produce the renders across this wiki.
</p>
""",
            ),
            Section(
                "Relationship to the Hat",
                2,
                f"""
<p>
  The Hat is Tile(1,√3) and the Turtle is Tile(√3,1); the Spectre's Tile(1,1) sits at the equilateral point
  of the same continuum.{cite(2)} Every Spectre tiling is closely related to a tiling with sparse hats in a
  dense field of turtles, and vice versa — the three descriptions morph continuously into each other.
  Kaplan's historical survey traces the whole path from Penrose tiles to these modern monotiles.{cite(3)}
  Wang-tile machinery provides yet another route to both shapes.{cite(7)}
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="hat-tile",
        title="Hat tile",
        summary="The first aperiodic monotile, an asymmetric polykite announced in March 2023.",
        categories=["Mathematics", "Concepts"],
        see_also=["aperiodic-monotile", "spectre-tile"],
        infobox={
            "Announced": "March 2023",
            "Authors": "Smith, Myers, Kaplan, Goodman-Strauss",
            "Construction": "Polykite (8 kites of a hexagon)",
            "Reflections": "Required in every tiling",
            "Diffraction": "Quasicrystalline",
            "Paper": "arXiv:2303.10798",
        },
        sections=[
            Section(
                "Discovery",
                2,
                f"""
<p>
  The <strong>Hat</strong> is an asymmetric polykite — eight kites carved from a hexagonal grid — that
  admits tilings of the plane, but none that are periodic. Found by hobbyist David Smith and proven
  aperiodic by Smith, Myers, Kaplan, and Goodman-Strauss, it was the first shape shown to solve the
  einstein problem.{cite(1)} The original paper gives two proofs, one computer-assisted; independent
  arguments{cite(4)} and a direct construction{cite(5)} followed within months, and the shape can also be
  reached from classical Wang-tile machinery.{cite(7)}
</p>
{FIG_HAT_TILE}
""",
            ),
            Section(
                "Why reflections matter",
                2,
                f"""
<p>
  Every Hat tiling mixes unreflected and reflected tiles at a fixed ratio. Whether that disqualifies it as
  a "true" monotile sparked public debate; the authors and standard references (Grünbaum &amp; Shephard)
  count reflected congruent copies as the same tile shape.{cite(1)}{cite(3)} The debate was settled
  constructively two months later: the {link("spectre-tile", "Spectre")} tiles aperiodically with no
  reflected copies at all.{cite(2)}
</p>
""",
            ),
            Section(
                "Physics on the Hat lattice",
                2,
                f"""
<p>
  Because the Hat gives physicists their first aperiodic <em>monotile</em> lattice, it quickly became a
  substrate for model systems. Its tilings have quasicrystalline diffraction structure — sharp Bragg-like
  peaks with symmetries forbidden to periodic crystals.{cite(6)} Exact diffraction theory now places Hat
  tilings in CAP cut-and-project model sets with computable Fourier–Bohr amplitudes,{cite(31)}{cite(35)}
  while crystallographic analysis shows vertex diffraction riding on an underlying periodic
  framework.{cite(33)} Electronic and vibrational properties of the Hat lattice show behavior distinct from
  both crystals and random media.{cite(20)} Statistical
  mechanics has been worked directly on the tiling: the Ising model on the Hat lattice{cite(21)} and dimer
  models on the Spectre tiling{cite(22)} both reveal how aperiodic adjacency changes collective behavior.
  For anyone designing materials, these papers are the evidence base that monotile geometry is not just
  decoration — it changes physics.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
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
            "Tile counts": "Fibonacci–Lucas growth",
        },
        sections=[
            Section(
                "How substitution works",
                2,
                f"""
<p>
  <strong>Substitution tilings</strong> start from a small set of metatiles and repeatedly replace each
  metatile with a configuration of smaller copies. Iterating produces patches at every scale, and in the
  limit, an infinite tiling whose local structure is hierarchical but never repeats periodically.{cite(3)}
  For the Spectre system, nine labeled tile classes (Gamma through Psi) combine into superclusters of
  roughly eight tiles, which combine into super-superclusters, and so on forever.{cite(2)}{cite(10)}
</p>
{FIG_HIERARCHY}
<p>
  The animation above is generated from the real Tile(1,1) substitution rules: one tile becomes a cluster
  of 9, which becomes a supercluster of 71. Each color marks a first-generation cluster, so you can watch
  the same structural motif recur at each level — the geometric signature of aperiodic order.
</p>
""",
            ),
            Section(
                "Structure inside the hierarchy",
                2,
                f"""
<p>
  The hierarchy is not just qualitative. Tile counts per generation follow Fibonacci and Lucas number
  recurrences,{cite(12)} Spectre tilings decompose into recognizable hexagonal clusters,{cite(11)} and the
  whole system embeds in a rhombic tiling framework shared by the Hat and Turtle.{cite(8)} Substitution
  systems can even be built from overlapping iterated function systems, connecting tilings to fractal
  geometry.{cite(14)} Sturmian sequences — the one-dimensional cousins of aperiodic order — provide lattice
  models with closely related structure.{cite(13)} Labbé and Selinger give an explicit torus Markov
  partition construction for Hat tilings with fractal boundaries,{cite(53)} complementing the inflation
  picture above.
</p>
""",
            ),
            Section(
                "Practical generation",
                2,
                f"""
<p>
  For engineering and graphics, substitution runs until a patch covers a requested mask (rectangle, circle,
  custom polygon), then edge tiles are clipped to the boundary. Each tile carries an ID, a label, an affine
  transform, and adjacency data — turning abstract mathematics into reproducible geometry files. Because
  the recurrence is deterministic, the same request always returns the same patch: essential for version
  control, physical fabrication, and scientific reproducibility.
</p>
{FIG_TILING_ARRAY}
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="moire",
        title="Moiré",
        summary="Layered aperiodic arrays produce moiré landscapes, phason rivers, and a navigable perceived 3D space.",
        categories=["Concepts", "Computer graphics", "Research frontiers"],
        see_also=["aliasing", "computer-graphics", "signal-processing", "aperiodic-monotile"],
        hero=FIG_MOIRE_1DEG,
        infobox={
            "Core effect": "Beat interference between layered arrays",
            "Controls": "Translation (tx, ty), rotation",
            "Near-alignment": "Rosette cells, depth-like navigation",
            "Large rotation": "Phason rivers (open research)",
            "Related": f'{link("aliasing", "Aliasing")}',
        },
        sections=[
            Section(
                "What moiré is",
                2,
                f"""
<p>
  In optics and imaging, a <strong>moiré pattern</strong> is a large-scale interference figure that appears
  when two similar periodic or quasi-periodic structures are overlaid — fabrics, fences, screens, or
  printed grids. The eye (or a camera) does not see either layer’s fine detail; it sees the
  <em>beat</em> between them: bright and dark regions where local alignment reinforces or cancels.
</p>
<p>
  Aperiodic monotile arrays make that classic idea richer. Because each layer is ordered but
  non-repeating, the beat field does not collapse into ordinary wallpaper. Instead it yields
  cells, channels, and gradients that stay deterministic and seed-stable while still feeling
  organic.{cite(6)} For the related sampling problem — false patterns from under-resolving a single
  lattice — see {link("aliasing", "Aliasing")}.
</p>
""",
            ),
            Section(
                "Layered arrays and beat patterns",
                2,
                """
<p>
  Take one aperiodic monotile array and <strong>layer a second copy on top</strong> — same seed, same tile
  scale, but offset by a small transform: a translation (<em>tx</em>, <em>ty</em>) and/or a rotation θ
  away from perfect alignment. Where the two structured layers agree locally, contrast cancels; where
  they disagree, macroscopic bright and dark regions appear. The result is a <strong>new visual
  field</strong> that was not present in either layer alone.
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
                2,
                """
<p>
  At very small rotations from pure alignment — on the order of <strong>one degree</strong> — the
  interference often organizes into radial <strong>rosette</strong> or cell-like structures: a bright or
  dark focal center surrounded by lobes that read almost like flowers or lenses. These are not random
  halos; they are the macroscopic signature of microscopic tile disagreement accumulating across the
  patch (see the figure at left).
</p>
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
                f"""
<p>
  At larger rotation offsets the beat field changes character. For example, at <strong>60°</strong> between
  layers, interference can organize into winding, channel-like structures — <strong>phason rivers</strong>
  — that flow in broad strokes across the patch. In quasicrystal physics, a <em>phason</em> is a type of
  structural rearrangement; here the term is used informally for these moiré channels: coherent pathways
  where the two arrays stay in partial registry over long distances before shearing apart.
</p>
{FIG_MOIRE_60DEG}
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
  <li>Layered overlays for generative art and data visualization</li>
  <li>Experimental interfaces that treat (tx, ty, θ) as a navigable space</li>
  <li>Print and fabrication stacks where two structured layers meet</li>
  <li>Research into phason-like channels on aperiodic lattices</li>
</ul>
<p>
  Related sampling and display artifacts are covered under {link("aliasing", "Aliasing")}.
  See also {link("computer-graphics", "Computer graphics")} and
  {link("signal-processing", "Signal processing and imaging")}.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="aliasing",
        title="Aliasing",
        summary="How periodic structure creates false patterns under sampling — and why aperiodic monotile layouts resist them.",
        categories=["Concepts", "Computer graphics", "Research frontiers"],
        see_also=["moire", "computer-graphics", "signal-processing", "aperiodic-monotile"],
        hero=FIG_ALIAS_COVER,
        infobox={
            "Core effect": "False low-frequency patterns from undersampling",
            "Classic cause": "Periodic lattice vs. pixel / sensor grid",
            "Periodic risk": "High (checkers, grids, bricks)",
            "Monotile role": "Ordered layout without a single lattice beat",
            "Related": f'{link("moire", "Moiré")}',
        },
        sections=[
            Section(
                "What aliasing is",
                2,
                f"""
<p>
  In signal processing and computer graphics, <strong>aliasing</strong> is the appearance of false
  structure when a continuous (or finely detailed) signal is sampled too coarsely. A high frequency that
  the sampler cannot resolve does not disappear — it <em>folds</em> into a lower frequency the system
  <em>can</em> represent. On a screen that looks like shimmering edges, crawling lines, or striped bands
  that were never in the scene. The Nyquist–Shannon sampling theorem is the classical statement: to
  reconstruct a band-limited signal faithfully, you must sample at least twice its highest frequency.
</p>
<p>
  Spatial aliasing is the same idea in 2D. A brick wall, a fence, a checkerboard, or a dense hatched fill
  has a dominant lattice frequency. When that frequency approaches the pixel (or sensor, or print-dot)
  frequency, the two grids beat — and you see a pattern that belongs to neither grid alone. That beat is
  closely related to {link("moire", "moiré")}; aliasing is the sampling-side story, moiré the overlay story.
</p>
""",
            ),
            Section(
                "Why regular tilings are fragile",
                2,
                f"""
<p>
  Periodic monohedral tilings — squares, hexagons, brickwork — are efficient and familiar, but they put
  almost all of their energy on a few reciprocal-lattice peaks. Point a camera, mipmap a texture, or
  print at an awkward DPI, and those peaks are exactly what collide with the sample lattice.
</p>
<p>
  Anti-aliasing filters (mipmaps, supersampling, anisotropic filtering) try to remove frequencies the
  display cannot carry. They help, but they also blur. Random noise textures dodge the lattice problem
  by having no coherent peaks — at the cost of structure, reproducibility, and clean fabrication IDs.
</p>
<p>
  Aperiodic monotile patches sit between those extremes: <strong>ordered but non-repeating</strong>,
  with diffraction more like a quasicrystal than a crystal — sharp features, yet no single translational
  lattice to lock onto the sample grid.{cite(6)}{cite(27)} Sensor-array simulations on Hat-family layouts
  show the same principle in hardware: aperiodic monotile arrays can outperform tested periodic and other
  aperiodic baselines for spatial sampling and reconstruction.{cite(37)}
</p>
""",
            ),
            Section(
                "A cleaner monotile surface",
                2,
                f"""
<p>
  Below, a landscape shaded with an aperiodic monotile packing. There is still plenty of edge detail, but
  the structure does not present one repeating period for the image grid to quarrel with — so the surface
  stays readable instead of dissolving into false bands.
</p>
{FIG_ALIAS_CLEAN}
""",
            ),
            Section(
                "The periodic failure mode",
                2,
                f"""
<p>
  Contrast that with a checker / periodic shading of a similar scene. As soon as the repeating cells
  approach the pixel scale, aliasing takes over: sparkle, moiré-like stripes, and crawling edges that
  move when the camera or the mip level changes. The geometry of the hills is the same idea; the
  <em>lattice</em> is what breaks.
</p>
{FIG_ALIAS_CHECKER}
""",
            ),
            Section(
                "Practical takeaways for monotile work",
                2,
                f"""
<ul>
  <li><strong>Textures and decals</strong> — prefer aperiodic packing when the pattern will be viewed
  across many scales (games cameras, print proofs, video).</li>
  <li><strong>Scatter and fill</strong> — monotile instance layouts avoid the row/column bands of a grid
  scatter without looking random.</li>
  <li><strong>Halftone and fabrication</strong> — when a screen or toolpath is itself periodic, pairing it
  with a periodic artwork doubles the risk; an aperiodic artwork removes one of the two lattices.</li>
  <li><strong>Do not confuse the two effects</strong> — deliberate layered overlays are {link("moire", "moiré")}
  research; accidental undersampling of one lattice is aliasing.</li>
</ul>
<p>
  See {link("computer-graphics", "Computer graphics")} and
  {link("signal-processing", "Signal processing and imaging")} for workflow detail.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="computer-graphics",
        title="Computer graphics",
        summary="Using aperiodic monotile patches for scenes, textures, meshes, and sampling studies.",
        categories=["Applications"],
        see_also=["moire", "aliasing", "design-and-architecture"],
        infobox={
            "Status": "Immediately practical",
            "Formats": "SVG, GLB, STL, PNG, JSON",
            "Key benefit": "No visible repeats, fully deterministic",
        },
        sections=[
            Section(
                "The problem with repeats",
                2,
                f"""
<p>
  Every graphics artist knows the failure mode: a tiled texture or instanced grid looks fine up close, then
  the camera pulls back and the repetition snaps into view — visible seams, moiré shimmer, wallpaper
  patterns marching across the frame. The classic fixes all trade something away. Larger textures cost
  memory; randomized scatter loses structure and is hard to make deterministic; blend-based tiling blurs
  detail.
</p>
<p>
  An aperiodic monotile patch attacks the root cause. The geometry itself is mathematically incapable of
  translational repetition,{cite(2)} yet it is a single instanced shape — one mesh, one material slot, one
  draw-call strategy — and every placement is deterministic and seed-stable. You get grid-like production
  economics with guaranteed non-repetition.{cite(27)}
</p>
{FIG_SPLIT}
""",
            ),
            Section(
                "Same material, different geometry",
                2,
                f"""
<p>
  The split render above makes the argument visually: identical glazed-ceramic material, identical sun,
  one seam. The hexagonal floor on the left is calm but relentlessly repetitive — the eye finds rows
  instantly, and at render scale those rows become aliasing bands. The Spectre floor on the right has the
  same tile density and the same manufacturing simplicity (one shape!), but every neighborhood is unique.
  Nothing marches; nothing bands.
</p>
{FIG_CG_SUNSET}
{FIG_CG_BRASS}
""",
            ),
            Section(
                "Workflows",
                2,
                f"""
<ul>
  <li><strong>Environment scatter and grounds</strong> — instance one tile mesh over patch transforms
  (CSV/JSON export) in Blender, Houdini, Unreal, or Three.js; the renders on this page use exactly this
  pipeline.</li>
  <li><strong>Texture synthesis</strong> — bake a patch to a texture whose autocorrelation has no lattice
  peaks; useful for anti-moiré hatching, stippling, and decals.{cite(27)}</li>
  <li><strong>Meshes and subdivision</strong> — clipped SVG/GLB patches as base meshes for relief,
  displacement, and parametric surface studies.</li>
  <li><strong>Sampling studies</strong> — tile centroids as deterministic non-periodic sample points; see
  {link("signal-processing", "Signal processing and imaging")}.</li>
</ul>
<p>
  Because tile IDs are stable across regenerations, look-dev iterates safely: change the palette, the
  material, or the displacement while the layout stays pinned. The interface between aperiodic and
  periodic regions can even be controlled explicitly when a scene needs both.{cite(18)}
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="design-and-architecture",
        title="Design, art, and architecture",
        summary="Repeat-free ornamental surfaces, facades, textiles, and real-world tiling instructions.",
        categories=["Applications"],
        see_also=["computer-graphics", "materials-and-fabrication"],
        infobox={
            "Status": "Immediately practical",
            "Exports": "Vector SVG, fabrication meshes",
            "Real-world install": "Single orientation, no flips",
        },
        sections=[
            Section(
                "Surfaces that never wallpaper",
                2,
                f"""
<p>
  Ornament has always negotiated between order and monotony. Historic zellige, azulejo, and parquet crafts
  solved it with hand variation; modern manufacturing lost that solution the moment patterns became
  repeatable. The aperiodic monotile restores it structurally: one manufactured shape, infinite
  non-repeating arrangements, provable by theorem rather than promised by a craftsman.{cite(2)}{cite(3)}
</p>
{FIG_ZELLIGE_EMERALD}
<p>
  Because the tiling is deterministic, a designer can sign off on the <em>exact</em> layout before
  fabrication — every tile position is known, exportable, and reproducible. And because Tile(1,1) needs no
  reflected copies, production tooling stays single-sided: one mold, one die, one glaze line.{cite(2)}
</p>
{FIG_ZELLIGE_SUNSET}
""",
            ),
            Section(
                "Tiling a real surface: practical instructions",
                2,
                f"""
<p>
  Physical monotile installations are already common among mathematicians, makers, and a growing number of
  tile artisans. The working recipe, distilled from the research community's own guides:
</p>
<ol>
  <li><strong>Choose the Spectre, not the Hat, for physical work.</strong> Hat tilings require reflected
  copies — for glazed or finished tiles that means two distinct products. The Spectre tiles with one
  handedness only.{cite(2)}</li>
  <li><strong>Use curved or keyed edges.</strong> The straight-edged Tile(1,1) <em>can</em> be assembled
  into a periodic pattern by a well-meaning installer. Curved Spectre edges physically refuse periodic
  and reflected placements — the geometry enforces correctness.{cite(2)}</li>
  <li><strong>Get the outline from a trusted source.</strong> Kaplan's
  <a href="https://cs.uwaterloo.ca/~csk/spectre/" rel="noopener noreferrer">project page</a> publishes SVG
  outlines; community repositories provide OpenSCAD, STL, and DXF for 3D printing, laser cutting, and CNC
  (see the {link("bibliography", "bibliography")} tools list). Parametric models let you add
  orientation marks so pieces cannot be laid face-down.</li>
  <li><strong>Assemble by supertile.</strong> Working tile-by-tile invites dead ends. Pre-assemble the
  8-to-9-tile clusters from the substitution system, then place clusters — the same hierarchy the
  mathematics uses. See {link("substitution-tiling", "Substitution tiling")}.</li>
  <li><strong>Or skip layout entirely:</strong> generate the exact patch for your wall's dimensions with a
  clipping mask, and deliver the installer a numbered plan where every tile has an ID and position.</li>
</ol>
<p>
  For hybrid designs, research on interfaces between aperiodic and periodic tilings shows how a Spectre
  field can hand off cleanly to a conventional grid at a boundary — useful where a feature wall meets
  standard tile.{cite(18)}
</p>
""",
            ),
            Section(
                "Applications",
                2,
                f"""
<ul>
  <li>Feature walls, floors, and facades with provable non-repetition — including built limestone terraces
  assembled from hundreds of waterjet-cut Spectre pieces (see {link("bibliography", "bibliography")})</li>
  <li>Three-dimensional topological interlocking assemblies from identical aperiodic blocks{cite(50)}</li>
  <li>Generative sculpture, ornamental screens, and visual illusions</li>
  <li>Textiles, wallpaper, packaging, embossing, and engraving with no repeat unit</li>
  <li>Lightweight shells, tensile structures, and spatial studies for built environments</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="materials-and-fabrication",
        title="Materials and fabrication",
        summary="From relief panels to STL toolpaths — one patch, many physical outputs.",
        categories=["Applications"],
        see_also=["design-and-architecture", "materials-science"],
        infobox={
            "Exports": "SVG, STL, GLB, CSV, JSON",
            "Status": "Immediately practical",
            "Tooling": "Single-sided (no mirrored parts)",
        },
        sections=[
            Section(
                "One geometry, many outputs",
                2,
                f"""
<p>
  A single generated patch exports as SVG for cutting, STL for printing, GLB for instancing, and CSV/JSON
  for custom toolpaths. One design becomes a relief panel, a printed texture, an instanced mesh, or a
  dataset of tile transforms — with identical geometry in each.{cite(2)}{cite(10)}
</p>
{FIG_FABRICATION_PANEL}
<p>
  The chirality result is a manufacturing feature, not a footnote: because Spectre tilings never need
  mirrored parts, one mold or die covers the entire surface.{cite(2)} Community fabrication files —
  OpenSCAD models, STLs with orientation grids, laser-cut outlines — are indexed in the
  {link("bibliography", "bibliography")} and {link("resources-and-tools", "Resources and tools")}. Experimental Hat honeycombs and aperiodic composite panels
  demonstrate that these exports translate into measurable mechanical gains,{cite(42)}{cite(46)}{cite(49)}
  and deployable monotile kirigami shows how flat sheets fold into aperiodic surface
  structures.{cite(51)}
</p>
""",
            ),
            Section(
                "Directions",
                2,
                f"""
<ul>
  <li>Toolpath and infill experiments — aperiodic infill avoids the resonance planes of periodic infill</li>
  <li>Support-free printing studies, topology optimization, and surface finishing</li>
  <li>Architectural panels, molds, product surfaces, screens, and repeat-free decoration</li>
  <li>Three-dimensional topological interlocking assemblies built from identical aperiodic
  blocks{cite(50)}</li>
  <li>Origami-adjacent folding studies: flat-foldable synthesis environments show how computational tools
  explore fold-pattern spaces{cite(26)}; monotile kirigami extends this to deployable aperiodic
  sheets{cite(51)}</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="education",
        title="Education",
        summary="Teaching a fresh mathematical discovery through manipulable patches and physical models.",
        categories=["Applications"],
        see_also=["aperiodic-monotile", "substitution-tiling"],
        infobox={
            "Audience": "Classrooms, museums, workshops",
            "Status": "Immediately practical",
            "Exhibits": "MoMath and worldwide",
        },
        sections=[
            Section(
                "A discovery you can hold",
                2,
                f"""
<p>
  Most mathematics taught in school is centuries old. The aperiodic monotile was discovered in 2023 — by a
  retired print technician experimenting with paper cutouts — and its proof is genuinely deep.{cite(1)}{cite(3)}
  That combination is rare gold for educators: a frontier result whose objects fit in a student's hand.
  The National Museum of Mathematics ran public competitions and exhibits around the Hat and Spectre within
  months of publication (see {link("bibliography", "bibliography")} for links).
</p>
{FIG_EDU_RIPPLE}
""",
            ),
            Section(
                "Classroom activities",
                2,
                f"""
<ul>
  <li><strong>Cut-and-tile workshops</strong> — print or laser-cut Spectre outlines and challenge groups to
  extend a patch; the substitution clusters emerge naturally from play.</li>
  <li><strong>Hierarchy walks</strong> — the animated hierarchy in {link("substitution-tiling", "Substitution tiling")}
  turns inflation rules into something students can watch and predict.</li>
  <li><strong>Counting projects</strong> — tile counts per generation follow Fibonacci–Lucas recurrences,
  linking geometry to sequences students already know.{cite(12)}</li>
  <li><strong>Chirality demonstrations</strong> — ceramic tiles cannot be flipped; the Spectre's
  no-reflection property becomes a physical puzzle rather than an abstract definition.{cite(2)}</li>
</ul>
{FIG_EDUCATION}
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="signal-processing",
        title="Signal processing and imaging",
        summary="Deterministic non-periodic sampling layouts for reconstruction and sensor geometry.",
        categories=["Research frontiers"],
        see_also=["moire", "aliasing", "waves-and-photonics"],
        infobox={"Status": "Research frontier", "Key property": "No lattice frequency to alias against"},
        sections=[
            Section(
                "Between the grid and the dice roll",
                2,
                f"""
<p>
  Regular sampling aliases: any signal content near the lattice frequency folds into artifacts. Random
  sampling trades aliasing for noise and loses reproducibility. Aperiodic monotile layouts offer a third
  option with a genuinely different spectrum — the quasicrystalline diffraction structure of monotile
  tilings means sharp spectral features but no periodic lattice to beat against.{cite(6)}
</p>
{FIG_SIGNAL}
<p>
  Recent work on 2D histogram binning shows the practical direction: non-square binning geometries
  materially change what structure an analysis can resolve.{cite(27)} Tile centroids, edges, and adjacency
  graphs from a generated patch provide deterministic, reproducible sampling frames for the same kind of
  experiments in reconstruction, denoising, and compression. Mordret and Grushin demonstrate the payoff in
  simulated sensor arrays: Hat-family monotile layouts beat tested periodic and aperiodic baselines for
  spatial sampling and aliasing resistance.{cite(37)}
</p>
""",
            ),
            Section(
                "Experiment directions",
                2,
                f"""
<ul>
  <li>Sampling theory: compare monotile centroids against grids, jittered grids, blue noise, and Penrose
  point sets in reconstruction benchmarks</li>
  <li>Sensor arrays: radar, sonar, MRI, and CT geometry studies where periodic element spacing creates
  grating lobes{cite(19)}{cite(37)}</li>
  <li>Phased arrays: simulated Hat layouts achieve low grating lobes and high aperture efficiency in
  limited-scan beamforming studies{cite(38)}; patent filings propose Hat polykite elements for SATCOM
  arrays (proposal only).{cite(68)}</li>
  <li>Compressed sensing: deterministic non-periodic measurement patterns with stable addressing</li>
  <li>Anti-aliasing masks and halftone screens; see {link("aliasing", "Aliasing")} and {link("moire", "Moiré")}</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="waves-and-photonics",
        title="Waves, acoustics, and photonics",
        summary="Non-repeating tiled surfaces for scattering, diffraction, and waveguide studies — now with experimental results.",
        categories=["Research frontiers"],
        see_also=["materials-science", "signal-processing"],
        infobox={
            "Status": "Active research (experimental)",
            "Landmark": "Chiral diffraction measured (2025)",
        },
        sections=[
            Section(
                "From conjecture to measurement",
                2,
                f"""
<p>
  This is the monotile application area with real laboratory results. Moritake, Takiguchi, Aihara, and
  Notomi fabricated a photonic lattice arranged as a Spectre monotile tiling and measured its diffraction:
  the pattern shows <strong>chiral diffraction</strong> — handedness-dependent optical response arising
  purely from the aperiodic chiral geometry, with no chiral material required.{cite(19)} The theoretical
  foundation is the quasicrystalline diffraction structure of monotile tilings.{cite(6)}
</p>
{FIG_WAVES}
<p>
  Condensed-matter theory adds depth: the electronic and vibrational properties of the Hat lattice differ
  measurably from periodic and random baselines,{cite(20)} Ising spins on the Hat tiling order
  differently,{cite(21)} and dimer statistics on the Spectre tiling reveal distinctive combinatorial
  structure.{cite(22)} Together these establish that monotile geometry changes wave and lattice physics —
  the open question is where that change is useful. Experimental polariton realizations on monotile lattices
  now show Bragg peaks and long-range coherence,{cite(40)} with theory predicting critical states and
  anomalous transport in related optical setups.{cite(41)} Tile-shape geometry can tune topological phases
  and the quantum geometric tensor in model systems.{cite(39)}
</p>
""",
            ),
            Section(
                "Candidate applications",
                2,
                f"""
<ul>
  <li>Acoustic diffusers and panels: aperiodic surfaces scatter without the flutter echoes of periodic ones</li>
  <li>Photonic and phononic structures with engineered chiral response</li>
  <li>Antenna and metasurface layouts that suppress grating lobes{cite(38)}</li>
  <li>Simulation-ready polygon exports for comparing periodic, random, and aperiodic boundaries in FDTD/FEM</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="materials-science",
        title="Materials science and fluids",
        summary="Metamaterials, lattices, electrodes, exchangers, and porous media candidates.",
        categories=["Research frontiers"],
        see_also=["materials-and-fabrication", "waves-and-photonics"],
        infobox={"Status": "Research frontier", "Evidence base": "Hat-lattice physics papers"},
        sections=[
            Section(
                "Geometry as a material parameter",
                2,
                f"""
<p>
  Engineers tune performance by changing geometry: pores, channels, lattices, electrodes, exchangers, and
  support structures. Periodic geometries bring resonances and preferred failure planes; random geometries
  bring variance and poor reproducibility. Aperiodic monotile arrays give a controlled middle path —
  deterministic, manufacturable from a single element, and provably free of translational symmetry.{cite(2)}
</p>
{FIG_MATERIALS_SCIENCE}
<p>
  The evidence that this matters physically is accumulating: distinct electronic and vibrational spectra on
  the Hat lattice,{cite(20)} modified phase behavior for spins,{cite(21)} distinctive dimer combinatorics,{cite(22)}
  and measured chiral optical response.{cite(19)} Related lattice families from Sturmian systems{cite(13)}
  and iterated function systems{cite(14)} extend the design space beyond the monotile itself.
</p>
<p>
  Mechanical evidence is now substantial. Printed Hat honeycombs achieve isotropic zero Poisson’s
  ratio,{cite(42)} converge toward isotropic continuum elasticity,{cite(43)} and allow independent tuning
  of modulus and Poisson ratio across Hat-family variants.{cite(44)} Comparative studies map effective
  properties across Hat, Turtle, and Spectre lattices.{cite(45)} In composites, aperiodic monotile
  reinforcements outperform tested honeycomb controls in stiffness, strength, and toughness,{cite(46)}
  with follow-on work using machine learning to explore the family{cite(47)} and multi-phase curvature
  engineering.{cite(48)} Interlocking aperiodic assemblies show dramatic fracture-resistance gains over
  periodic honeycombs.{cite(49)} TPMS cells patterned on Hat, Turtle, and Spectre tilings offer another
  design axis for thin-walled metamaterials,{cite(60)} and phase-field studies explore polycrystalline
  evolution on Hat-family meshes.{cite(61)}
</p>
<p class="ref-note">
  Several papers label new lattices “einstein monotile” while using geometry <em>inspired by</em> rather
  than identical to Smith’s Hat or Spectre — see refs.&nbsp;[62] and [64]–[65]. Always verify whether a
  source uses canonical tile outlines or a derivative mesh.
</p>
""",
            ),
            Section(
                "Directions",
                2,
                """
<ul>
  <li>Metamaterials, auxetic lattices, acoustic cloaking, and programmable matter</li>
  <li>Battery electrodes, fuel cells, solar concentrators, thermal exchangers, and porous media</li>
  <li>Crack-arrest and impact structures: no periodic cleavage planes for failures to follow</li>
  <li>Drag reduction, turbulence control, microfluidics, and surface texturing</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="robotics-and-mobility",
        title="Robotics and mobility",
        summary="Aperiodic surfaces as navigation substrates: every neighborhood is a unique landmark.",
        categories=["Research frontiers"],
        see_also=["algorithms-and-machine-learning"],
        infobox={
            "Status": "Research frontier (no published robotics demo yet)",
            "Key benefit": "Position from local appearance",
        },
        sections=[
            Section(
                "Why aperiodic beats periodic here",
                2,
                f"""
<p>
  <em>No published robotics application uses monotile floors yet; the argument below is a research
  direction, not a demonstrated product.</em> Regular grids are the worst possible texture for visual
  localization: every cell looks like every other cell, so a camera looking at a periodic floor learns
  nothing about <em>where</em> it is. Random textures
  are locally distinctive but cannot be regenerated or queried. An aperiodic monotile surface is the
  interesting middle: <strong>every neighborhood is provably unique</strong>,{cite(2)} yet the whole
  surface is deterministic — a robot that recognizes its local tile configuration can, in principle, look
  up its exact pose. The tiling is simultaneously the floor and the map.
</p>
{FIG_ROBOTICS_HORIZON}
<p>
  Algorithmic groundwork exists: exact extraction of finite tessellation structure from observed
  fragments{cite(25)} is precisely the primitive a localization system needs, and computational tiling
  search shows the machinery scales.{cite(17)} Fibonacci-structured tile counts give the hierarchy usable
  statistical signatures at every scale.{cite(12)}
</p>
""",
            ),
            Section(
                "Test surfaces and mechanics",
                2,
                """
<ul>
  <li>Repeatable benchmark terrains: deterministic aperiodic ground for SLAM and motion-planning papers,
  regenerable exactly from a seed by any lab</li>
  <li>Grasping and traction textures with no periodic slip planes</li>
  <li>Tire tread, road surface, and rail-bed studies where periodic patterns excite resonance</li>
  <li>Deployable structures and folding mechanisms; flat-foldability synthesis tools point the way</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="biology-and-medicine",
        title="Biology and medicine",
        summary="Geometric scaffolds for packing, growth, folding, and implant design studies.",
        categories=["Research frontiers"],
        see_also=["materials-science"],
        infobox={"Status": "Research frontier"},
        sections=[
            Section(
                "Clean scaffolds for messy questions",
                2,
                f"""
<p>
  Natural systems are full of packing, branching, growth, folding, and surface constraints — and they are
  conspicuously non-periodic. Aperiodic monotile patches are not biological models by default, but they are
  clean geometric scaffolds for asking better questions: what does growth on a structured-but-non-repeating
  substrate look like? How do cells or crystals pack when the template forbids periodicity?{cite(6)}{cite(13)}
</p>
{FIG_BIOLOGY}
<p>
  For implants and tissue scaffolds the mechanical argument mirrors {link("materials-science", "materials science")}:
  aperiodic strut layouts avoid the aligned failure planes and resonances of periodic lattices while
  remaining fully specified for regulatory review — every strut position is deterministic and
  documentable.{cite(2)}
</p>
""",
            ),
            Section(
                "Directions",
                2,
                """
<ul>
  <li>Morphogenesis, shell growth, protein folding, cellular packing, and neural geometry studies</li>
  <li>Implants, prosthetics, vascular stents, tissue scaffolds, and surgical planning</li>
  <li>Crystal nucleation templates, catalysts, zeolites, and molecular cage geometry</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="algorithms-and-machine-learning",
        title="Algorithms and machine learning",
        summary="Structured non-repeating benchmark geometry for spatial algorithms and geometric ML.",
        categories=["Research frontiers"],
        see_also=["robotics-and-mobility", "signal-processing"],
        infobox={
            "Status": "Research frontier",
            "Key property": "Structured, non-memorizable, reproducible",
        },
        sections=[
            Section(
                "A benchmark that cannot be memorized",
                2,
                f"""
<p>
  Machine learning systems exploit repetition; aperiodic monotile geometry is repetition-proof by theorem.
  Because every patch regenerates exactly from stable IDs and transforms, it makes an unusual benchmark
  input: <strong>structured enough to learn on, impossible to memorize globally, and perfectly
  reproducible</strong>.{cite(2)} Monotiles are also nearly absent from pre-2023 training corpora, which
  makes them a probe for how models handle genuinely novel geometric structure.
</p>
{FIG_ALGORITHMS}
<p>
  The theoretical backdrop is rich. Tiling problems sit at the edge of computability — translational tiling
  is undecidable with three tiles,{cite(24)} and the structured-vs-wild dichotomy is an open research
  program.{cite(23)} On the constructive side, SAT solvers detect isohedral polyforms,{cite(17)} exact
  algorithms extract tessellation generators from data,{cite(25)} and group-theoretic formulations connect
  tilings to algebra.{cite(9)} Percolation thresholds on Hat-family lattices are now being mapped by Monte
  Carlo simulation,{cite(52)} giving concrete statistical signatures for random-process models on monotile
  graphs. Batle and Bednorz extend Li–Boyle quantum error-correcting codes to Hat and Spectre tilings,
  grounding recoverability in the supertile hierarchy and CAP torus parametrization.{cite(55)}
</p>
""",
            ),
            Section(
                "Experiment directions",
                2,
                """
<ul>
  <li>Spatial indexing, nearest-neighbor search, graph embeddings, and geometric hashing over tile adjacency graphs</li>
  <li>Geometric deep learning: equivariant models tested on structure with no translation group</li>
  <li>Procedural benchmarks for SLAM, navigation, and reconstruction (see Robotics)</li>
  <li>Cryptographic experiments — geometric trapdoors and hardness ideas — research-only unless formally reviewed</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="four-dimensional-lift",
        title="Four-dimensional lift",
        summary="Nan Ma’s coherent ℝ⁴ edge lift, and how it differs from CAP/CASPr cut-and-project theory.",
        categories=["Mathematics", "Visualizations"],
        see_also=["aperiodic-monotile", "spectre-tile", "substitution-tiling"],
        infobox={
            "Initial idea": "Nan Ma",
            "Exposition": "Arnaud Chéritat with Nan Ma",
            "First dated artifact": "9 June 2023",
            "Ambient space": "ℝ⁴ = ℝ² × ℝ²",
            "Key distinction": "Edge lift ≠ cut-and-project proof",
        },
        sections=[
            Section(
                "The observation",
                2,
                f"""
<p>
  The whole Hat or Spectre tiling can be treated as a single static object in four-dimensional space.
  Arnaud Chéritat credits the initial idea to Nan Ma: not merely lifting one Tile(<em>a,b</em>) outline,
  but assigning coherent ℝ⁴ coordinates to every vertex in an entire simply connected tiling.{cite(54)}
  Ma’s earliest securely dated public artifact is the
  <a href="https://github.com/nanma80/aperiodic-monotile-4d" rel="noopener noreferrer">aperiodic-monotile-4d</a>
  repository created 9 June 2023.
</p>
{FIG_4D_LIFT}
""",
            ),
            Section(
                "How the lift works",
                2,
                f"""
<p>
  Write four-space as ℝ⁴ = ℝ²<sub>red</sub> × ℝ²<sub>green</sub>. Tile(<em>a,b</em>) has two
  direction classes: edges at multiples of 60° and edges at odd multiples of 30°. A directed edge
  (<em>x,y</em>) in the first class lifts to (<em>x,y,0,0</em>); one in the second lifts to
  (<em>0,0,x,y</em>). Opposite edges cancel by class, so the fourteen lifted vectors close into one
  polygonal path in ℝ⁴.
</p>
<p>
  The ordinary two-dimensional tile is recovered by
  L<sub>a,b</sub>(<em>u,v</em>) = <em>a u + b v</em>. Changing (<em>a,b</em>) changes the
  projection, not the lifted object: Hat, Tile(1,1), Turtle, Chevron, and Comet are views of the same
  four-dimensional edge path. Adjacent tiles give their shared edge the same lifted vector; integrating
  these vectors gives path-independent vertex coordinates across any simply connected patch.{cite(54)}
</p>
<p>
  For homochiral Tile(1,1)/Spectre tilings, tiles rotated by an odd multiple of 30° swap the two edge
  classes. Animations vary an ℝ⁴→ℝ³ projection while the lifted surface stays still. This is why a
  complicated coordinated deformation can be understood as moving a camera around one higher-dimensional
  object.
</p>
""",
            ),
            Section(
                "Scope and limits",
                2,
                f"""
<p>
  Ma’s construction is best understood as a discrete height function or stepped surface. The edge lift is
  canonical, but filling each lifted tile interior with a surface is not unique; rendered solids include a
  visualization choice. The lift does not by itself prove that Hat or Spectre control points form a regular
  model set.
</p>
<p>
  That stronger result comes from distinct work. Baake, Gähler, and Sadun construct the self-similar CAP
  representative of the Hat family and a 4:2 cut-and-project scheme with two-dimensional internal
  space.{cite(31)} Baake, Gähler, Mazáč, and Sadun do the analogous job for Spectre via CASPr and five
  Rauzy-fractal windows, proving pure-point spectrum and diffraction.{cite(32)} These frameworks use
  algebraic return modules, Galois conjugation, and acceptance windows—not Ma’s edge coloring.
</p>
""",
            ),
            Section(
                "Six dimensions and diffraction",
                2,
                f"""
<p>
  Socolar’s independent Golden Key construction embeds a related Hat metatiling in a six-dimensional
  hypercubic lattice and projects selected points to the plane, establishing golden-mean quasiperiodicity
  and a phason degree of freedom.{cite(6)} Exact diffraction calculations later use CAP and CASPr
  reprojections plus renormalization cocycles to compute Fourier–Bohr amplitudes through fractal
  windows.{cite(35)}{cite(36)}
</p>
<p>
  These are complementary views: Ma’s lift explains the moving Tile(<em>a,b</em>) family geometrically;
  CAP/CASPr explain long-range order dynamically; the six-dimensional Golden Key construction exposes a
  larger quasiperiodic embedding.
</p>
""",
            ),
            Section(
                "Explore it",
                2,
                """
<ul>
  <li><a href="https://www.math.univ-toulouse.fr/~cheritat/2023-monotile/4D-lift/" rel="noopener noreferrer">Chéritat and Ma’s full exposition</a></li>
  <li><a href="https://www.math.univ-toulouse.fr/~cheritat/AppletsDivers/Monotile-4D-lift/3-outlines/" rel="noopener noreferrer">Interactive 4D projection applet</a> (CC BY-SA)</li>
  <li><a href="https://github.com/nanma80/aperiodic-monotile-4d" rel="noopener noreferrer">Nan Ma’s Wolfram Language repository</a> (no license; link only)</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="resources-and-tools",
        title="Resources and tools",
        summary="Generators, datasets, museums, fabrication files, OEIS sequences, and built installations.",
        categories=["References", "Meta"],
        see_also=["bibliography", "education", "materials-and-fabrication"],
        infobox={
            "Scope": "Public web resources through July 2026",
            "Scholarly papers": f"See {link('bibliography', 'Bibliography')} ({len(REFERENCES)} refs)",
            "Auto-discovery": "Crossref/arXiv registry JSON",
            "Terminology": "Tile(1,1) ≠ Spectre",
        },
        sections=[
            Section(
                "How to use this index",
                2,
                f"""
<p>
  The numbered {link("bibliography", "bibliography")} holds peer-reviewed and preprint research with stable
  citation anchors. This page catalogs everything else: official generators, open fabrication files,
  museum exhibits, workshop kits, games, OEIS sequences, journalism, and documented installations.
</p>
<p>
  <strong>Tile(1,1) is not the same as Spectre.</strong> The straight-edged Tile(1,1) polygon admits a
  periodic tiling if reflected copies are mixed; Spectres are edge-modified, strictly chiral shapes. Many
  community repositories reuse the word “Spectre” for straight-edged outlines — verify the geometry before
  fabrication.{cite(2)}
</p>
<p>
  An automated crawl maintains a machine-readable
  <a href="source-registry.json">source registry</a> for literature discovery. The lists below are
  human-curated and tiered: link freely, but check each site’s license before republishing assets.
</p>
""",
            ),
            Section(
                "Catalog",
                2,
                render_web_resources_html(compact=True),
            ),
            Section(
                "Still missing?",
                2,
                """
<p>
  No single index can guarantee completeness on the open web. If you maintain a generator, dataset,
  fabrication guide, or installation archive that belongs here,
  <a href="../../contact.html">contact us</a> with a URL, license, and one-line description.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="bibliography",
        title="Bibliography",
        summary=f"{len(REFERENCES)} curated scholarly references, tools index, and an automated discovery registry.",
        categories=["References"],
        see_also=["aperiodic-monotile", "spectre-tile", "four-dimensional-lift", "resources-and-tools"],
        sections=[
            Section("References", 2, render_references_html() + f"""
<p class="ref-note">
  An automated Crossref/arXiv crawl maintains a separate
  <a href="source-registry.json">source registry</a> for literature discovery. The numbered list above is
  human-curated and cited throughout the wiki. For generators, museums, and fabrication files see
  {link("resources-and-tools", "Resources and tools")}.
</p>
"""),
        ],
    ),
]

NAV_GROUPS = [
    ("Concepts", ["aperiodic-monotile", "moire", "aliasing"]),
    ("Mathematics", ["spectre-tile", "hat-tile", "substitution-tiling", "four-dimensional-lift"]),
    ("Applications", [
        "computer-graphics", "design-and-architecture", "materials-and-fabrication", "education",
    ]),
    ("Research frontiers", [
        "signal-processing", "waves-and-photonics", "materials-science",
        "robotics-and-mobility", "biology-and-medicine", "algorithms-and-machine-learning",
    ]),
    ("Meta", ["resources-and-tools", "bibliography"]),
]

ARTICLE_BY_SLUG = {a.slug: a for a in ARTICLES}


def render_nav(current: str) -> str:
    parts = ['<nav class="wiki-nav" aria-label="Wiki navigation">']
    parts.append('<p class="wiki-nav-title"><a href="index.html">Wiki</a></p>')
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
    <title>{html.escape(page_title)} | Aperiodic Monotile wiki | Untiling</title>
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
        <span>Untiling</span>
      </a>
      <nav class="nav" aria-label="Primary navigation">
        <a href="../../use-cases/generative-art.html">Art</a>
        <a href="../index.html">Research</a>
        <a class="nav-generator" href="https://aperiodicgenerator.com/">Generator</a>
        <a href="../../apparel/">Shop</a>
        <a href="index.html" aria-current="page">Wiki</a>
      </nav>
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
          {article.hero if article.hero else ""}
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
    return """<!doctype html>
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

    # Legacy combined URL → moiré article
    (WIKI_ROOT / "moire-and-aliasing.html").write_text(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="refresh" content="0;url=moire.html" />
    <link rel="canonical" href="https://untiling.com/research/wiki/moire.html" />
    <title>Redirecting...</title>
  </head>
  <body>
    <p>This page split into <a href="moire.html">Moire</a> and <a href="aliasing.html">Aliasing</a>.</p>
  </body>
</html>
""",
        encoding="utf-8",
    )
    print("wrote research/wiki/moire-and-aliasing.html (redirect)")

    (RESEARCH_ROOT / "index.html").write_text(render_research_hub(), encoding="utf-8")
    print(f"wrote {RESEARCH_ROOT.relative_to(SITE_ROOT)}/index.html")

    write_wiki_assets()
    print("wrote research/wiki assets")


if __name__ == "__main__":
    main()
