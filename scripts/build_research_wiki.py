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
         title="An aperiodic monotile", arxiv="2303.10798", doi="10.5070/C64163843",
         note="Peer-reviewed Hat theorem: the first solution to the einstein problem."),
    dict(n=2, authors="David Smith, Joseph Samuel Myers, Craig S. Kaplan, and Chaim Goodman-Strauss",
         title="A chiral aperiodic monotile", arxiv="2305.17743", doi="10.5070/C64264241",
         note="Peer-reviewed Tile(1,1) and Spectre theorem: aperiodicity without reflections."),
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
         title="Hexagonal quasiperiodic tilings as decorations of periodic lattices", arxiv="2404.11378",
         note="Vertices may sit on a periodic lattice while edge/bond arrangement remains quasiperiodic; not a constructed Hat-periodic interface."),
    dict(n=19, authors="Yuto Moritake, Masato Takiguchi, Takuma Aihara, and Masaya Notomi",
         title="Chiral diffraction from aperiodic monotile structure", arxiv="2506.07561",
         doi="10.1038/s41467-026-75023-7",
         note="Nature Communications experiment on a fabricated Hat-centroid quasilattice: sharp position-independent Bragg peaks, pinwheel diffraction, mirror reversal, and circular-polarization response."),
    dict(n=20, authors="Justin Schirmann, Selma Franca, Felix Flicker, and Adolfo G. Grushin",
         title="Physical properties of an Aperiodic monotile: Graphene-like features, chirality and zero-modes",
         arxiv="2307.11054",
         doi="10.1103/PhysRevLett.132.086402",
         note="Peer-reviewed tight-binding study on the Hat vertex graph; a theoretical electronic/wave model, not a vibrational experiment."),
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
         note="Preprint theorem for three connected polyhypercubes in four dimensions; not a planar or monotile result."),
    dict(n=25, authors="Sushish Baral, Paulo Garcia, and Warisa Sritriratanarak",
         title="On the Exact Algorithmic Extraction of Finite Tessellations Through Prime Extraction of Minimal Representative Forms",
         arxiv="2603.00911",
         note="Preprint prototype for exact rectangular symbolic grids; not geometric reconstruction from photographs or noisy fragments."),
    dict(n=26, authors="Naaisha Agarwal, Yihan Wu, Yichang Jian, Yifei Peng, Yao-Xiang Ding, Nishad Mansoor, Yikuan Hu, Mohan Li, Wang-Zhou Dai, and Emanuele Sansone",
         title="OrigamiBench: An Interactive Environment to Synthesize Flat-Foldable Origamis", arxiv="2603.13856", note=""),
    dict(n=27, authors="I. Vaiman",
         title="Enabling fundamental understanding of Nature with novel binning methods for 2D histograms",
         arxiv="2603.30006",
         note="Satirical/tool paper accompanying arbitrary-polygon histogram software; not comparative evidence for anti-aliasing or reconstruction accuracy."),
    dict(n=28, authors="Saksham Sharma",
         title="Proof of Aperiodicity of hat tile using the Golden Ratio", arxiv="2403.09640",
         note="Unreviewed claimed proof with an insufficiently verified count-ratio argument; quarantined and not used to support the Hat theorem."),
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
         title="Periodic diffraction from an aperiodic monohedral tiling, the Spectre tiling. Addendum",
         doi="10.1107/S2053273324008945",
         note="Spectre diffraction is non-periodic with chiral sixfold point symmetry."),
    dict(n=35, authors="Michael Baake, Franz Gähler, Jan Mazáč, and Andrew J. Mitchell",
         title="Diffraction of the Hat and Spectre tilings and some of their relatives",
         arxiv="2502.03268", doi="10.1063/5.0264955",
         note="Exact Fourier-Bohr amplitudes from CAP and CASPr model sets."),
    dict(n=36, authors="Michael Baake, Franz Gähler, Anna Klick, Neil Mañibo, and Jan Mazáč",
         title="Renormalisation techniques for inflation systems and some of their applications",
         arxiv="2606.19645",
         note="Exact renormalization machinery applied to Hat and Spectre diffraction."),
    dict(n=37, authors="Aurélien Mordret and Adolfo G. Grushin",
         title="Beating the aliasing limit with aperiodic monotile arrays",
         arxiv="2408.16476", doi="10.1103/PhysRevApplied.23.034021",
         note="Peer-reviewed finite-array response and synthetic beamforming study; not an image-reconstruction experiment."),
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
         note="Experimental preprint on a finite optically written polariton realization with Bragg peaks and coherence."),
    dict(n=41, authors="Valtýr Kári Daníelsson and Helgi Sigurðsson",
         title="Critical states and anomalous wave transport in an aperiodic polariton monotile",
         arxiv="2605.29023",
         note="Computational preprint and experimental proposal predicting critical states and anomalous transport."),
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
         note="Mathematical construction and computational kinematic checks for identical Spectre-derived blocks; not a structural load experiment."),
    dict(n=51, authors="Hugo Hiu Chak Cheng and Gary P. T. Choi",
         title="Monotile kirigami", arxiv="2604.19586",
         note="Theoretical and computational deployable-kirigami constructions; no reported force, fatigue, or fabrication campaign."),
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
         note="Li-Boyle QECCs extended to Hat and Spectre; local recoverability and SE(2) classical-bit storage."),
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
         note="FEA and Gaussian-process study of aperiodic minimal-surface shells; not conventional TPMS and not experimentally validated."),
    dict(n=61, authors="Sankarganesh P., Vinothkumar G., and P. G. Kubendran Amos",
         title="Evolving Einstein: The instability of aperiodic monotile as a polycrystalline microstructure",
         doi="10.1016/j.mtla.2025.102517",
         note="Phase-field polycrystalline evolution on Hat-family lattice topology."),
    dict(n=62, authors="Amin Montazeri, Mohamad Rahimi, Mohammadreza Maghzi, Iman Ahmadian, and Majid Safarabadi",
         title="Aperiodic ordered lattices with semi Re-entrant einstein monotile",
         doi="10.1016/j.euromechsol.2025.105830",
         note="Mechanical compression, bending, energy-absorption, and Poisson-ratio study of a derivative semi-re-entrant lattice; not a canonical Smith tile."),
    dict(n=63, authors="Sidney Holden and Geoffrey Vasil",
         title="A continuum limit for dense spatial networks",
         arxiv="2301.07086",
         note="Homogenization framework with Hat monotile as a convergence example."),
    dict(n=64, authors="Xinxin Wang, Xinwei Li, Zhendong Li, Zhonggang Wang, and Wei Zhai",
         title="Superior Strength, Toughness, and Damage-Tolerance Observed in Microlattices of Aperiodic Unit Cells",
         doi="10.1002/smll.202307369",
         note="Experimental and simulated monotile-inspired 3D microlattices under compression; derivative geometry."),
    dict(n=65, authors="Xinxin Wang, Zhendong Li, Junjie Deng, Tianyu Gao, Kexin Zeng, Xiao Guo, Xinwei Li, Wei Zhai, and Zhonggang Wang",
         title="Unprecedented Strength Enhancement Observed in Interpenetrating Phase Composites of Aperiodic Lattice Metamaterials",
         doi="10.1002/adfm.202406890",
         note="Experimental Ti-6Al-4V-epoxy interpenetrating composites based on a monotile-inspired truss lattice."),
    dict(n=66, authors="Iestyn Jowers and Richard J. Moat",
         title="What Lies Beneath a Family of Aperiodic Monotilings",
         url="https://archive.bridgesmathart.org/2025/bridges2025-169.html",
         note="Bridges 2025: vertex arrangements and subsidiary polygon systems in the Hat family."),
    dict(n=67, authors="David Richeson",
         title="Fold-and-Cut Lines for the Hat, Turtle, and Spectre Tiles",
         url="https://archive.bridgesmathart.org/2025/bridges2025-567.html",
         note="Bridges 2025 one-cut paper templates; its “Spectre” is straight-edged Tile(1,1), not the strict curved chiral Spectre."),
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
    dict(n=72, authors="Peter Wide and Holger Schellwat",
         title="Position detection of an autonomous robot by aperiodic tilings",
         doi="10.1109/IMTC.1997.604016",
         note="1997 conference antecedent proposing and discussing aperiodic-floor localization; not a modern implemented Hat/Spectre benchmark."),
    dict(n=73, authors="Shigeki Akiyama, Tadahisa Hamada, and Katsuki Ito",
         title="Aperiodic Tile Sets from Sturmian Lattices",
         arxiv="2607.14693",
         note="Constructs infinitely many aperiodic tile sets from quadratic-irrational Sturmian lattices using Ammann bars and bounded-displacement correspondences."),
    dict(n=74, authors="Marcel Krüger",
         title="From Chiral Aperiodic Diffraction to a Falsifiable HLV Optical Benchmark",
         note="Unpublished preregistration protocol (v0.1, 2026). Included for its positive-control, matched-null, holdout, and falsification methodology, not as evidence for HLV."),
    dict(n=75, authors="Michel Duneau and André Katz",
         title="Quasiperiodic patterns", doi="10.1103/PhysRevLett.54.2688",
         note="Peer-reviewed foundational cut-and-project construction using physical/internal projections and acceptance domains."),
    dict(n=76, authors="N. G. de Bruijn",
         title="Algebraic theory of Penrose’s non-periodic tilings of the plane. I, II",
         doi="10.1016/1385-7258(81)90016-0",
         note="Peer-reviewed pentagrid and higher-dimensional coordinate theory; DOI points to Part I of the two-paper treatment."),
]

WEB_RESOURCES = [
    dict(label="Kaplan et al., <em>An aperiodic monotile</em> project page, interactive patch builders, source code, and CC&nbsp;BY sample images",
         url="https://cs.uwaterloo.ca/~csk/hat/"),
    dict(label="Kaplan et al., <em>A chiral aperiodic monotile</em> project page, Tile(1,1) patch app and Spectre SVG outlines for cutting and printing",
         url="https://cs.uwaterloo.ca/~csk/spectre/"),
    dict(label="Printables: Spectre chiral aperiodic monotile, parametric 3D-printable tiles with this-way-up orientation grids",
         url="https://www.printables.com/model/520972-spectre-chiral-aperiodic-monotile"),
    dict(label="National Museum of Mathematics: The Hat and the Spectre, exhibits and the Einstein Mad Hat competition",
         url="https://momath.org/the-hat/"),
    dict(label="Nan Ma, aperiodic-monotile-4d, original Wolfram Language code and projection experiments (no license; link only)",
         url="https://github.com/nanma80/aperiodic-monotile-4d"),
    dict(label="Arnaud Chéritat and Nan Ma, interactive 4D projection applet, CC BY-SA",
         url="https://www.math.univ-toulouse.fr/~cheritat/AppletsDivers/Monotile-4D-lift/3-outlines/"),
    dict(label="Simon Tatham, Combinatorial Coordinates for the Aperiodic Spectre Tiling",
         url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-spectre/"),
    dict(label="Christian Lawson-Perfect et al., multi-format monotile assets, CC0 SVG, DXF, OpenSCAD, and STL",
         url="https://github.com/christianp/aperiodic-monotile"),
    dict(label="Infinite Spectres, MIT-licensed Rust/WebGPU deep-zoom viewer",
         url="https://github.com/necocen/spectre"),
    dict(label="Tilings Encyclopedia: Spectre, institutional patch and reference record",
         url="https://tilings.math.uni-bielefeld.de/substitution/spectre/"),
    dict(label="Large Spectre Tiling, 488-piece hierarchical group activity",
         url="https://www.gathering4gardner.org/large-spectre-tiling/"),
    dict(label="Terracing with Spectres, built CNC-waterjet limestone terrace and process archive",
         url="https://anarchive.fo.am/silver/spectres/"),
    dict(label="Hats in Grout, practical fabrication and installation geometry",
         url="https://archive.bridgesmathart.org/2024/bridges2024-389.html"),
    dict(label="OEIS A363348, recursive turn sequence for drawing an infinite Hat tiling",
         url="https://oeis.org/A363348"),
]

WEB_RESOURCE_SECTIONS: list[tuple[str, list[dict]]] = [
    ("Official project pages and discoverer accounts", [
        dict(label="Kaplan, <em>Aperiodic Monotiles</em>, discovery chronology and community links",
             url="https://isohedral.ca/aperiodic-monotiles/"),
        dict(label="David Smith, Hedraweb, discoverer blog and physical experiments",
             url="https://hedraweb.blogspot.com/"),
        dict(label="David Smith, <em>The Special One</em>, first-person Tile(1,1) / Spectre story",
             url="https://hedraweb.wordpress.com/2023/06/02/the-special-one/"),
        dict(label="Joseph Myers, publications and preprints",
             url="https://www.polyomino.org.uk/publications/"),
        dict(label="Chaim Goodman-Strauss, papers and notes",
             url="https://chaimgoodmanstrauss.com/papers/"),
        dict(label="Combinatorial Theory, Hat paper (open access)",
             url="https://doi.org/10.5070/c64163843"),
        dict(label="Combinatorial Theory, Spectre paper (open access)",
             url="https://doi.org/10.5070/c64264241"),
    ]),
    ("Generators, code, and datasets", [
        dict(label="isohedral/hatviz, official Hat patch builder (BSD-3-Clause)",
             url="https://github.com/isohedral/hatviz"),
        dict(label="isohedral/hatvalidate, computer-assisted aperiodicity verification",
             url="https://github.com/isohedral/hatvalidate"),
        dict(label="henningle/TileOneOne, reference Tile(1,1) MATLAB generator (MIT)",
             url="https://github.com/henningle/TileOneOne"),
        dict(label="jsm28/AperiodicMonotilesLean, Lean formalization staging repo",
             url="https://github.com/jsm28/AperiodicMonotilesLean"),
        dict(label="reversi-fun/symbolic-spectre-tiles, symbolic coordinates and CSV/SVG export (MPL-2.0)",
             url="https://github.com/reversi-fun/symbolic-spectre-tiles"),
        dict(label="ctkrug/monotile, infinite Spectre pan/zoom studio",
             url="https://apps.charliekrug.com/monotile/"),
        dict(label="Ricky Reusser, WebGPU aperiodic monotile rendering notebook",
             url="https://rreusser.github.io/notebooks/aperiodic-monotile/"),
        dict(label="Ricky Reusser, deep-zoom aperiodic monotile notebook",
             url="https://rreusser.github.io/notebooks/zooming-aperiodic-monotile/"),
        dict(label="James Smith, AperiodicCube 3D interactive demo",
             url="https://jpdsmith.github.io/AperiodicCube/"),
        dict(label="Simon Tatham, coordinate algorithms for Hat tilings",
             url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-tilings/"),
        dict(label="Simon Tatham, finite-state transducers for Hat and Spectre",
             url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-transducers/"),
        dict(label="Simon Tatham, refinable frontier (H7/H8 and Spectre hex types)",
             url="https://www.chiark.greenend.org.uk/~sgtatham/quasiblog/aperiodic-refine/"),
        dict(label="Jaap Scherphuis, PolyForm Puzzle Solver (discovery-era search tool)",
             url="https://www.jaapsch.net/puzzles/polysolver.htm"),
        dict(label="Spectre Tiling Playground, manual editor with TILE coordinate format",
             url="https://bnaskrecki.faculty.wmi.amu.edu.pl/spectre/"),
        dict(label="Beach Spectre Practise, touch-friendly substitution trainer",
             url="https://beach-spectre-practise.think.somethingorotherwhatever.com/"),
    ]),
    ("Institutional references and OEIS", [
        dict(label="Tilings Encyclopedia, Hat substitution record",
             url="https://tilings.math.uni-bielefeld.de/substitution/hat/"),
        dict(label="Tilings Encyclopedia, CAP representative",
             url="https://tilings.math.uni-bielefeld.de/substitution/cap/"),
        dict(label="Tilings Encyclopedia, aperiodic monotile glossary",
             url="https://tilings.math.uni-bielefeld.de/glossary/aperiodic-monotile/"),
        dict(label="OEIS A363445, Hat perimeter fractal turn sequence",
             url="https://oeis.org/A363445"),
        dict(label="OEIS A397115-A397123, Spectre hierarchical cluster counts (2026)",
             url="https://oeis.org/A397115"),
    ]),
    ("Museums, competitions, and workshops", [
        dict(label="UKMT Einstein Mad Hat Awards, competition archive",
             url="https://ukmt.org.uk/hat-awards"),
        dict(label="Hatfest, Oxford / Grimm Network conference archive",
             url="https://sites.google.com/view/thegrimmnetwork/hatfest"),
        dict(label="Cambridge Faculty of Mathematics, Tip of the Hat celebration",
             url="https://www.maths.cam.ac.uk/features/tip-hat-celebrating-aperiodic-monotile-discovery"),
        dict(label="Marcello Seri, Spectres, Hats and Maths workshop kits (CC BY 4.0)",
             url="https://academic.mseri.me/pe.htm"),
        dict(label="Bridges 2024, Group activity to build a Spectre tiling",
             url="https://archive.bridgesmathart.org/2024/bridges2024-385.html"),
        dict(label="Numberphile, Discovery of the Aperiodic Monotile",
             url="https://www.youtube.com/watch?v=_ZS3Oqg1AX0"),
        dict(label="Quanta, Hobbyist finds maths elusive Einstein tile",
             url="https://www.quantamagazine.org/hobbyist-finds-maths-elusive-einstein-tile-20230404/"),
    ]),
    ("Fabrication, installations, and products", [
        dict(label="Beach Spectres, public sand-tiling project and how-to guides",
             url="https://beachspectres.com/"),
        dict(label="Printables, Einstein Tiles family (Hat, Tile(1,1), Spectre variants)",
             url="https://www.printables.com/model/574374-einstein-tiles-original-and-chiral"),
        dict(label="Spirko/SpectreOpenSCAD, parametric Spectre STL generator (GPL-3.0)",
             url="https://github.com/Spirko/SpectreOpenSCAD"),
        dict(label="vmagnin/hat_polykite, laser-cut Hat and Tile(1,1) sheets",
             url="https://github.com/vmagnin/hat_polykite"),
        dict(label="Nervous System, wooden Spectre puzzle (111 pieces)",
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
        note = f' <span class="ref-note">. {html.escape(r["note"])}</span>' if r["note"] else ""
        href = (
            f"https://doi.org/{r['doi']}" if r.get("doi")
            else f"https://arxiv.org/abs/{r['arxiv']}" if r.get("arxiv")
            else r.get("url")
        )
        identifier = (
            f" DOI:{r['doi']}." if r.get("doi")
            else f" arXiv:{r['arxiv']}." if r.get("arxiv")
            else ""
        )
        title = (
            f'<a href="{href}" rel="noopener noreferrer">{html.escape(r["title"])}</a>'
            if href
            else f'<span>{html.escape(r["title"])}</span>'
        )
        items.append(
            f'<li id="ref-{r["n"]}">{authors}{title}.'
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
    "silhouettes, straight polygon, jagged, wavy, stepped, scalloped, and rounded forms. All tile the same "
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
    ", the same real generated patch read as texture at a distance and as individual tiles up close. "
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
    "(left) repeats identically in every direction; the Spectre floor (right) is equally ordered but has no "
    "translational repeat. Finite motifs may recur. Both are real geometry: an equal-area hex grid and a generated "
    "Tile(1,1) patch.",
    width=2048,
)
FIG_CG_SUNSET = fig(
    "computer-graphics-sunset.jpg",
    "Aperiodic monotile floor at sunset with terracotta tones stretching to the horizon",
    "<strong>Environmental scatter.</strong> Eye-height procedural ground plane, aperiodic monotile "
    "instances with warm PBR materials, useful for scenes that need ordered but non-repeating structure.",
    width=1400,
)
FIG_CG_BRASS = fig(
    "computer-graphics-brass.jpg",
    "Brass aperiodic monotile relief panel with beveled edges and dramatic lighting",
    "<strong>Material and lighting study.</strong> Instanced monotile meshes with metallic shading, "
    "the same patch data drives real-time previews, offline renders, and exported GLB assets.",
    width=1400,
)
FIG_CG_HILLS = fig_video(
    "rolling-hills-moon.mp4",
    "<strong>Rolling terrain, one tile.</strong> Eye-height walk across a curvy monotile landscape under "
    "moonlight, the same generated patch language used for production scenes. "
    f'<a href="{ASSET}/rolling-hills-hero.png">Hero still</a>',
    poster="rolling-hills-moon.jpg",
)
FIG_CG_FALCOR = fig_video(
    "falcor-city.mp4",
    "<strong>City-scale instancing.</strong> A Spectre-city flythrough built from deterministic tile "
    "transforms, one outline, no translational wallpaper.",
    poster="falcor-city.jpg",
)
FIG_CG_ORBIT = fig_video(
    "hill-orbit.mp4",
    "<strong>Orbit study.</strong> Camera circle around a single curvy monotile hill, useful for lighting "
    "and silhouette checks before locking a hero shot.",
    poster="hill-orbit.jpg",
)
FIG_CG_BALL = fig_video(
    "ball-roll.mp4",
    "<strong>Contact and bounce.</strong> A reflective ball rolling on monotile terrain, the layout stays "
    "seed-stable while motion reads the surface continuously.",
    poster="ball-roll.jpg",
)
FIG_CG_LUMEN = fig_video(
    "lumen-vault.mp4",
    "<strong>Lumen Vault.</strong> Slow orbit of an iridescent circular patch of curvy Spectre tiles, "
    "real API geometry, Blender EEVEE materials. Also on the "
    '<a href="../../art.html">art page</a>.',
    poster="lumen-vault.jpg",
)
FIG_CG_INK = fig_video(
    "ink-gold.mp4",
    "<strong>Ink &amp; Gold.</strong> Wet lacquer Spectre disc with molten gold seams and leaf inlays, "
    "raking light sweep over real API geometry. Also on the "
    '<a href="../../art.html">art page</a>.',
    poster="ink-gold.jpg",
)
FIG_DESIGN_HILLS = fig(
    "rolling-hills-hero.png",
    "Curvy aperiodic monotile hills as a landscape still",
    "<strong>Landscape still.</strong> A generated curvy-edge monotile field as environmental design "
    "reference, also on the "
    '<a href="../../art.html">art page</a>.',
    width=1400,
)
FIG_DESIGN_CERAMIC = fig_video(
    "ceramic-dusk.mp4",
    "<strong>Ceramic dusk POV.</strong> Ground-level walk across a glazed monotile floor at dusk, "
    "material and palette as data on fixed geometry.",
    poster="ceramic-dusk.jpg",
)
FIG_WAVE_PROP = fig_video(
    "wave-propagation.mp4",
    "<strong>Wavefront across a monotile lattice.</strong> A luminous crest expands tile-by-tile through a "
    "generated patch, the medium stays visible so you can watch the wave move, not just light rings in "
    "black space.",
    poster="wave-propagation.jpg",
)
FIG_IMPACT_FRONT = fig_video(
    "impact-front.mp4",
    "<strong>Normal impact on a monotile sheet.</strong> Schematic slow-motion: a punch opens a hole and a "
    "stress/energy ring races outward through interlocking cells. Illustration for energy-absorption and "
    "impact-mitigation research interest, not a measured crash test.",
    poster="impact-front.jpg",
)
FIG_IMPACT_OBLIQUE = fig_video(
    "impact-oblique.mp4",
    "<strong>Oblique impact.</strong> Same schematic sheet, angled strike, the disturbed neighborhood and "
    "outgoing ring stay readable on the aperiodic mesh.",
    poster="impact-oblique.jpg",
)
FIG_IMPACT_LATERAL = fig_video(
    "impact-lateral.mp4",
    "<strong>Lateral slice.</strong> Cutaway of the same impact sequence, emphasizing how deformation and "
    "the outgoing wave occupy neighboring cells rather than a single lattice corridor.",
    poster="impact-lateral.jpg",
)
FIG_ROBOTICS_POSE = fig(
    "robotics-pose-lookup-redraw.png",
    "Side-by-side: periodic floor FOV is ambiguous versus aperiodic floor FOV that maps to a unique pose",
    "<strong>Where am I?</strong> A downward camera on a checkerboard sees a neighborhood that could be "
    "anywhere. On a generated monotile floor, the same FOV highlights a unique neighborhood that can look "
    "up pose in a regenerable map.",
    width=1400,
)
FIG_EDU_HOLD_GROW = fig(
    "education-hold-and-grow-redraw.png",
    "One hand-held tile leading to a color-coded substitution hierarchy cluster",
    "<strong>Hold one tile, grow the hierarchy.</strong> Classroom story: start with a single cutout, then "
    "assemble the same substitution clusters used in proofs and museum builds.",
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
    "a palette change is a data change, the geometry, grout lines, and layout never move.",
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
    "colored by angle, the kind of demo that makes a classroom lean in. Every tile is the same shape; the "
    "pattern still never repeats.",
    width=1600,
)
FIG_EDUCATION = fig(
    "education-colorful-patch.png",
    "Colorful labeled aperiodic monotile patch for classroom demonstration",
    "<strong>Classroom patch.</strong> Deterministic color per tile, ideal for posters, museum panels, "
    "and puzzles that show order without translational repetition.",
    width=1400,
)
FIG_SIGNAL = fig(
    "signal-processing-sampling.png",
    "Tile centroids as a deterministic non-periodic sampling layout",
    "<strong>Sampling layout.</strong> Each tile centroid is a reproducible sample point, an alternative "
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
FIG_PHYSICS_DIFFRACTION = fig(
    "physics-diffraction-blender-redraw.png",
    "Original three-dimensional redraw of a Hat-centroid hole array beside a twisted sixfold diffraction pinwheel",
    "<strong>Hat-centroid diffraction.</strong> Original Blender reconstruction of the experimental concept "
    "in ref.&nbsp;19: a membrane punctured at tile centroids and a schematic sixfold pinwheel with the "
    "reported 15.52° twist. Not a reproduction of the published photograph or diffraction image.",
    width=1600,
)
FIG_PHYSICS_DIMERS = fig(
    "physics-dimers-blender-redraw.png",
    "Original three-dimensional redraw of a regularized Spectre dimer graph with free Mystic choices highlighted",
    "<strong>Exact dimer counting.</strong> Original Blender reconstruction of the regularized bipartite "
    "Spectre graph from ref.&nbsp;22. Forced dimers are pale; free Mystic choices glow. The exact count "
    "Z=2<sup>N<sub>Mystic</sub>+1</sup> is combinatorial, not a measured material property.",
    width=1600,
)
FIG_PHYSICS_ARRAYS = fig(
    "physics-arrays-centroid-redraw.png",
    "Same-square-aperture comparison of a filled regular sensor grid and real Hat/Spectre tile centroids with schematic array responses",
    "<strong>Same FOV, no blind corners.</strong> Top: both layouts fill the gold dashed square aperture "
    "at equal count, an <em>n</em>×<em>n</em> lattice versus actual Tile(1,1) centroids from a generated "
    "patch. Bottom: schematic far-field responses. Aliases are redistributed, not erased. Not a Blender "
    "sculpture and not a traced paper plot.",
    width=1400,
)
FIG_MATH_SPECTRE_CLUSTERS = fig(
    "substitution-hierarchy-still.png",
    "Color-coded Hat substitution hierarchy showing clustered metatile superclusters",
    "<strong>Substitution hierarchy.</strong> Color-coded metatile clusters in a Hat patch, the hierarchy "
    "that forces structure on unbounded scales. Same still as the hierarchy animation.",
    width=1400,
)
FIG_MATERIALS_SCIENCE = fig(
    "materials-science-lattice.png",
    "Metallic aperiodic lattice visualization for metamaterial studies",
    "<strong>Lattice candidate.</strong> Controlled non-periodic pore and strut layouts for metamaterials, "
    "electrodes, exchangers, and porous-media experiments.",
    width=1400,
)
FIG_MATERIALS_COMPRESSION = fig(
    "materials-compression-blender-redraw.png",
    "Original three-dimensional redraw of a finite monotile wall network compressed between rigid platens",
    "<strong>Finite compression specimen.</strong> Original Blender reconstruction of the test concept in "
    "ref.&nbsp;42: a cropped monotile-derived wall network between compression platens. It is an explanatory "
    "redraw, not the paper’s specimen photograph or a calibrated mechanical simulation.",
    width=1600,
)
FIG_MATERIALS_CONVERGENCE = fig(
    "materials-convergence-blender-redraw.png",
    "Three increasingly large circular monotile networks representing a scale-dependent continuum study",
    "<strong>Scale changes the question.</strong> Original Blender reconstruction of the domain-size sweep "
    "in ref.&nbsp;43. The rendered networks illustrate 10<em>a</em>, 100<em>a</em>, and 300<em>a</em> "
    "domains; the published anisotropy values come from simulation, not from this rendering.",
    width=1600,
)
FIG_MATERIALS_FRACTURE = fig_video(
    "materials-fracture-blender-redraw.mp4",
    "<strong>Notched multiphase panel.</strong> Original Blender reconstruction of the architecture and "
    "failure mechanism studied in ref.&nbsp;46. Rigid tile cores sit in a continuous soft phase; the glowing "
    "line is a schematic tortuous crack growing under tension, not copied experimental data. "
    f'<a href="{ASSET}/materials-fracture-blender-redraw.png">Still frame</a>',
    poster="materials-fracture-blender-redraw.png",
)
FIG_MATERIALS_INTERLOCKING = fig_video(
    "materials-interlocking-blender-redraw.mp4",
    "<strong>Derivative interlocking interface.</strong> Original Blender reconstruction of the mechanism "
    "discussed in ref.&nbsp;49, redrawn with a flat-top bulb / undercut dovetail profile. The animation "
    "separates complementary necks and heads; this boundary is engineered, not a canonical Hat or Spectre edge. "
    f'<a href="{ASSET}/materials-interlocking-blender-redraw.png">Still frame</a>',
    poster="materials-interlocking-blender-redraw.png",
)
FIG_ROBOTICS_HORIZON = fig(
    "robotics-horizon-walk.jpg",
    "Eye-height view over an aperiodic monotile ground plane stretching to a sunset horizon",
    "<strong>A ground plane with no translational period.</strong> An eye-height camera over a generated "
    "monotile terrain. Finite motifs still recur, but within a fixed mapped patch a sufficiently large "
    "visible neighborhood can identify position, something a periodic grid cannot do.",
    width=1600,
)
FIG_BIOLOGY = fig(
    "biology-scaffold-patch.png",
    "Soft pastel aperiodic packing pattern as a geometric scaffold",
    "<strong>Geometric scaffold.</strong> Clean packing layouts for exploring cellular, branching, and "
    "surface-constrained design questions, not biological models by default.",
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
    "produces large rosette cells with a strong central focal point, a moiré landscape that feels "
    "dimensional even though it is a flat 2D beat pattern. "
    f'<a href="{ASSET}/aperiodicmoire.png">Full resolution</a>',
    width=320,
    side="left",
)
FIG_MOIRE_60DEG = fig(
    "aperiodicrivers-web.png",
    "Phason rivers at 60° rotation: winding moiré channels across layered aperiodic arrays",
    "<strong>60° rotation.</strong> The same layered arrays with a 60° relative twist. Interference "
    "concentrates into jagged, river-like channels, phason rivers, that cross the field in broad "
    "horizontal and vertical strokes. "
    f'<a href="{ASSET}/aperiodicrivers.png">Full resolution</a>',
    width=1400,
)
FIG_ALIAS_COVER = fig_thumb(
    "aliasing-cover-web.jpg",
    "Dense checker-like landscape with strong sampling and aliasing artifacts",
    "<strong>Aliasing on a periodic lattice.</strong> When high-frequency regular structure meets "
    "limited resolution, a camera, a screen, a texture sampler, false low-frequency patterns appear. "
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
        summary="The aperiodic monotile research wiki, concepts, mathematics, and application frontiers.",
        categories=["Research"],
        is_main=True,
        sections=[
            Section(
                "Welcome",
                2,
                f"""
<p>
  Welcome to the <strong>Aperiodic Monotile Research Wiki</strong>, a field guide to the geometry,
  mathematics, and emerging applications of aperiodic monotiles, single shapes that tile the plane
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
  <li>{link("aperiodic-monotile", "Aperiodic monotile")}, the core definition and why it matters</li>
  <li>{link("moire", "Moiré")}, layered arrays, phason rivers, and navigable beat patterns</li>
  <li>{link("aliasing", "Aliasing")}, sampling artifacts, periodic risk, and monotile resistance</li>
  <li>{link("spectre-tile", "Spectre tile")}, the strictly chiral monotile discovered in 2023</li>
  <li>{link("hat-tile", "Hat tile")}, the first aperiodic monotile, March 2023</li>
  <li>{link("substitution-tiling", "Substitution tiling")}, how one tile grows into an infinite hierarchy</li>
  <li>{link("diffraction-and-dynamical-spectrum", "Diffraction and dynamical spectrum")}, from correlations to Bragg and continuous components</li>
  <li>{link("cut-and-project-and-model-sets", "Cut-and-project schemes")}, windows, internal space, CAP, and CASPr</li>
  <li>{link("sturmian-lattices", "Sturmian lattices")}, balanced words, Ammann bars, Nuts, and Bolts</li>
  <li>{link("discovery-history", "Discovery history")}, dated physical, computational, and proof milestones</li>
  <li>{link("computational-generation", "Computational generation")}, exact coordinates, navigation, rendering, and validation</li>
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
  <li>{link("dimers-and-constrained-models", "Dimers and constrained models")}</li>
</ul>
""",
            ),
            Section(
                "Reading paths",
                2,
                f"""
<ul class="wiki-feature-list">
  <li><strong>Newcomer:</strong> {link("aperiodic-monotile", "Aperiodic monotile")} →
  {link("hat-tile", "Hat tile")} → {link("spectre-tile", "Spectre tile")} →
  {link("substitution-tiling", "Substitution tiling")} → {link("discovery-history", "Discovery history")}.</li>
  <li><strong>Designer or maker:</strong> {link("design-and-architecture", "Design, art, and architecture")} →
  {link("materials-and-fabrication", "Materials and fabrication")} →
  {link("computer-graphics", "Computer graphics")} → {link("resources-and-tools", "Resources and tools")}.</li>
  <li><strong>Researcher:</strong> choose {link("signal-processing", "sampling")},
  {link("waves-and-photonics", "wave physics")}, {link("materials-science", "materials")},
  {link("robotics-and-mobility", "robotics")}, {link("biology-and-medicine", "biology")}, or
  {link("algorithms-and-machine-learning", "algorithms")}; continue through
  {link("diffraction-and-dynamical-spectrum", "diffraction")}, {link("cut-and-project-and-model-sets", "model sets")},
  or {link("sturmian-lattices", "Sturmian lattices")}. Each article separates published evidence from
  candidate experiments and links to the numbered {link("bibliography", "bibliography")}.</li>
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
  Three terms are easy to confuse. A <strong>monotile</strong> is one shape used to cover the plane.
  A <strong>monohedral non-periodic tiling</strong> is one particular non-repeating arrangement of one
  shape, even if that shape also permits a repeating arrangement. An <strong>aperiodic monotile</strong>
  is stronger: congruent copies cover the plane, but <em>no</em> valid tiling has translational
  periodicity.{cite(1)}{cite(3)}
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
  at all. Recent work continues to map where the boundary of decidability lies, translational tiling
  is undecidable for three connected polyhypercubes in four dimensions,{cite(24)} translational monotiles are undecidable in
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
  quasicrystalline, sharp peaks, like a crystal, but with symmetries no crystal can have.{cite(6)}
</p>
<p>
  For practical work, a chosen substitution construction can regenerate a patch, scale it, and export
  stable tile IDs. That gives a reproducible geometric dataset rather than random noise. Aperiodicity does
  <em>not</em> mean that every small neighborhood is unique: finite motifs recur. Within one fixed finite
  patch, however, a sufficiently large local neighborhood can identify position, which is useful for
  experiments in localization and indexing. Those are engineering opportunities, not consequences proved
  for every sensor or every generated patch.
</p>
{FIG_TILING_ARRAY}
""",
            ),
            Section(
                "Weak vs strict chirality",
                2,
                f"""
<p>
  The Hat tile is asymmetric: every Hat tiling contains mostly one handedness and a smaller, required
  population of reflected copies. Standard tiling terminology normally allows every rigid motion,
  including reflection, when it calls two copies congruent; a fabrication process with decorated faces
  may nevertheless have to treat the two handed parts as distinct products.{cite(1)}{cite(3)}
</p>
<p>
  The Spectre tile closed the question. Tile(1,1) is <em>weakly</em> chiral, banning reflections by rule
  leaves only non-periodic tilings, and its curved-edge Spectre variants are <em>strictly</em> chiral: the
  geometry itself makes reflected copies unusable, so only single-handed non-periodic tilings exist.{cite(2)}
  That distinction matters physically. A glazed ceramic tile or other one-sided part may not be usable
  face-down. A homochiral layout can reduce part variants, but it does not by itself determine tooling cost
  or prevent installation errors; edge keys, markings, tolerances, and the selected patch still matter.
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
  with a single shape and can form striking non-periodic arrangements, often spiral or ring-like,
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
            Section(
                "Evidence, use, and limits",
                2,
                f"""
<p>
  The established result is mathematical: the Hat and Spectre papers prove that valid infinite tilings
  exist and that periodic ones are excluded under their stated congruence and reflection rules.{cite(1)}{cite(2)}
  The proof strategy is not “the patch looks irregular.” It converts tiles into a finite collection of
  labeled clusters or metatiles, proves that every tiling must decompose into those larger units, and repeats
  that decomposition at arbitrarily large scales. A finite translation period cannot survive that forced
  hierarchy. Independent proofs and direct constructions check the conclusion by different routes.{cite(4)}{cite(5)}
</p>
<p>
  Finite exports are samples of an infinite system, so clipping a patch can hide hierarchy and create
  boundary fragments. Claims about strength, optics, localization, or visual quality require separate
  controls; aperiodicity alone proves none of them. The practical value is a precisely specified,
  non-periodic geometry on which those questions can be tested.
</p>
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
        see_also=["aperiodic-monotile", "hat-tile", "substitution-tiling", "discovery-history",
                  "diffraction-and-dynamical-spectrum"],
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
  The <strong>Spectre</strong> is a 14-sided equilateral polygon, Tile(1,1) in the Hat's shape continuum,
  that tiles the plane aperiodically using only translations and rotations. No reflected tiles are needed,
  and in the strict curved-edge form, none are even possible. It was introduced in <em>A chiral aperiodic
  monotile</em> as the solution to the "vampire einstein" problem: an aperiodic monotile that casts no
  mirror image.{cite(2)}
</p>
{FIG_TILE_VARIANTS}
<p>
  The straight-edged Tile(1,1) is subtle: allowed reflections give it a simple periodic tiling, so it is
  only aperiodic when reflections are forbidden by rule (<em>weakly chiral</em>). Modifying its edges with
  matching curves, any of the variant silhouettes above, removes that escape hatch and produces the
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
  proof techniques, including Akiyama and Araki's alternative argument, confirmed aperiodicity through
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
  up the hierarchy. Public tooling, Kaplan's
  <a href="https://cs.uwaterloo.ca/~csk/spectre/" rel="noopener noreferrer">Spectre explorer</a> and
  community ports, implements these rules for interactive exploration.{cite(2)}
</p>
{FIG_HIERARCHY}
<p>
  The Aperiodic Monotile API packages this mathematics for production workflows: clipped patches,
  stable tile IDs and transforms, and exporters (SVG, STL, GLB, CSV, JSON), the exact pipeline used to
  produce the renders across this wiki.
</p>
""",
            ),
            Section(
                "What the chiral theorem proves",
                2,
                f"""
<p>
  The proof concerns mathematically exact tiles and allowed rigid motions. Local fits force a small family
  of larger clusters, and recognizability lets those clusters be recovered at every scale. A translational
  period cannot survive this unbounded hierarchy. Reflection creates the opposite-handed tiling space; it
  is not an orientation required inside one strict Spectre tiling.{cite(2)}
</p>
<p>
  A one-monotile theorem can still require many decorated substitution states. Those labels remember
  orientation, local role, and parent boundary so that hierarchy is recognizable; they are bookkeeping
  states, not extra physical tile shapes. Straight polygonal encodings with matching marks are useful for
  software but must not be substituted silently for the exact unmarked curved geometry.
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
  dense field of turtles, and vice versa, the three descriptions morph continuously into each other.
  Kaplan's historical survey traces the whole path from Penrose tiles to these modern monotiles.{cite(3)}
  Wang-tile machinery provides yet another route to both shapes.{cite(7)}
</p>
<p>
  Family members can share combinatorial adjacency while differing metrically. Moving through
  Tile(<em>a,b</em>) changes distances, angles, clearances, diffraction peak locations, and physical
  couplings. A theorem preserved under the family deformation does not make every Euclidean or material
  observable identical.
</p>
""",
            ),
            Section(
                "Evidence and limitations",
                2,
                f"""
<p>
  Aperiodicity and chirality are established by the substitution and combinatorial arguments in the
  discovery paper.{cite(2)} Diffraction is a different observable: it describes how a point decoration or
  fabricated lattice scatters waves. Theory predicts pure-point long-range order for CASPr
  representatives,{cite(32)} crystallographic work finds non-periodic chiral sixfold diffraction,{cite(34)}
  while a fabricated Hat-centroid quasilattice has produced handed optical response.{cite(19)}
</p>
<p>
  Results depend on what is placed on the tiling, vertices, centroids, resonators, edges, or material
  domains, and on finite-patch boundaries. The straight Tile(1,1) polygon must not be described as strictly
  aperiodic when reflections are allowed. Nor does one successful optical experiment establish benefits
  for acoustics, mechanics, graphics, or antennas; those require their own baselines and measurements.
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
        see_also=["aperiodic-monotile", "spectre-tile", "discovery-history",
                  "diffraction-and-dynamical-spectrum"],
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
                "What the Hat is",
                2,
                f"""
<p>
  The <strong>Hat</strong> is an asymmetric polykite, eight kites carved from a hexagonal grid, that
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
                "Geometry and the proof idea",
                2,
                f"""
<p>
  A <strong>polykite</strong> is a shape assembled edge-to-edge from kites in a regular kite grid. The
  Hat uses eight such kites, so its outline inherits a small set of edge directions and lengths. It belongs
  to the two-parameter Tile(<em>a,b</em>) family: changing the two edge scales deforms the outline while
  preserving the combinatorial pattern; the Hat is Tile(1,√3), the Turtle is Tile(√3,1), and Tile(1,1)
  leads to the Spectre construction.{cite(1)}{cite(2)}
</p>
<p>
  The proof forces any Hat tiling to group into a finite set of labeled metatiles. Those metatiles in turn
  form larger copies of the same labeled system. Repeating this grouping creates structure on unbounded
  scales, contradicting any fixed translation period.{cite(1)} An independent proof and a direct
  construction provide useful checks on that hierarchy-based account.{cite(4)}{cite(5)}
</p>
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
  substrate for model systems. Its tilings have quasicrystalline diffraction structure, sharp Bragg-like
  peaks with symmetries forbidden to periodic crystals.{cite(6)} Exact diffraction theory now places Hat
  tilings in CAP cut-and-project model sets with computable Fourier-Bohr amplitudes,{cite(31)}{cite(35)}
  while crystallographic analysis shows vertex diffraction riding on an underlying periodic
  framework.{cite(33)} A nearest-neighbor tight-binding model on the Hat vertex graph shows graphene-like
  features, chirality, and exact zero modes under ideal equal hopping; it is not a vibrational
  experiment.{cite(20)} Statistical
  mechanics has been worked directly on the tiling: the Ising model on the Hat lattice{cite(21)} and dimer
  models on the Spectre tiling{cite(22)} both reveal how aperiodic adjacency changes collective behavior.
  For anyone designing materials, these papers are the evidence base that monotile geometry is not just
  decoration in those models. They do not imply that every Hat-shaped material has improved performance.
</p>
<p>
  Ref.&nbsp;20 first chooses a graph and Hamiltonian: one orbital on each selected Hat vertex with ideal
  nearest-neighbor hopping. A honeycomb approximant covers about 53% of vertices and reproduces Dirac-like
  structure near E≈−0.2t. One H2 patch has eight exact zero modes at zero flux and 22 at half flux, but
  unequal hopping, boundaries, and finite size can move or broaden them.{cite(20)} The Ising study instead
  uses the underlying kite graph, reaches 939,201 spins, and reports T<sub>c</sub>/J=2.405±0.0005 with
  ordinary two-dimensional Ising scaling.{cite(21)}
</p>
""",
            ),
            Section(
                "What is established and what is not",
                2,
                f"""
<p>
  Established results include the Hat’s forced aperiodicity with reflected copies, its substitution
  structure, and rigorous long-range-order descriptions for related CAP representatives.{cite(1)}{cite(31)}
  Physical papers cited here specify particular graphs, point sets, or honeycomb constructions; their
  conclusions should not be transferred to an arbitrary decorative Hat pattern.
</p>
<p>
  Open practical questions include boundary design, defect tolerance, finite-size convergence, and which
  Tile(<em>a,b</em>) member best serves a given load or wavelength. A laser-cut puzzle demonstrates
  manufacturability, not mechanical or wave performance. Those claims need matched periodic, random, and
  alternative aperiodic controls.
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
        see_also=["aperiodic-monotile", "spectre-tile", "computational-generation",
                  "sturmian-lattices", "cut-and-project-and-model-sets"],
        infobox={
            "Used by": "Spectre, Hat, Penrose systems",
            "Output": "Deterministic tile placements",
            "Key idea": "Inflation / deflation rules",
            "Tile counts": "Fibonacci-Lucas growth",
        },
        sections=[
            Section(
                "How substitution works",
                2,
                f"""
<p>
  A <strong>substitution rule</strong> is a geometric recipe: replace one labeled large shape with a fixed
  patch of smaller labeled shapes. Reading the recipe from large to small is <strong>deflation</strong>;
  rescaling the small patch back up and grouping it as one larger unit is <strong>inflation</strong>.
  A <strong>metatile</strong> is one of those labeled groups. Labels record roles or orientations that the
  bare outline may not reveal.{cite(2)}{cite(3)}
</p>
{FIG_HIERARCHY}
<p>
  In the Spectre construction, a finite family of labeled clusters combines into larger clusters and then
  repeats that hierarchy indefinitely.{cite(2)}{cite(10)} The animation shows a finite rendering of that
  idea. Substitution is not automatically a proof of aperiodicity: one must also show that legal tilings
  are forced to admit the hierarchy and that the hierarchy rules out a translation period.
</p>
""",
            ),
            Section(
                "Structure inside the hierarchy",
                2,
                f"""
<p>
  The hierarchy is quantitative. For the homochiral Spectre construction, writing
  <em>N</em><sub>Γ</sub> and <em>N</em><sub>Ω</sub> for eight- and nine-tile cluster counts, one
  generation acts by the 2×2 inflation
</p>
<p class="wiki-equation">
  (<em>N</em><sub>Γ</sub>, <em>N</em><sub>Ω</sub>) ↦
  (<em>N</em><sub>Γ</sub>+<em>N</em><sub>Ω</sub>,
  6<em>N</em><sub>Γ</sub>+7<em>N</em><sub>Ω</sub>).
</p>
<p>
  The Perron root is 4+√15≈7.873, and the asymptotic Ω:Γ ratio is the same value.{cite(10)} Six
  orientations of each cluster give twelve metatile states.
</p>
{FIG_MATH_SPECTRE_CLUSTERS}
<p>
  Independently, Hat-family supervectors
  obey <em>V</em><sub>n</sub>=3<em>V</em><sub>n−1</sub>−<em>V</em><sub>n−2</sub> and, for the
  normalized Hat, <em>V</em><sub>n</sub>=(<em>F</em><sub>2n</sub>, √3 <em>L</em><sub>2n</sub>), so
  Fibonacci and Lucas counts appear as concrete coordinates rather than slogans.{cite(12)} Spectre
  tilings also decompose into triangular hex-clusters of 1, 3, or 6 hexagons dual to the H8/H9
  hierarchy,{cite(11)} and the whole system embeds in a rhombic framework shared by the Hat and
  Turtle.{cite(8)}
</p>
<p>
  Substitution systems can even be built from overlapping iterated function systems, connecting tilings
  to fractal geometry.{cite(14)} Sturmian sequences, the one-dimensional cousins of aperiodic order,
  provide lattice models with closely related structure.{cite(13)} A newer construction starts from three
  families of Ammann-bar lines whose short and long gaps follow balanced Sturmian words. Irrational slope
  removes translational periods; for every quadratic irrational slope, the authors construct an aperiodic
  tile set whose expansion factor is a unit of the corresponding real quadratic field.{cite(73)} Ref.&nbsp;73
  is a concise note whose complete classification and proofs point back to ref.&nbsp;13; the two should not
  be read as independent corroboration. The construction produces finite <em>tile sets</em>, not new
  single aperiodic monotiles. Labbé and Selinger give an explicit torus Markov partition construction for
  Hat tilings with fractal boundaries,{cite(53)} complementing the inflation picture above.
</p>
<p>
  A substitution also defines a <strong>tiling hull</strong>: translate admitted tilings and close the
  resulting family in the local topology. Patch frequencies and measurable spectral statements belong to
  this ensemble, not to one arbitrarily clipped rendering. Under primitivity and recognizability, invariant
  measures stabilize frequencies; pure-point diffraction still needs geometric or spectral hypotheses.
</p>
<p>
  Detailed treatments continue in {link("sturmian-lattices", "Sturmian lattices")},
  {link("cut-and-project-and-model-sets", "cut-and-project schemes")}, and
  {link("diffraction-and-dynamical-spectrum", "diffraction and dynamical spectrum")}.
</p>
""",
            ),
            Section(
                "Practical generation",
                2,
                f"""
<p>
  For engineering and graphics, inflate until a supertile safely covers the requested rectangle, circle,
  or polygon; transform all child tiles; reject tiles outside the mask; then either retain whole boundary
  tiles or geometrically clip them. Record the seed or root metatile, generation, scale, coordinate
  convention, labels, affine transforms, and clipping policy. IDs are stable only if the generator defines
  and versions that convention.
</p>
<p>
  Do not conflate generation, hierarchy recognition, local validation, global extension, and exhaustive
  enumeration. An explicit substitution can generate and label millions of tiles efficiently while saying
  nothing by itself about whether an arbitrary user-supplied frontier extends. See
  {link("computational-generation", "Computational generation and navigation")} for exact coordinates,
  hierarchy addresses, finite-state methods, and GPU rendering.
</p>
{FIG_TILING_ARRAY}
""",
            ),
            Section(
                "Validation and recurrence",
                2,
                f"""
<p>
  Validate a generated patch by checking polygon closure, edge-to-edge contacts, overlap, uncovered area,
  legal labels, and parent-child counts. Compare several generations with the published substitution
  matrices or known count recurrences; Fibonacci and Lucas sequences occur in Spectre supertile
  counts.{cite(12)} Boundary clipping should be tested separately because it intentionally creates shapes
  that are no longer copies of the prototile.
</p>
<p>
  At an advanced level, a substitution matrix describes how many children of each label each parent
  produces. Its dominant eigenvalue controls area growth, while other eigenstructure helps describe
  frequencies. These algebraic facts do not by themselves establish a cut-and-project or
  <strong>model-set</strong> description, a model set selects projected lattice points using a window in
  an auxiliary “internal” space. CAP and CASPr require additional constructions.{cite(31)}{cite(32)}
</p>
""",
            ),
            Section(
                "Limits and open questions",
                2,
                """
<p>
  Different legal seeds, boundary choices, and representatives can produce different finite patches even
  when they belong to the same tiling space. A substitution generator usually produces a controlled subset
  or parametrization of legal tilings, not necessarily an enumeration of every legal finite patch.
  Numerical coordinates also accumulate error, so exact symbolic geometry or tolerance-aware validation is
  preferable for fabrication and diffraction studies.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="sturmian-lattices",
        title="Sturmian lattices and aperiodic tile sets",
        summary="Balanced mechanical words, three line families, and finite aperiodic tile sets for quadratic slopes.",
        categories=["Mathematics"],
        see_also=["substitution-tiling", "cut-and-project-and-model-sets", "aperiodic-monotile"],
        infobox={
            "Basic object": "Three Sturmian line families",
            "Parameters": "κ, η, α, ρ",
            "Main theorem": "Finite aperiodic set for each quadratic irrational α",
            "Not claimed": "A single aperiodic monotile",
        },
        sections=[
            Section(
                "From balanced words to lines",
                2,
                f"""
<p>
  A Sturmian word is the least complicated binary sequence that is still aperiodic. Its number of distinct
  length-<em>n</em> factors is <em>n</em>+1, and it is <strong>balanced</strong>: two equal-length factors
  differ in their number of 1s by at most one. Lower and upper <strong>mechanical words</strong> obtain the
  symbols by coding an irrational rotation; the slope gives the frequency of long gaps and the intercept
  gives their phase.{cite(13)}{cite(73)}
</p>
<p>
  Akiyama, Hamada, and Ito turn this one-dimensional order into a planar lattice using three families of
  parallel lines at angles 0, 2π/3, and 4π/3. Coordinates take the mechanical-word form
  <em>a(i)=iκ+η<sub>0</sub>+⟦iα+ρ<sub>0</sub>⟧</em>, with analogous formulas for <em>b(j)</em> and
  <em>c(k)</em>, subject to the zero-sum constraints
  η<sub>0</sub>+η<sub>1</sub>+η<sub>2</sub>=ρ<sub>0</sub>+ρ<sub>1</sub>+ρ<sub>2</sub>=0. Whenever
  <em>i+j+k=0</em>, one has |<em>a(i)+b(j)+c(k)</em>|=1/2, so relevant triples bound a uniformly small
  equilateral triangle instead of meeting at one point. Consecutive gaps are at least one. Irrational
  systems admit only the trivial period; rational cases are classified separately and are eventually or
  fully periodic except for explicitly described singular choices. The discontinuous parameter set is dense
  but has two-dimensional Lebesgue measure zero.{cite(13)}{cite(73)}
</p>
<p>
  This line system was motivated by structure extracted from Smith Turtle tilings, but the construction
  stands as a separate finite-tile-set theory. Ref.&nbsp;73 is a seven-page 2026 announcement whose full
  proofs live in ref.&nbsp;13; cite both for completeness, not as independent confirmations.
</p>
""",
            ),
            Section(
                "The four parameter classes",
                2,
                f"""
<p>
  Four kinds of data must be kept separate. <strong>κ</strong> fixes the minimum passage or gap scale;
  the vector <strong>η</strong> translates the three line families; the irrational
  <strong>α</strong> is the density of long gaps; and the intercept vector <strong>ρ</strong> arranges
  those gaps. The components of η and ρ obey zero-sum constraints. Changing α changes the long-range
  frequency, while changing ρ changes phase or boundary termination without changing that frequency.
</p>
<p>
  Finite evidence can falsify a proposed Sturmian coding but cannot prove the infinite property by itself.
  Compute factor complexity, balance, long-gap frequency, and return words over growing windows. A single
  complexity value other than <em>n</em>+1, or a symbol-count discrepancy above one for equal-length
  factors, rules out Sturmian behavior for that coding.{cite(13)}
</p>
""",
            ),
            Section(
                "Nuts, Bolts, and the density equation",
                2,
                f"""
<p>
  The construction uses three annular <strong>Nuts</strong>, labelled S, M, and L, carrying Ammann bars
  that force the three line families. Disk-like <strong>Bolts</strong> constrain how frequently the three
  local classes occur. Their center densities must satisfy
</p>
<p class="wiki-equation">
  δ(S) : δ(M) : δ(L) = (1−α)<sup>2</sup> : 2α(1−α) : α<sup>2</sup>.
</p>
<p>
  Thus α is recoverable from frequencies rather than assumed from a drawing. The proof organizes Bolt
  centers as Delone sets and uses <strong>bounded displacement</strong>: matched points may move, but by a
  distance bounded uniformly over the infinite set. Many-to-many bounded-displacement correspondences
  divide centers into bounded groups, which unfold into finitely many patch-tile shapes.{cite(73)}
</p>
""",
            ),
            Section(
                "The theorem and a 29-tile example",
                2,
                f"""
<p>
  The theorem states that for every quadratic irrational α there is a finite aperiodic tile set
  𝒜(α) enforcing α or its Galois conjugate. Its expansion constant is a unit of the real quadratic field
  ℚ(α). A stronger cardinality estimate is Card(𝒜<sub>λ</sub>)≤2λ+O(1). The mechanism is frequency plus
  bounded displacement; it does not assume that every tiling displays an obvious self-similar inflation.
  Self-similarity is not required by the proof: ref.&nbsp;13 also constructs a tiling space with positive
  topological entropy.{cite(13)}{cite(73)}
</p>
<p>
  For α=√6−2, Nuts enforce Ammann bars and Bolts enforce the density ratio
  (1−α)<sup>2</sup>:2α(1−α):α<sup>2</sup>. A class containing 3S+2L, M, and the three Nuts forces
  (1−α)<sup>2</sup>:α<sup>2</sup>=3:2. The fundamental unit is 5+2√6, and unfolding the bounded groups
  gives 29 patch-tiles. These may be decorated, colored, or disconnected and use matching information.
  The result is therefore a finite aperiodic <em>tile set</em>, not a Hat- or Spectre-like monotile.
  The Nuts / Bolts / density ratio are combinatorial matching constraints in the papers, not a physical
  fastener kit, so this page keeps the quantitative statement rather than a decorative redraw.
</p>
""",
            ),
            Section(
                "Evidence and limits",
                2,
                """
<p>
  Ref.&nbsp;73 is a 2026 preprint note summarizing and extending the fuller treatment in ref.&nbsp;13.
  The definitions, classification, and theorem are mathematical claims; no manufacturing, mechanical, or
  wave advantage follows. The construction is valuable because it shows how symbolic balance, planar line
  geometry, density invariants, and aperiodic matching rules fit together without collapsing those layers
  into “looks quasiperiodic.”
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="diffraction-and-dynamical-spectrum",
        title="Diffraction and dynamical spectrum",
        summary="How infinite-volume correlations become Bragg and continuous diffraction, and what finite FFTs can actually show.",
        categories=["Mathematics", "Research frontiers"],
        see_also=["waves-and-photonics", "cut-and-project-and-model-sets", "hat-tile", "spectre-tile"],
        infobox={
            "Input": "Weighted Dirac comb",
            "Core limit": "Volume-averaged autocorrelation",
            "Output": "Diffraction measure",
            "Warning": "Finite FFT ≠ proof of spectral type",
        },
        sections=[
            Section(
                "From a tiling to a diffraction measure",
                2,
                f"""
<p>
  Diffraction belongs to a specified decoration, not to a tile name. Choose control points
  <em>x</em><sub>j</sub> and weights <em>w</em><sub>j</sub>, then form the weighted Dirac comb
  ω=Σ<em>w</em><sub>j</sub>δ<sub><em>x</em><sub>j</sub></sub>. Its autocorrelation γ is the
  volume-averaged limit of ω restricted to larger regions convolved with its reflected conjugate. The
  mathematical diffraction measure is the Fourier transform γ̂.{cite(6)}{cite(35)}
</p>
<p>
  Atomic or resonator motifs modify amplitudes through form factors. Moving a repeated decoration within
  every Spectre changes nearest-neighbor distances, extinctions, and Fourier intensity even when the
  underlying tile adjacency is unchanged.{cite(30)} A control-point theorem therefore cannot be copied
  unchanged to holes, antennas, struts, or a multiphase specimen.
</p>
""",
            ),
            Section(
                "Bragg and continuous components",
                2,
                f"""
<p>
  The pure-point part of γ̂ consists of delta peaks, Bragg diffraction. Singular-continuous and
  absolutely-continuous parts are spread rather than concentrated, but they encode different kinds of
  order and disorder. Pure-point diffraction is not synonymous with “aperiodic,” “substitution,” or
  “quasicrystalline-looking.” CAP and CASPr model-set constructions provide the extra hypotheses needed
  for exact Hat- and Spectre-family Fourier-Bohr amplitudes.{cite(31)}{cite(32)}{cite(35)}
</p>
<p>
  Dynamical spectrum concerns translation acting on the entire tiling hull; diffraction concerns a
  chosen weighted point set. They are related under standard ergodic hypotheses but are not interchangeable
  labels. Substitution matrices first provide growth and frequencies; pair correlations and geometric
  displacement data are additional inputs to spectral classification.{cite(36)}
</p>
""",
            ),
            Section(
                "What finite Fourier transforms miss",
                2,
                f"""
<p>
  A finite FFT multiplies the infinite structure by a window. Peak width, sidelobes, pixel smoothing,
  clipping, and boundary shape can create or conceal weak components. A sharp image is evidence of
  organized correlations in that approximant, not by itself a proof of pure-point diffraction. Report
  point weights, physical motif, aperture, normalization, boundary, patch generation, and convergence
  across increasing windows.
</p>
<p>
  Exact renormalization is stronger. Inflation maps displacement classes across scale, yielding matrix
  recursions for pair-correlation measures and Fourier cocycles. These equations let large-patch FFTs be
  checked against hierarchy-implied frequencies rather than interpreted only by eye.{cite(36)}
</p>
""",
            ),
            Section(
                "Hat and Spectre evidence",
                2,
                f"""
<p>
  The Hat has several distinct diffraction statements. Socolar gives a six-dimensional Golden Key
  construction; CAP supplies a regular-model-set description; one vertex decoration also has diffraction
  on an underlying periodic framework.{cite(6)}{cite(31)}{cite(33)} Spectre/CASPr has Rauzy-fractal windows
  and pure-point order, while crystallographic work finds non-periodic chiral sixfold diffraction for a
  specified decoration.{cite(32)}{cite(34)}{cite(35)}
</p>
<p>
  Moritake and colleagues fabricated 372,100 circular holes of radius 100&nbsp;nm at Hat centroids in a
  roughly 500 × 500&nbsp;μm, 350-nm silicon-nitride specimen, with pseudo-period swept from 600 to
  750&nbsp;nm. The measured pinwheel twist was 15.52° relative to radial directions. Exact model-set
  calculations supply complementary intensities: a CAP equal-weight central peak of order
  1/(75φ<sup>4</sup>)≈0.001945 and a CASPr brightest equal-weight peak of order
  (31−8√15)/972≈1.66×10<sup>−5</sup>. Position-independent peaks, mirror-reversed pinwheels, and circular-
  polarization contrast establish planar-chiral optical diffraction for that specimen. They do not prove
  a band gap or universal Spectre response.{cite(19)}{cite(35)}
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="cut-and-project-and-model-sets",
        title="Cut-and-project schemes and model sets",
        summary="Physical and internal space, lattices, star maps, windows, and the evidence required for a Spectre lift claim.",
        categories=["Mathematics"],
        see_also=["four-dimensional-lift", "diffraction-and-dynamical-spectrum", "sturmian-lattices"],
        infobox={
            "Spaces": "Physical × internal",
            "Selector": "Acceptance window",
            "Classical examples": "Duneau-Katz, de Bruijn",
            "Hat/Spectre models": "CAP / CASPr",
        },
        sections=[
            Section(
                "The cut-and-project recipe",
                2,
                f"""
<p>
  Start with a lattice ℒ in a product of physical space and internal space. Each lattice point has a
  physical projection and an internal projection, often called its <strong>star map</strong>. Retain a
  lattice point when its internal image lies in an acceptance <strong>window</strong>; the retained physical
  projections form a model set. Irrational orientation prevents an ordinary physical-space period while
  the parent lattice preserves long-range order.{cite(31)}
</p>
<p>
  Duneau and Katz established this projection viewpoint for quasiperiodic patterns.{cite(75)} De Bruijn’s Penrose
  pentagrid supplies a worked algebraic example: five indexed line families assign integer coordinates,
  and dualizing grid intersections produces rhombi. Singular offsets require explicit boundary
  conventions; merely counting visible directions is not a cut-and-project proof.{cite(76)}
</p>
""",
            ),
            Section(
                "Windows, regularity, and diffraction",
                2,
                f"""
<p>
  The window controls allowed local configurations and Fourier amplitudes. A regular model set uses a
  relatively compact window whose boundary has measure zero under the usual hypotheses, giving pure-point
  diffraction. Different windows on the same lattice can produce different point sets, and different
  weights can create extinctions.{cite(31)}{cite(32)}{cite(35)}
</p>
<p>
  CAP is a self-similar Hat-family representative with a 4:2 cut-and-project description. CASPr gives the
  Spectre-family analogue using five Rauzy-fractal windows. These are theorem-backed model-set
  constructions, not generic consequences of every drawing of a Hat or Spectre patch.{cite(31)}{cite(32)}
</p>
""",
            ),
            Section(
                "CAP versus Nan Ma’s lift",
                2,
                f"""
<p>
  Nan Ma’s coherent ℝ⁴ edge lift splits two edge-direction classes into two coordinate planes and integrates
  them across a simply connected tiling.{cite(54)} It elegantly unifies Tile(<em>a,b</em>) projections, but
  it does not by itself identify a lattice, star map, or acceptance window. CAP/CASPr instead use return
  modules, algebraic conjugation, and explicit windows to prove model-set and spectral statements.
</p>
<p>
  Van Dongen’s “lift” is different again: a three-dimensional architectural construction made by replacing
  double-kites with polyhedral surface modules. It can produce continuous non-periodically textured walls,
  but it is neither Ma’s ℝ⁴ height function nor a cut-and-project theorem.{cite(69)}
</p>
""",
            ),
            Section(
                "Checklist for a Spectre claim",
                2,
                """
<p>
  A proposed Spectre model set should state the ambient lattice or module, physical and internal projections,
  injectivity/density conditions, star map, window, treatment of boundary points, and a proof that the
  selected projections reproduce the intended control-point hull. A Fourier module of a certain rank or a
  visually convincing high-dimensional projection is evidence to investigate, not a substitute for those
  data.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="discovery-history",
        title="Discovery history of the Hat and Spectre",
        summary="A dated account of physical search, computation, proof, and the official records behind the 2023 discoveries.",
        categories=["History", "Mathematics"],
        see_also=["hat-tile", "spectre-tile", "computational-generation", "resources-and-tools"],
        infobox={
            "Hat announced": "March 2023",
            "Spectre announced": "May 2023",
            "Discovery modes": "Physical experiments + computation",
            "Proof status": "Peer-reviewed papers (2024)",
        },
        sections=[
            Section(
                "The Hat: November 2022 to March 2023",
                2,
                f"""
<p>
  David Smith combined paper cutouts, card experiments, and polyform-search software rather than relying
  on one lucky picture. In November 2022 he sent Craig Kaplan a candidate assembled from kites. Kaplan’s
  computation grew larger patches; Joseph Myers and Chaim Goodman-Strauss joined the effort to identify
  forced metatiles and turn the candidate into a proof. The Hat preprint appeared in March 2023.{cite(1)}{cite(3)}
</p>
<p>
  Official project pages, Kaplan’s dated retrospective, Smith’s Hedraweb posts, and the PolyForm Puzzle
  Solver document discovery practice; the 2024 open-access journal paper is the authority for the theorem.
  A large finite patch was evidence of compatibility, while forced hierarchy and incommensurability supplied
  the global aperiodicity argument.
</p>
""",
            ),
            Section(
                "The Spectre: weak to strict chirality",
                2,
                f"""
<p>
  Firm public dates: Smith contacted Kaplan on 17&nbsp;November&nbsp;2022; he suggested an einstein
  candidate on 24&nbsp;November; the Hat preprint appeared on 20&nbsp;March&nbsp;2023; the Spectre
  preprint on 28&nbsp;May&nbsp;2023; and the peer-reviewed papers followed on 30&nbsp;June and
  30&nbsp;September&nbsp;2024.{cite(1)}{cite(2)}{cite(3)}
</p>
<p>
  The straight equilateral Tile(1,1) initially looked like a limiting family member with a periodic
  escape: equal numbers of both handednesses tile periodically. Smith’s experiments showed that when
  reflections were forbidden, recurring eight- and nine-tile clusters and Mystic pairs exposed a
  homochiral hierarchy. Edge modifications then made the no-reflection rule geometric, producing strict
  Spectres. Anecdotes about a “six-day turn” appear in informal histories; this wiki keeps only the
  dated public record unless a first-person source is cited for that specific claim.{cite(2)}{cite(3)}
</p>
<p>
  Discovery narrative and theorem should remain distinct. First-person posts explain who noticed what and
  which tools were used; the peer-reviewed paper defines weak versus strict chirality and proves
  aperiodicity. Community models and press articles are useful orientation sources, not replacements for
  the proof.
</p>
""",
            ),
            Section(
                "Evidence levels and later work",
                2,
                f"""
<ul>
  <li><strong>Primary theorem:</strong> the final Hat and Spectre papers.{cite(1)}{cite(2)}</li>
  <li><strong>Independent mathematics:</strong> alternative proof, direct construction, group and rhombic
  formulations.{cite(4)}{cite(5)}{cite(8)}{cite(9)}</li>
  <li><strong>Discoverer history:</strong> dated project pages, repositories, and first-person accounts.</li>
  <li><strong>Community and journalism:</strong> museum events, Hatfest, videos, and reporting that explain
  reception but do not independently certify theorem details.</li>
  <li><strong>Unverified claim:</strong> ref.&nbsp;28’s golden-ratio argument remains quarantined because an
  irrational count limit for one construction does not rule out all periodic tilings.{cite(28)}</li>
</ul>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="computational-generation",
        title="Computational generation and navigation",
        summary="Exact patch generation, hierarchical addresses, finite-state navigation, GPU rendering, and independent validation.",
        categories=["Mathematics", "Computer graphics", "Algorithms"],
        see_also=["substitution-tiling", "algorithms-and-machine-learning", "resources-and-tools"],
        infobox={
            "Core representation": "State + affine transform + hierarchy address",
            "Preferred geometry": "Exact or symbolic",
            "Navigation": "Recursive or finite-state",
            "Validation": "Topology and geometry, independently",
        },
        sections=[
            Section(
                "Five different computational problems",
                2,
                f"""
<p>
  <strong>Generation</strong> produces one legal substitution patch. <strong>Recognition</strong> recovers
  parent supertiles from children. <strong>Local validation</strong> checks contacts and labels.
  <strong>Extension</strong> asks whether a finite frontier belongs to an infinite tiling, while
  <strong>enumeration</strong> asks for all legal patches. A hierarchy can make the first three practical
  without automatically solving the last two.
</p>
<p>
  Undecidability results concern specified broad input classes: three connected polyhypercubes in 4D,
  translational monotiles in ℤ<sup>d</sup> for <em>d</em>≥3, and three polycubes in a 3D translational
  setting.{cite(24)}{cite(56)}{cite(59)} They do not make explicit Hat or Spectre substitution generation
  undecidable. Seven-polyomino aperiodic sets likewise illuminate the small-set frontier without changing
  the one-planar-monotile theorem.{cite(58)} Separately, SAT methods can certify isohedral polyforms, but
  no general algorithm is known for recognizing aperiodic monotiles as an input class.{cite(17)}
</p>
""",
            ),
            Section(
                "Exact coordinates and hierarchy addresses",
                2,
                f"""
<p>
  Store every tile as a discrete state, orientation, exact or high-precision affine transform, and a stable
  path from the root supertile. Expand the hierarchy before clipping. Exact symbolic coordinates prevent
  tiny roundoff discrepancies from becoming false gaps or overlaps; floating-point coordinates remain
  appropriate for final rendering after topology is fixed.
</p>
<p>
  Voss’s MATLAB constructor translates the S/M composition rules into coordinates and was visually checked
  through level eight, containing 16,908,641 Tile(1,1) instances.{cite(29)} Tatham’s combinatorial coordinate
  system instead rewrites hierarchical addresses to cross tile edges, generating a local neighborhood
  without materializing a giant enclosing supertile. The symbolic-spectre-tiles repository provides an
  MPL-2.0 exact-coordinate export path; both independent implementations still require comparison with the
  official rules.
</p>
""",
            ),
            Section(
                "Finite-state navigation and automatic refinement",
                2,
                """
<p>
  Recursive neighbor lookup can become expensive or ambiguous near infinite-order boundaries. Finite-state
  transducers read and rewrite hierarchy-address strings directly, giving bounded-state navigation for
  supported substitution presentations. Tatham’s neighborhood-refinement method splits ambiguous tile
  states until deterministic transitions become possible, then minimizes equivalent states; on Hat and
  Spectre inputs it recovers known refined systems. The author does not claim a universal theorem for every
  substitution.
</p>
""",
            ),
            Section(
                "GPU rendering without losing provenance",
                2,
                """
<p>
  GPU renderers should instance one canonical mesh and upload compact transforms or split algebraic
  components. Reusser’s WebGPU notebook separates transform components so Hat-Spectre-Turtle morphs become
  per-frame projections and reports roughly 17 million depth-eight instances. Deep zoom can generate
  supertiles on demand and replace subpixel detail with simpler instances, but extreme scales expose
  floating-point failure and level-of-detail seams.
</p>
<p>
  Rendering speed is not geometric validation. Archive the rule table, root state, depth, coordinate
  convention, clipping mask, transform precision, renderer revision, and file hashes. Validate polygon
  closure, overlap, uncovered area, edge contacts, legal states, hierarchy counts, and handedness in a
  separate code path.
</p>
""",
            ),
            Section(
                "Tool choice and scope",
                2,
                """
<p>
  Prefer the official BSD-licensed <code>hatviz</code> and <code>hatvalidate</code> repositories for Hat
  reference generation and proof-case replay. The MIT TileOneOne code generates the straight weakly chiral
  polygon; it does not add strict Spectre edge modifications. Browser studios are excellent for exploration
  but may permit overlaps, reflections, or freeform invalid layouts. License, geometry variant, revision,
  and export semantics must be checked tool by tool.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="dimers-and-constrained-models",
        title="Dimers and constrained models",
        summary="Exact classical and quantum dimer results on a regularized Spectre graph, with their physical limits.",
        categories=["Mathematics", "Physics"],
        see_also=["materials-science", "waves-and-photonics", "spectre-tile"],
        infobox={
            "Model": "Perfect matchings on a Spectre-derived graph",
            "Exact count": "Z = 2^(N_Mystic + 1)",
            "Evidence": "Theorem/model + numerical verification",
            "Not evidence for": "A measured quantum material",
        },
        sections=[
            Section(
                "What a dimer model asks",
                2,
                f"""
<p>
  A perfect matching covers every graph vertex exactly once with selected edges called dimers. Singh and
  Flicker regularize the Spectre graph by adding a “gold” vertex to 13-edge environments so each decorated
  tile contributes identical connectivity and the graph remains bipartite. Forced dimers then leave
  independent two-way choices on Upper Mystics plus one boundary choice. Some raw finite Spectre patches
  admit no perfect matching until that boundary/decorative construction is regularized, so the exact
  result is graph-decoration dependent.{cite(22)}
</p>
{FIG_PHYSICS_DIMERS}
""",
            ),
            Section(
                "Exact classical and quantum results",
                2,
                f"""
<p>
  The classical partition function is exactly
  Z=2<sup>N<sub>Mystic</sub>+1</sup>. The thermodynamic free energy per dimer is
  ln(2)/[3(5+√15)]≈0.02604, much smaller than the cited square-lattice value 0.583. Finite-patch FKT counts
  on S2-S6 verify the combinatorial result.{cite(22)}
</p>
<p>
  In the Rokhsar-Kivelson quantum model, the independent Mystic choices give an exact eigenbasis for every
  V/t; a flipped Mystic costs 2t. Test monomers can separate arbitrarily far at no additional energy, so
  the model is deconfined across the stated parameter family. Singh’s 2025 thesis places this result beside
  algorithms and constrained models on Ammann-Beenker, Penrose, and random graphs.{cite(70)}
</p>
""",
            ),
            Section(
                "Interpretation and limits",
                2,
                """
<p>
  These are exact results for a specified regularized adjacency graph, not measurements on a tile-shaped
  solid. Aperiodicity alone does not imply a quantum spin liquid, and changing vertices, couplings,
  boundaries, or graph regularization changes the model. A physical proposal must identify microscopic
  degrees of freedom, energy scales, disorder, preparation, and observables before borrowing the exact
  combinatorial language.
</p>
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
  when two similar periodic or quasi-periodic structures are overlaid, fabrics, fences, screens, or
  printed grids. The eye (or a camera) does not see either layer’s fine detail; it sees the
  <em>beat</em> between them: bright and dark regions where local alignment reinforces or cancels.
</p>
<p>
  Aperiodic monotile arrays make that classic idea richer. Because each layer is ordered but
  non-repeating, the beat field does not collapse into ordinary wallpaper. Instead it yields
  cells, channels, and gradients that stay deterministic and seed-stable while still feeling
  organic.{cite(6)} For the related sampling problem, false patterns from under-resolving a single
  lattice, see {link("aliasing", "Aliasing")}.
</p>
""",
            ),
            Section(
                "Layered arrays and beat patterns",
                2,
                """
<p>
  Take one aperiodic monotile array and <strong>layer a second copy on top</strong>, same seed, same tile
  scale, but offset by a small transform: a translation (<em>tx</em>, <em>ty</em>) and/or a rotation θ
  away from perfect alignment. Where the two structured layers agree locally, contrast cancels; where
  they disagree, macroscopic bright and dark regions appear. The result is a <strong>new visual
  field</strong> that was not present in either layer alone.
</p>
<p>
  Because both layers are aperiodic, the beat pattern does not settle into a simple repeating wallpaper.
  Instead it produces large-scale structures, cells, channels, and gradients, whose topology changes
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
  At very small rotations from pure alignment, on the order of <strong>one degree</strong>, the
  interference often organizes into radial <strong>rosette</strong> or cell-like structures: a bright or
  dark focal center surrounded by lobes that read almost like flowers or lenses. These are not random
  halos; they are the macroscopic signature of microscopic tile disagreement accumulating across the
  patch (see the figure at left).
</p>
<p>
  Observers often describe this field as a <strong>navigable 3D space</strong>: nudging <em>tx</em> and
  <em>ty</em> pans across the moiré terrain, while small changes in rotation θ act like a zoom or
  dolly, the rosette cells expand, contract, and hand off to neighbors without ever repeating on a
  simple grid. The perceived depth is an optical effect, not true geometry, but it is stable and
  controllable, which makes it interesting for interfaces, data visualization, and spatial encoding.
</p>
""",
            ),
            Section(
                "Phason rivers",
                2,
                f"""
<p>
  At larger rotation offsets the beat field changes character. For example, at <strong>60°</strong> between
  layers, interference can organize into winding, channel-like structures, <strong>phason rivers</strong>
 , that flow in broad strokes across the patch. In quasicrystal physics, a <em>phason</em> is a type of
  structural rearrangement; here the term is used informally for these moiré channels: coherent pathways
  where the two arrays stay in partial registry over long distances before shearing apart.
</p>
{FIG_MOIRE_60DEG}
<p>
  Unlike the near-aligned rosettes, phason rivers are <strong>not intuitive</strong>. Their paths, branch
  points, and sensitivity to tiny parameter changes are not yet well characterized for aperiodic monotile
  arrays. Which rotations produce stable rivers? Do rivers form a navigable network or fragment under
  translation? Can they encode data or serve as routing channels? These questions are <strong>open research
  frontiers</strong>, worthy of systematic study now that monotile patches can be generated and overlaid
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
  <li><strong>tx, ty</strong>, translate the upper layer; the moiré field scrolls, revealing new river
  segments or rosette cells.</li>
  <li><strong>Rotation θ</strong>, twist the upper layer; at small θ the effect reads as zoom or
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
            Section(
                "Terminology and limits",
                2,
                f"""
<p>
  Moiré is interference between overlaid structures; {link("aliasing", "aliasing")} is false low-frequency
  content created by inadequate sampling. They can look similar and can occur together. “Phason rivers” on
  this page is an informal visual label, not evidence that the overlay realizes the phason dynamics of a
  physical quasicrystal.
</p>
<p>
  The apparent depth and navigation behavior are perceptual observations that need controlled user studies.
  Finite patch boundaries, line width, transparency, raster resolution, and layer registration can dominate
  the image. Proposed storage, routing, and interface uses remain speculative until compared with simpler
  periodic and non-periodic encodings using stated metrics.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="aliasing",
        title="Aliasing",
        summary="How periodic structure creates false patterns under sampling, and why aperiodic monotile layouts resist them.",
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
  the sampler cannot resolve does not disappear, it <em>folds</em> into a lower frequency the system
  <em>can</em> represent. On a screen that looks like shimmering edges, crawling lines, or striped bands
  that were never in the scene. The Nyquist-Shannon sampling theorem is the classical statement: to
  reconstruct a band-limited signal faithfully, you must sample at least twice its highest frequency.
</p>
<p>
  Spatial aliasing is the same idea in 2D. A brick wall, a fence, a checkerboard, or a dense hatched fill
  has a dominant lattice frequency. When that frequency approaches the pixel (or sensor, or print-dot)
  frequency, the two grids beat, and you see a pattern that belongs to neither grid alone. That beat is
  closely related to {link("moire", "moiré")}; aliasing is the sampling-side story, moiré the overlay story.
</p>
""",
            ),
            Section(
                "Why regular tilings are fragile",
                2,
                f"""
<p>
  Periodic monohedral tilings, squares, hexagons, brickwork, are efficient and familiar, but they put
  almost all of their energy on a few reciprocal-lattice peaks. Point a camera, mipmap a texture, or
  print at an awkward DPI, and those peaks are exactly what collide with the sample lattice.
</p>
<p>
  Anti-aliasing filters (mipmaps, supersampling, anisotropic filtering) try to remove frequencies the
  display cannot carry. They help, but they also blur. Random noise textures dodge the lattice problem
  by having no coherent peaks, at the cost of structure, reproducibility, and clean fabrication IDs.
</p>
<p>
  Aperiodic monotile patches sit between those extremes: <strong>ordered but non-repeating</strong>,
  with diffraction more like a quasicrystal than a crystal, sharp features, yet no single translational
  lattice to lock onto the sample grid.{cite(6)} Synthetic beamforming on selected Hat-family layouts
  reports lower sidelobes than tested regular and aperiodic controls, but this is not hardware or an
  image-reconstruction result.{cite(37)}
</p>
""",
            ),
            Section(
                "A cleaner monotile surface",
                2,
                f"""
<p>
  Below, a landscape shaded with an aperiodic monotile packing. There is still plenty of edge detail, but
  the structure does not present one repeating period for the image grid to quarrel with, so the surface
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
  <li><strong>Textures and decals</strong>, prefer aperiodic packing when the pattern will be viewed
  across many scales (games cameras, print proofs, video).</li>
  <li><strong>Scatter and fill</strong>, monotile instance layouts avoid the row/column bands of a grid
  scatter without looking random.</li>
  <li><strong>Halftone and fabrication</strong>, when a screen or toolpath is itself periodic, pairing it
  with a periodic artwork doubles the risk; an aperiodic artwork removes one of the two lattices.</li>
  <li><strong>Do not confuse the two effects</strong>, deliberate layered overlays are {link("moire", "moiré")}
  research; accidental undersampling of one lattice is aliasing.</li>
</ul>
<p>
  See {link("computer-graphics", "Computer graphics")} and
  {link("signal-processing", "Signal processing and imaging")} for workflow detail.
</p>
""",
            ),
            Section(
                "Limits",
                2,
                """
<p>
  Aperiodicity redistributes spectral energy; it does not make a pattern alias-free. Sharp tile edges,
  high-frequency per-tile textures, strong quasicrystalline peaks, and repeated finite assets can still
  shimmer or form false structure. Correct remedies remain adequate sampling, prefiltering, mipmapping,
  supersampling, and temporal testing. Compare patterns at matched feature density and contrast before
  attributing an improvement to layout.
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
  the camera pulls back and the repetition snaps into view, visible seams, moiré shimmer, wallpaper
  patterns marching across the frame. The classic fixes all trade something away. Larger textures cost
  memory; randomized scatter loses structure and is hard to make deterministic; blend-based tiling blurs
  detail.
</p>
<p>
  An aperiodic monotile patch attacks the root cause. The geometry itself is mathematically incapable of
  translational repetition,{cite(2)} yet it is a single instanced shape, one mesh, one material slot, one
  draw-call strategy, and every placement is deterministic and seed-stable. You get grid-like production
  economics with no translational repetition in the generated layout. Memory and draw-call costs still
  depend on implementation.
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
  one seam. The hexagonal floor on the left is calm but visibly repetitive, the eye finds rows
  quickly, and at some render scales those rows can become
  <a href="aliasing.html">aliasing</a> bands. The Spectre floor on the right has the
  same nominal tile density and one base outline, but lacks a translational repeat. Finite motifs still
  recur, and the render remains subject to filtering and edge aliasing. For the sampling story, see
  {link("aliasing", "Aliasing")}.
</p>
{FIG_CG_SUNSET}
{FIG_CG_BRASS}
{FIG_CG_LUMEN}
{FIG_CG_INK}
{FIG_CG_HILLS}
{FIG_CG_FALCOR}
{FIG_CG_ORBIT}
{FIG_CG_BALL}
""",
            ),
            Section(
                "Production pipeline",
                2,
                f"""
<p>
  Start with one canonical polygon and a transform table. Generate beyond the camera footprint, clip only
  if the asset needs a hard boundary, triangulate the base tile once, and apply each row’s translation and
  rotation as an instance transform. Keep geometry coordinates, tile ID, hierarchy label, and material
  class in separate attributes so layout changes do not invalidate shading.
</p>
<ol>
  <li>Generate and validate a patch at world scale; retain provenance and units.</li>
  <li>Import CSV/JSON transforms for instancing, or GLB for a portable scene; use SVG for masks and decals.</li>
  <li>Assign colors or texture offsets from stable IDs or hierarchy labels rather than frame-dependent randomness.</li>
  <li>Bake normals, displacement, or albedo only after deciding the camera-distance and texel-density targets.</li>
  <li>Test animated cameras with temporal anti-aliasing, mipmapping, and anisotropic filtering enabled.</li>
</ol>
<p>
  Interfaces with periodic regions can be designed explicitly when a scene needs both.{cite(18)}
</p>
""",
            ),
            Section(
                "Instancing, sampling, and level of detail",
                2,
                f"""
<p>
  For large patches, avoid one object and one draw call per tile. Store the mesh once, batch transforms in
  an instance buffer, frustum-cull by hierarchy cluster, and merge only distant clusters. A hierarchy gives
  natural level-of-detail units, but coarse meshes must preserve silhouettes and material statistics or
  they will pop. Measure frame time, GPU memory, draw calls, overdraw, and visible seam count against a
  periodic grid and a randomized scatter with the same tile density. Finished scene loops from the same
  pipeline are collected on the <a href="../../art.html">art page</a>.
</p>
<p>
  Aperiodic placement changes the spectrum of the layout; it does not band-limit the texture painted on
  each tile. Use mipmaps for color, filtered displacement or normal maps, adequate UV gutters, and
  supersampled vector rasterization. Tile centroids can also serve as deterministic sample points, but
  reconstruction quality must be measured against grids, jittered grids, and blue noise rather than
  inferred from appearance.{cite(37)}
</p>
""",
            ),
            Section(
                "Limitations",
                2,
                """
<p>
  Aperiodicity does not automatically remove texture seams, UV discontinuities, jagged silhouettes,
  temporal shimmer, clipping artifacts, or poor level-of-detail transitions. A finite patch can still show
  large-scale bias, and a repeated finite patch is periodic regardless of how it was generated. The safest
  claim is narrower: canonical monotile transforms provide a deterministic layout without translational
  repetition, leaving ordinary graphics engineering responsible for filtering and performance.
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
                "One shape, no repeating motif",
                2,
                f"""
<p>
  Historic zellige, azulejo, and parquet crafts fought monotony with hand variation. Industrial printing
  and molding made exact repeats cheap, and made wallpaper repeats obvious at wall scale. An aperiodic
  monotile restores structure without a translational repeat unit: one manufactured outline, arrangements
  that cannot tile by lattice translation, proved rather than promised.{cite(2)}{cite(3)}
  More finished stills and loops live on the
  <a href="../../art.html">art page</a>.
</p>
{FIG_ZELLIGE_EMERALD}
{FIG_DESIGN_HILLS}
{FIG_DESIGN_CERAMIC}
<p>
  Because the tiling is deterministic, a designer can sign off on the <em>exact</em> layout before
  fabrication, every tile position is known, exportable, and reproducible. And because Tile(1,1) needs no
  reflected copies, a homochiral design can avoid a second mirrored outline. Whether production can use one
  mold, die, or glaze workflow depends on edge treatment, finish, and process.{cite(2)}
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
  <li><strong>Choose the geometry for the manufacturing constraint.</strong> Hat tilings require
  reflected copies, so one-sided glazed or finished parts become two SKUs. Homochiral Spectre or
  Tile(1,1) layouts avoid that second outline when the process cannot flip parts. If both faces are
  identical, Hat may still be acceptable. The choice is a manufacturing tradeoff, not a universal
  Spectre preference.{cite(1)}{cite(2)}</li>
  <li><strong>Prefer curved or keyed edges when installers must not invent periodicity.</strong> The
  straight-edged Tile(1,1) <em>can</em> be assembled into a periodic pattern by a well-meaning installer
  using both handednesses. Curved Spectre edges physically refuse periodic and reflected placements,
  the geometry enforces correctness.{cite(2)}</li>
  <li><strong>Get the outline from a trusted source.</strong> Kaplan's
  <a href="https://cs.uwaterloo.ca/~csk/spectre/" rel="noopener noreferrer">project page</a> publishes SVG
  outlines; community repositories provide OpenSCAD, STL, and DXF for 3D printing, laser cutting, and CNC
  (see the {link("bibliography", "bibliography")} tools list). Parametric models let you add
  orientation marks so pieces cannot be laid face-down.</li>
  <li><strong>Assemble by supertile.</strong> Working tile-by-tile invites dead ends. Pre-assemble the
  8-to-9-tile clusters from the substitution system, then place clusters, the same hierarchy the
  mathematics uses. See {link("substitution-tiling", "Substitution tiling")}.</li>
  <li><strong>Or skip layout entirely:</strong> generate the exact patch for your wall's dimensions with a
  clipping mask at
  <a href="https://aperiodicgenerator.com/" rel="noopener noreferrer">aperiodicgenerator.com</a>,
  and deliver the installer a numbered plan where every tile has an ID and position.</li>
</ol>
<p>
  Coates studies hexagonal quasiperiodic decorations of periodic lattices as a transferable geometric
  precedent; vertices may remain periodic while bonds are quasiperiodic.{cite(18)}
  The cited work does not prove a coherent periodic-Spectre interface, so a Spectre handoff still requires
  an explicit boundary coding, metric fit, tolerance study, and physical validation.
</p>
""",
            ),
            Section(
                "Composition, color, and scale",
                2,
                f"""
<p>
  The outline supplies structure, not a finished composition. Color can follow tile orientation,
  substitution parent, distance from a focal point, or a small constrained palette. Use hierarchy labels
  for broad fields and per-tile IDs for fine variation; this preserves visual continuity without inventing
  a repeat unit. Mock up the full elevation or floor at viewing distance, because dense joints and high
  contrast can dominate the shape.
</p>
<p>
  Jowers and Moat expose another design layer by connecting selected Hat-family vertices with straight
  segments. The resulting subsidiary systems contain mostly convex polygons aligned with larger metatile
  structure, opening alternatives for color fields, screens, and multi-part assemblies.{cite(66)} Some
  newly proposed derivatives are described by their authors as <em>assumed</em> aperiodic rather than
  proved, so geometric exploration must not be promoted as a new monotile theorem.
</p>
<ul>
  <li>Feature walls, floors, and facades with provable non-repetition, including built limestone terraces
  assembled from hundreds of waterjet-cut Spectre pieces (see {link("bibliography", "bibliography")})</li>
  <li>Mathematically constructed three-dimensional topological-interlocking systems made from identical
  aperiodic blocks; physical load testing remains open{cite(50)}</li>
  <li>Generative sculpture, ornamental screens, and visual illusions</li>
  <li>Textiles, wallpaper, packaging, embossing, and engraving with no repeat unit</li>
  <li>Lightweight shells, tensile structures, and spatial studies for built environments</li>
</ul>
""",
            ),
            Section(
                "Lifted wall modules and interfaces",
                2,
                f"""
<p>
  Van Dongen’s <em>Lifted Aperiodic Hat and Turtle</em> replaces each double-kite with a polyhedral surface
  module, then glues modules into congruent three-dimensional Hat or Turtle units. The resulting assemblies
  can carry a continuous non-periodic wall texture; paper layouts and an alternate square-grid lift make
  the geometry reproducible.{cite(69)}
</p>
<p>
  This is a geometric and artistic construction, not structural engineering and not Nan Ma’s ℝ⁴ edge lift.
  It reports no load, joint, weathering, fire, drainage, code, tolerance, or scale tests. Likewise, Coates’s
  periodic-aperiodic interfaces are methodological precedent rather than proof that a periodic wall can
  meet a Spectre field coherently without a separately designed boundary map.{cite(18)}
</p>
""",
            ),
            Section(
                "Fabrication and installation planning",
                2,
                f"""
<p>
  Freeze the canonical outline, units, handedness, joint width, and boundary policy before nesting parts.
  Number pieces or clusters on the drawing and on removable labels. Dry-fit substitution clusters, survey
  cumulative error, then install from fixed datums rather than following a drifting edge. Record partial
  boundary pieces separately from whole tiles and reserve spares by orientation.
</p>
<p>
  For floors and walls, account for substrate flatness, adhesive bed, grout movement joints, drainage,
  cleanability, slip resistance, fire behavior, weathering, and replacement access. Structural facades
  require an independent support and fastening design; the mathematical tiling is not a building system.
  Built terraces and community installations show that physical assembly is feasible. Coates’s
  periodic-aperiodic interface work is precedent for boundary design, not a validated Spectre installation
  recipe.{cite(18)}
</p>
""",
            ),
            Section(
                "Constraints and open design questions",
                2,
                """
<p>
  A single outline does not guarantee one mold, lower cost, code compliance, or easy replacement. Curved
  edges may increase cutting time; one-sided finishes can create handed inventory; small acute features
  may chip; and clipped boundaries can dominate waste. Compare nesting yield, tool time, part count,
  installer error, maintenance access, and total installed cost with a conventional module.
</p>
<p>
  Ornament, tested mechanical lattices, and proposed architectural shells are different evidence levels.
  Describe a built installation as built, a simulation as simulated, and an untested facade or textile
  concept as a candidate direction.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="materials-and-fabrication",
        title="Materials and fabrication",
        summary="From relief panels to STL toolpaths, one patch, many physical outputs.",
        categories=["Applications"],
        see_also=["design-and-architecture", "materials-science"],
        infobox={
            "Exports": "SVG, STL, GLB, CSV, JSON",
            "Status": "Immediately practical",
            "Tooling": "Single-sided (no mirrored parts)",
        },
        sections=[
            Section(
                "Cutting, molding, and toolpaths",
                2,
                f"""
<p>
  A single generated patch exports as SVG for cutting, STL for printing, GLB for instancing, and CSV/JSON
  for custom toolpaths. One design becomes a relief panel, a printed texture, an instanced mesh, or a
  dataset of tile transforms, with identical geometry in each.{cite(2)}{cite(10)}
</p>
{FIG_FABRICATION_PANEL}
<p>
  The chirality result can simplify part inventory: Spectre tilings do not require a second mirrored
  outline.{cite(2)} Tool count still depends on edge variants, draft, finish, and process. Community fabrication files,
  OpenSCAD models, STLs with orientation grids, laser-cut outlines, are indexed in the
  {link("bibliography", "bibliography")} and {link("resources-and-tools", "Resources and tools")}. Digital
  monotile geometry has been used to manufacture PLA Hat-wall honeycombs{cite(42)} and PolyJet multiphase
  fracture panels.{cite(46)}{cite(49)} Their measured performance came from the complete specimen, topology,
  materials, interfaces, dimensions, process, and loading, not from the export format. Monotile kirigami
  currently establishes deployable geometry theoretically and computationally; force, fatigue, thickness,
  and fabrication-tolerance tests remain open.{cite(51)}
</p>
""",
            ),
            Section(
                "Choosing and preparing an export",
                2,
                """
<ul>
  <li><strong>SVG/DXF:</strong> planar outlines for laser, waterjet, router, plotter, or print. Confirm units,
  closed paths, winding, duplicate edges, and whether shared edges should be cut once.</li>
  <li><strong>STL:</strong> watertight triangulated solids for printing. STL carries no reliable units,
  materials, hierarchy, or instance semantics, so include a manifest.</li>
  <li><strong>GLB:</strong> compact meshes, materials, and scene transforms for review or instancing. Check
  axis convention, transform baking, normals, and material licensing.</li>
  <li><strong>CSV/JSON:</strong> tile IDs, labels, parent clusters, positions, rotations, scale, and source
  version for CAM, robotics, or custom scripts. Publish a schema and coordinate convention.</li>
</ul>
""",
            ),
            Section(
                "Tolerance, kerf, grout, and chirality",
                2,
                f"""
<p>
  <strong>Kerf</strong> is material removed by a cutting beam or tool. Offset toolpaths by the measured
  kerf, not the nominal machine setting, and cut a multi-tile coupon before a full sheet. For molded or
  printed parts, include shrinkage, clearance, corner radii, minimum wall thickness, and surface finish.
  For architectural tile, design the grout gap into the placement geometry; independently offsetting every
  complex outline can change which corners meet.
</p>
<p>
  Preserve handedness through export and nesting. Straight Tile(1,1) and edge-modified Spectres have
  different reflection rules,{cite(2)} while face decoration or draft angle may make even a geometrically
  flippable part one-sided. Add an orientation mark and reject accidental mirror transforms in validation.
</p>
""",
            ),
            Section(
                "Validation workflow",
                2,
                """
<ol>
  <li>Hash or version the source outline and record units, scale, patch seed/root, and generator revision.</li>
  <li>Check closed polygons, self-intersection, overlap, gaps, duplicate paths, and transform handedness.</li>
  <li>Simulate nesting and tool reach; manufacture a coupon containing representative joints and corners.</li>
  <li>Measure actual dimensions, fit, warpage, and surface quality; update compensation from measurements.</li>
  <li>Dry-assemble a numbered cluster, then archive the final files, manifest, machine settings, and inspection results.</li>
</ol>
""",
            ),
            Section(
                "Evidence and candidate directions",
                2,
                f"""
<ul>
  <li><strong>Measured in specific specimens:</strong> printed Hat honeycombs and multiphase composite
  panels, including an interdigitated derivative interface.{cite(42)}{cite(46)}{cite(49)}</li>
  <li><strong>Constructed mathematically or computationally:</strong> topologically interlocking
  Spectre-derived blocks{cite(50)} and deployable monotile kirigami.{cite(51)} These papers establish
  geometric or kinematic possibility, not structural load capacity.</li>
  <li><strong>Paper prototyping:</strong> fold-and-cut templates produce Hat, Turtle, and straight
  Tile(1,1) outlines after flat folding and one cut.{cite(67)}</li>
  <li><strong>Candidate experiment:</strong> compare aperiodic and periodic infill at matched mass, process
  parameters, and boundary conditions; do not assume resonance or strength gains in advance.</li>
  <li>Support-free printing studies, topology optimization, and surface finishing</li>
  <li>Architectural panels, molds, product surfaces, screens, and repeat-free decoration</li>
  <li>Physical prototyping and load testing of mathematically constructed three-dimensional
  topological-interlocking blocks{cite(50)}</li>
</ul>
<p>
  Origami-adjacent folding studies and flat-foldable synthesis environments show how computational tools
  explore fold-pattern spaces{cite(26)}; monotile kirigami extends this to deployable aperiodic
  sheets.{cite(51)} Mechanical performance belongs to the complete specimen, material, strut thickness,
  joints, defects, boundaries, and loading, not to the outline alone. “Monotile-inspired” lattices should be
  labeled as such when they modify the canonical geometry.
</p>
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
  Most mathematics taught in school is centuries old. The aperiodic monotile was discovered in 2023, by a
  retired print technician experimenting with paper cutouts, and its proof is genuinely deep.{cite(1)}{cite(3)}
  That combination is rare gold for educators: a frontier result whose objects fit in a student's hand.
  The National Museum of Mathematics ran public competitions and exhibits around the Hat and Spectre within
  months of publication (see {link("bibliography", "bibliography")} for links).
</p>
{FIG_EDU_HOLD_GROW}
{FIG_HIERARCHY}
""",
            ),
            Section(
                "Activities by learner stage",
                2,
                f"""
<ul>
  <li><strong>Primary / informal:</strong> sort shapes, trace boundaries, distinguish slide/turn/flip, and
  extend a supplied cluster. Ask learners to predict a fit before testing it.</li>
  <li><strong>Secondary:</strong> compare periodic and non-periodic patches, map tile orientations, count
  labels across generations, graph the Fibonacci-Lucas recurrence reported for supertiles,{cite(12)} or
  use fold-and-cut crease templates to produce Hat, Turtle, and straight Tile(1,1) outlines with one cut
  after flat folding.{cite(67)}</li>
  <li><strong>Undergraduate:</strong> implement affine transforms, validate edge contacts, build a
  substitution matrix, or compute a finite-patch Fourier transform.</li>
  <li><strong>Graduate / research:</strong> reproduce one published diffraction, mechanics, or sampling
  comparison with matched controls and a preregistered metric.{cite(35)}{cite(37)}{cite(42)}</li>
</ul>
<p>
  Existing activities provide concrete scales. Gathering 4 Gardner publishes a 488-piece hierarchical
  group build. Marcello Seri’s CC BY 4.0 workshop kit reports 657 personalized Spectres assembled in five
  hours by hundreds of participants, with bilingual booklets and wall blueprints. OEIS A363348 turns the
  hierarchy into turtle graphics: 14 terms draw one Hat, 140 draw H8, and 1,588 draw the next supertile.
  These are replicable activities, not controlled studies of learning outcomes.
</p>
{FIG_EDUCATION}
""",
            ),
            Section(
                "Misconceptions to surface",
                2,
                f"""
<ul>
  <li>“Non-periodic” does not mean random, and recurring local motifs do not make a tiling periodic.</li>
  <li>One non-periodic arrangement does not make a shape an aperiodic monotile; periodic alternatives must
  be impossible. The Miki Imura family is a useful contrast.{cite(71)}</li>
  <li>Reflection, rotation, and translation are different rigid motions. The Hat requires reflected copies;
  the strict Spectre modifies edges to exclude them.{cite(1)}{cite(2)}</li>
  <li>A finite classroom patch cannot prove an infinite theorem by appearance. It can illustrate the
  hierarchy used in a proof.</li>
</ul>
""",
            ),
            Section(
                "Assessment and reproducibility",
                2,
                """
<p>
  Assess explanations, not merely completed puzzles: can the learner define a translation period, identify
  a reflected tile, explain a metatile label, and state what a finite patch does not prove? For coding work,
  grade a small validation report alongside the image.
</p>
<p>
  Publish the exact outline, scale, patch root or seed, generation, clipping rule, palette key, software
  version, and license. Photograph or export the completed patch and report missing or forced pieces.
  These records let another class reproduce the activity and distinguish a geometry error from an
  instructional outcome.
</p>
""",
            ),
            Section(
                "Limits and extensions",
                2,
                """
<p>
  Manipulatives privilege visual and motor access; pair them with high-contrast, tactile, large-print, and
  screen-readable alternatives. Do not present an application proposal as settled science. A useful final
  assignment is to classify statements as theorem, published measurement, simulation result, or hypothesis,
  then trace each supported statement to its source.
</p>
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
                "Sampling without a repeating grid",
                2,
                f"""
<p>
  Sampling means measuring a field at selected locations. On a regular grid, detail finer than the spacing
  can masquerade as a false coarse pattern: this is <strong>aliasing</strong>. In an antenna or microphone
  array, the analogous false directions are <strong>grating lobes</strong>, extra beams caused by repeated
  element spacing. Random layouts spread these errors but introduce variance. Aperiodic monotile layouts
  offer a deterministic third geometry with no translational lattice.{cite(6)}
</p>
{FIG_SIGNAL}
<p>
  Mordret and Grushin tested Hat-family arrays against periodic and other aperiodic baselines and reported
  improved aliasing behavior for the studied spatial-sampling tasks.{cite(37)} This is evidence for those
  array definitions, apertures, and metrics, not a universal theorem that every monotile sampling pattern is
  optimal. Tile centroids, vertices, or edges produce different point sets and spectra.
</p>
""",
            ),
            Section(
                "Evidence from array studies",
                2,
                f"""
<p>
  Ref.&nbsp;37 compares finite arrays through array-response functions and synthetic seismic
  beamforming, not image reconstruction. For roughly 310-sensor single-source arrays, favorable Tile(p)
  windows narrowed to p=0.41-0.43, 0.495-0.505, and 0.57-0.59, with sidelobes more than 2.5 times below the
  tested regular arrays. Hat and Turtle counterexamples show that aperiodicity alone is insufficient; the
  unusually uniform distance and azimuth distributions mattered.{cite(37)} A separate simulated Hat
  subarray retained about 90% aperture efficiency and grating lobes below −14 dB over ±18°; it has no
  fabricated-array validation.{cite(38)} A pending 85-element, 31-GHz SATCOM patent is a proposal, not
  experimental evidence.{cite(68)}
</p>
{FIG_PHYSICS_ARRAYS}
""",
            ),
            Section(
                "Benchmark design",
                2,
                """
<p>
  Compare equal aperture, sensor count, minimum spacing, and noise budget. Baselines should include square
  and hexagonal grids, jittered grids, blue-noise or Poisson-disk samples, a random ensemble, and another
  deterministic aperiodic set. Repeat random baselines with multiple seeds.
</p>
<ul>
  <li><strong>Imaging:</strong> reconstruction error, modulation transfer, artifact energy, robustness to
  missing sensors, and compute cost.</li>
  <li><strong>Arrays:</strong> peak sidelobe and grating-lobe level, beam width, scan range, aperture
  efficiency, calibration sensitivity, and mutual coupling.</li>
  <li><strong>Provenance:</strong> publish the canonical patch, selected point decoration, boundary mask,
  units, transforms, solver settings, and code.</li>
</ul>
""",
            ),
            Section(
                "Candidate experiments",
                2,
                f"""
<ul>
  <li>Sampling theory: compare monotile centroids against grids, jittered grids, blue noise, and Penrose
  point sets in reconstruction benchmarks</li>
  <li>Sensor arrays: radar, sonar, ultrasound, MRI, and CT geometry studies where periodic spacing can
  create directional ambiguities; each modality needs its own forward model.</li>
  <li>Compressed sensing: deterministic non-periodic measurement patterns with stable addressing</li>
  <li>Anti-aliasing masks and halftone screens; see {link("aliasing", "Aliasing")} and {link("moire", "Moiré")}</li>
</ul>
""",
            ),
            Section(
                "Limitations",
                2,
                """
<p>
  No layout escapes sampling theory: insufficient density still loses information. Aperiodic arrays can
  have strong non-lattice spectral peaks, awkward wiring, edge bias, unequal nearest-neighbor spacing, and
  difficult calibration. Finite aperture and the chosen decoration may matter more than the tile theorem.
  Claims should therefore name the signal class, baseline, aperture, metric, and tested patch.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="waves-and-photonics",
        title="Waves, acoustics, and photonics",
        summary="Non-repeating tiled surfaces for scattering, diffraction, and waveguide studies, now with experimental results.",
        categories=["Research frontiers"],
        see_also=["materials-science", "signal-processing", "diffraction-and-dynamical-spectrum",
                  "dimers-and-constrained-models"],
        infobox={
            "Status": "Active research (experimental)",
            "Landmark": "Chiral Hat diffraction measured (2026)",
        },
        sections=[
            Section(
                "How tiled geometry affects waves",
                2,
                f"""
<p>
  <strong>Diffraction</strong> is the far-field pattern produced when waves scatter from many features.
  <strong>Scattering</strong> means that an obstacle redirects part of a wave. A structure is
  <strong>chiral</strong> when it has a handedness that cannot be aligned with its mirror image. A
  monotile point or resonator array can therefore change which directions and frequencies reinforce,
  cancel, or respond differently to opposite handedness.
</p>
<p>
  Moritake, Takiguchi, Aihara, and Notomi fabricated a <strong>Hat-centroid quasilattice</strong>: circular
  holes of radius 100&nbsp;nm were placed at tile centroids in an H6 Hat metatile, then etched into a
  350-nm silicon-nitride film. The roughly 500 × 500&nbsp;μm sample contained 372,100 holes; the
  pseudo-period <em>a</em> was swept from 600 to 750&nbsp;nm. Illumination used a 532-nm laser expanded
  to about 1&nbsp;mm, exceeding the patterned area, with diffraction recorded 75&nbsp;mm downstream. It
  was not a Spectre-shaped material lattice. The measured far field showed sharp,
  illumination-position-independent Bragg peaks, a sixfold pinwheel whose twist relative to radial
  directions was 15.52°, a sign reversal under mirroring, and a response that changed relative peak
  intensity (but not peak position) under left- versus right-circular polarization. Honeycomb and Penrose
  controls did not reproduce the Hat-specific chiral pinwheel.{cite(19)}
</p>
<p>
  Those observations establish long-range quasiperiodic order and planar chirality for that point
  decoration under ordinary Maxwell electrodynamics. Finite-aperture Fourier transforms cannot exclude
  continuous spectral weight, so position-independent Bragg peaks support long-range order without by
  themselves proving pure-point diffraction. The diffraction had C6 intensity symmetry through
  Friedel’s law even though the centroid set had exact C3 rotational symmetry without mirror symmetry.
  A Fourier transform of the measured point coordinates reproduced the peak positions; finite hole size
  reduced high-wavevector intensity relative to ideal delta-function calculations.{cite(19)} The broader
  theoretical foundation is the quasicrystalline diffraction structure of Hat-family tilings.{cite(6)}
</p>
{FIG_WAVES}
{FIG_WAVE_PROP}
{FIG_PHYSICS_DIFFRACTION}
<p>
  Condensed-matter theory adds depth: an ideal nearest-neighbor tight-binding model on the Hat vertex graph
  (mean coordination ≈2.31, mean bond length ≈1.37<em>a</em>) has graphene-like features and a macroscopic
  zero-energy manifold of compact localized states, many concentrated around reflected “anti-hat”
  environments, under specified hopping and flux choices,{cite(20)}
  Ising spins on the underlying kite graph order with critical temperatures
  <em>T</em><sub>c</sub>/<em>J</em>=2.405±0.0005 and <em>T</em><sub>c</sub><sup>*</sup>/<em>J</em>=2.143±0.0005
  while satisfying Kramers-Wannier duality to 1.000±0.001 and collapsing with ordinary 2D Ising
  exponents,{cite(21)}
  and dimer statistics on a regularized Spectre graph admit the exact count
  Z=2<sup>N<sub>Mystic</sub>+1</sup>.{cite(22)} Together these establish that monotile geometry changes wave
  and lattice physics, the open question is where that change is useful. Experimental polariton
  realizations on monotile lattices now show Bragg peaks and long-range coherence,{cite(40)} with theory
  predicting critical states and anomalous transport in related optical setups.{cite(41)} Tile-shape
  geometry can tune topological phases and the quantum geometric tensor in model systems: one geometric
  parameter continuously connects Chevron, Spectre, Turtle, and Comet, with a reported bulk Chern marker
  C≈0.98 at ℓ=0.33 and survival under onsite disorder through roughly <em>W</em>/<em>t</em>≤1.{cite(39)}
</p>
""",
            ),
            Section(
                "Established experiments and theory",
                2,
                f"""
<p>
  Peer-reviewed experimental evidence includes fabricated chiral diffraction from a Hat-centroid
  quasilattice.{cite(19)} A separate experimental preprint reports a finite, optically written
  aperiodic polariton realization with Bragg peaks and coherence.{cite(40)} Rigorous and
  numerical work describes Hat/Spectre diffraction,{cite(6)}{cite(33)}{cite(35)} a Hat-graph tight-binding
  model,{cite(20)} and predicted critical transport in a related polariton proposal.{cite(41)}
  These studies use different physical decorations; they should not be merged into one generic “Spectre
  material” claim.
</p>
<p>
  In the polariton preprint, a spatial light modulator writes finite Hat-vertex pump arrays with
  M=1, 4, and 13 tiles into a GaAs microcavity. At about 1.15 times threshold, the M=13 array shows narrow
  C6 peaks; changing characteristic spacing from D=27.2 μm to 22.6 μm changes favored nearest-neighbor
  locking from in-phase to out-of-phase. Periodic triangular and Penrose arrays are controls. This is a
  driven-dissipative experiment under preprint review, not a passive bulk material.{cite(40)}
</p>
<p>
  Ref.&nbsp;41 is a prediction, not an experiment. A finite-difference polariton model with Gaussian
  scatterers at Hat vertices finds critical states near low-energy pseudogaps and representative transport
  exponents ν≈0.72 and ν≈0.40. Finite-grid mismatch affects the superdiffusive front, and comparable
  behavior in Penrose calculations leaves monotile specificity unresolved.{cite(41)}
</p>
""",
            ),
            Section(
                "Simulation and measurement workflow",
                2,
                f"""
<p>
  The HLV optical benchmark protocol supplied to this project is useful here only as a
  <strong>claim-disciplined methods template</strong>. It correctly treats the Hat diffraction experiment
  as a positive control for Fourier and full-wave solvers, not as evidence for HLV. Its broader HLV carrier,
  phase-channel, and memory-channel proposals are unpublished and unvalidated.{cite(74)}
</p>
<ol>
  <li>Select the physical decoration, points, holes, resonators, struts, or material domains, and state how
  it is derived from the canonical tiling.</li>
  <li>Match periodic, random, and alternative aperiodic controls by area fraction, feature count, minimum
  spacing, material, thickness, and outer boundary.</li>
  <li>Converge finite-element, finite-difference time-domain, or boundary-element meshes and absorbing
  boundaries; sweep patch size to separate bulk behavior from edge effects.</li>
  <li>Report transmission/reflection spectra, angular scattering, polarization or handedness contrast,
  quality factor, loss, uncertainty, and raw geometry.</li>
  <li>Fabricate and image the sample, measure dimensional disorder, and feed the as-built geometry back
  into the model.</li>
</ol>
<p>
  A rigorous benchmark should lock geometry and metrics before target runs, separate calibration,
  validation, and sealed holdouts, and include matched nulls: honeycomb, Penrose, radial-phase-randomized,
  pair-correlation-matched, and mirrored structures. Mirror reversal, polarization response, aperture
  scaling, and illumination-position invariance should be explicit gates. A visually striking pinwheel is
  not enough; the target must predict held-out observables better than equally flexible conventional
  alternatives.{cite(19)}{cite(74)}
</p>
""",
            ),
            Section(
                "Candidate applications",
                2,
                f"""
<ul>
  <li>Acoustic diffusers and panels tested for angular uniformity and flutter-echo reduction</li>
  <li>Photonic and phononic structures with engineered chiral response</li>
  <li>Antenna and metasurface layouts that suppress grating lobes{cite(38)}</li>
  <li>Simulation-ready polygon exports for comparing periodic, random, and aperiodic boundaries in FDTD/FEM</li>
</ul>
""",
            ),
            Section(
                "Limitations and open questions",
                2,
                """
<p>
  Aperiodicity does not guarantee a band gap, isotropic scattering, low sidelobes, or useful chirality.
  Response depends on wavelength-to-feature ratio, losses, coupling, boundary, disorder, and the selected
  points or domains. Acoustic and electromagnetic analogies are helpful only after their boundary
  conditions and constitutive physics are specified. The main open engineering task is to identify where a
  canonical monotile layout beats well-tuned periodic, random, and established quasicrystal controls.
</p>
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
        infobox={"Status": "Active research", "Evidence base": "Experiments, simulation, and theory"},
        sections=[
            Section(
                "Geometry as a material parameter",
                2,
                f"""
<p>
  Engineers tune performance by changing geometry: pores, channels, lattices, electrodes, exchangers, and
  support structures. Periodic geometries bring resonances and preferred failure planes; random geometries
  bring variance and poor reproducibility. Aperiodic monotile arrays give a controlled middle path,
  deterministic, manufacturable from a single element, and provably free of translational symmetry.{cite(2)}
</p>
{FIG_MATERIALS_SCIENCE}
<p>
  The evidence that this matters physically is accumulating: a specified tight-binding spectrum on the Hat
  vertex graph,{cite(20)} modified phase behavior for spins,{cite(21)} distinctive dimer combinatorics,{cite(22)}
  and measured chiral optical response.{cite(19)} Related lattice families from Sturmian systems{cite(13)}
  and iterated function systems{cite(14)} extend the design space beyond the monotile itself.
</p>
<p>
  Mechanical evidence is substantial but heterogeneous. It includes printed Hat-wall honeycombs,{cite(42)}
  numerical continuum limits,{cite(43)} Tile(<em>a,b</em>) parameter sweeps,{cite(44)} ideal beam
  networks,{cite(45)} multiphase fracture panels,{cite(46)}{cite(49)} and three-dimensional lattices that
  are only <em>inspired</em> by monotiles.{cite(64)}{cite(65)} Those are different specimens and different
  claims. The sections below keep their materials, controls, methods, and evidence levels separate.
</p>
<p class="ref-note">
  Several papers label new lattices “einstein monotile” while using geometry <em>inspired by</em> rather
  than identical to Smith’s Hat or Spectre, see refs.&nbsp;[62] and [64]-[65]. Always verify whether a
  source uses canonical tile outlines or a derivative mesh.
</p>
""",
            ),
            Section(
                "Canonical Hat-family honeycombs",
                2,
                f"""
<p>
  <strong>Poisson’s ratio</strong> measures sideways strain under axial loading. Clarke and colleagues
  printed 50 × 50 × 50&nbsp;mm PLA cellular specimens whose walls followed a finite Hat tiling. An
  Ultimaker&nbsp;S3 deposited two-toolpath, 0.5&nbsp;mm walls through a 0.4&nbsp;mm nozzle in
  0.2&nbsp;mm layers. ASTM&nbsp;D1621 compression used a 50&nbsp;kN Instron load cell at
  0.5&nbsp;mm/min to 25% strain; digital image correlation used 31-pixel subsets. Relative-density and
  orientation sweeps were compared with a hexagonal honeycomb. The Hat architecture returned Poisson
  ratios of 0.010-0.048 above relative density 0.225 and 0.018-0.075 at or below it.{cite(42)} “Zero”
  here means experimentally near zero for these finite specimens, not an exact property of every
  Hat-shaped object.
</p>
{FIG_MATERIALS_COMPRESSION}
<p>
  Rieger and Danescu asked a different question: whether increasingly large ideal Hat networks approach
  continuum isotropy. In spring-and-angle and Timoshenko-beam simulations, the mean anisotropy index fell
  from about 6.8 × 10<sup>−2</sup> at radius 10<em>a</em> to 4.3 × 10<sup>−4</sup> at
  300<em>a</em>, using ten realizations at each scale.{cite(43)} The first seven inflation generations
  contain 4, 25, 169, 1,156, 7,921, 54,289, and 372,100 polygons, which helps explain the slow approach
  to a continuum response. This is a computational scale-limit result; a small printed panel can remain
  boundary-dominated and direction-dependent. The demonstrated Timoshenko-beam convergence also used an
  internal beam scale comparable to the tile edge. The more realistic slender-beam regime remains open.
</p>
{FIG_MATERIALS_CONVERGENCE}
<p>
  The continuous Tile(<em>a,b</em>) family adds geometry as a design variable. Selected experiments and a
  larger computational map found Poisson ratios from about 0.006 to 0.491 and normalized moduli from
  approximately 0.003 to 0.056 across relative densities near 0.2-0.4.{cite(44)} Hat is
  Tile(1,√3); the family’s Tile(0,1), Tile(1,1), and Tile(1,0) endpoints admit periodic tilings even
  though generic intermediate members are aperiodic. Hat and Tile(1,1) entered a smooth,
  bending-dominated plateau, while other tested family members showed an initial stress drop; endpoint
  designs began densifying near 15% strain, versus roughly 25% for the other cases. Separate finite-element
  comparisons of Hat-, Turtle-, and straight-Spectre-type beam lattices at 10-40% relative density found
  nearly isotropic effective moduli, while some Hat cases retained direction-dependent negative Poisson
  ratios.{cite(45)} Isotropic stiffness and isotropic lateral contraction are therefore separate claims.
</p>
""",
            ),
            Section(
                "Multiphase composites and interlocking interfaces",
                2,
                f"""
<p>
  Jung, Chen, and Gu assigned rigid VeroClear to tile interiors and soft TangoBlackPlus to boundaries in
  50 × 125 × 3&nbsp;mm PolyJet panels with a 10&nbsp;mm notch. At least three specimens per design were
  pulled at 2&nbsp;mm/min and compared with periodic honeycomb and square-grid controls, including rotated
  controls and translated or rotated crack placements. For the published 80% stiff-phase comparison, the
  selected aperiodic panels averaged about 130% higher modulus, 65.2% higher strength, and 31.6% higher
  toughness than HC80, with more tortuous crack paths.{cite(46)} (An earlier preprint reported smaller
  gains, so values should always be tied to the cited version.) Fracture stayed within TangoBlackPlus
  rather than following a VeroClear-interface debond. Longer initial notches reduced modulus, strength,
  and toughness, and simulated crack paths diverged from experiments because print anisotropy and defects
  were omitted. The headline result therefore belongs to those phases, crops, notches, and controls.
</p>
{FIG_MATERIALS_FRACTURE}
<p>
  Follow-on work uses Gaussian-process regression to navigate a larger simulated composite family and
  estimate uncertainty,{cite(47)} while curved chiral interfaces introduce curvature as another variable
  affecting interface length, connectivity, and stress concentration.{cite(48)} These are design and
  optimization studies, not independent demonstrations that any curved Spectre outline is stronger.
</p>
<p>
  A bio-inspired interlocking derivative produced the largest reported fracture gain in this literature.
  Its rigid and ductile phases met along strongly interdigitated monotile-derived edges. The selected
  specimen reached roughly 20 times the fracture resistance of its honeycomb control, six times that of
  the straight-edge aperiodic control, and 148% more than a semicircular-edge variant.{cite(49)} The control
  ladder shows that local key-and-socket geometry and global layout both matter. This is evidence for that
  engineered interface, not a twentyfold advantage of the canonical Hat or Spectre.
</p>
{FIG_MATERIALS_INTERLOCKING}
""",
            ),
            Section(
                "Minimal surfaces, networks, and polycrystal analogues",
                2,
                f"""
<p>
  Daynes generated smooth <strong>aperiodic minimal-surface shells</strong> inside monotile-derived cells
  and swept orientation, local configuration, topology, density, and representative-volume size with
  finite-element analysis. Selected designs approached in-plane stiffness isotropy, and variance decreased
  as the modeled region grew; Gaussian-process models predicted modulus and anisotropy with uncertainty.
  These structures are not conventional triply periodic minimal surfaces, and the study reports no printed
  strength, thermal, acoustic, or band-gap experiment.{cite(60)}
</p>
<p>
  Holden and Vasil provide a more general continuum bridge. Starting from diffusion or wave equations on
  dense metric graphs with Kirchhoff node conditions, they derive a coarse-grained PDE retaining local
  conductivity, capacity, and vertex density. Periodic, random, and aperiodic-monotile graphs are numerical
  convergence examples.{cite(63)} The framework can guide future heat, sound, or transport models, but it
  is not itself a measurement of any of those properties.
</p>
<p>
  A phase-field study instead interprets a monotile pattern as an initial grain-boundary map. Under its
  idealized two-dimensional grain-growth law, boundaries migrate and junctions reorganize, so the imposed
  network does not remain an equilibrium polycrystal.{cite(61)} “Instability” here means microstructure
  evolution in that model, not mechanical failure of a Hat lattice or spontaneous Hat grains in an alloy.
</p>
""",
            ),
            Section(
                "Monotile-inspired three-dimensional derivatives",
                2,
                f"""
<p>
  Several high-performing structures borrow aperiodic organization without preserving a canonical tile.
  A semi-re-entrant derivative is studied through compression, bending, energy absorption, and
  Poisson-ratio evolution; it is an auxetic-lattice paper, not evidence of a phononic band gap.{cite(62)}
</p>
<p>
  Printed aperiodic-unit-cell microlattices were compared with selected periodic microlattices at matched
  relative density. The DLP specimens used Standard Gray&nbsp;8K resin. Strut thicknesses of
  0.4-0.8&nbsp;mm produced relative densities from 0.0971 to 0.3441; the baseline was 0.206. Against
  simple-cubic, FCC, and BCC controls, the reported design achieved at least 830% higher fracture strain,
  300% higher energy absorption, 130% higher crushing-stress efficiency, and a 160% higher smoothness
  metric; after recovery from 30% compressive strain it retained 76% of ultimate stress.{cite(64)}
  Periodic controls developed catastrophic buckling, detachment, or diagonal shear bands around
  0.1 strain, whereas the aperiodic derivative spread deformation across local bands and then compacted.
  These numbers belong to that three-dimensional truss, resin, density range, and recovery protocol.
</p>
{FIG_IMPACT_FRONT}
{FIG_IMPACT_OBLIQUE}
{FIG_IMPACT_LATERAL}
<p>
  Those loops are schematic impact illustrations on a monotile sheet, useful intuition for why
  energy-absorption and crushing studies matter to vehicle / protective-structure research, not a
  substitute for instrumented crash tests. Keep them next to the measured lattice numbers above.
</p>
<p>
  A related interpenetrating-phase composite combines an additively manufactured Ti-6Al-4V truss with
  epoxy infiltration in roughly 24.75 × 24.85 × 25&nbsp;mm specimens. Selective-laser-melted
  Ti-6Al-4V struts ranged from 500 to 860&nbsp;µm before vacuum-assisted epoxy curing. Its strongest tested
  configuration reported a 246.61% compressive-strength increase and specific energy absorption of
  46.2&nbsp;J&nbsp;g<sup>−1</sup>. In an equal-mass comparison, the composite used 13.75% titanium plus
  86.25% epoxy against a 36.74% titanium-only lattice, increasing strength by 221.91%, plateau strength by
  215.7%, and specific energy absorption by 185.39%.{cite(65)} The polymer suppressed abrupt stress drops,
  delayed densification toward 0.6 strain, and distributed damage, although the highest-strut-fraction
  specimen still fluctuated. Metal-printing defects, infiltration, interface adhesion, density, and damage
  sequencing are inseparable from that result. Both studies should be called
  <strong>monotile-inspired</strong>, not direct tests of the two-dimensional monotile theorem.
</p>
""",
            ),
            Section(
                "Wave and electronic evidence",
                2,
                f"""
<p>
  Hat-graph tight-binding models show distinct electronic and wave behavior under specified couplings,{cite(20)} and Spectre/Hat work covers
  dimers, spins, diffraction, and tunable quantum geometry.{cite(21)}{cite(22)}{cite(35)}{cite(39)} A fabricated
  Hat-centroid quasilattice has measured chiral diffraction.{cite(19)} These results concern specified
  graphs or resonator decorations, not the bulk chemistry of a Hat-shaped solid.
</p>
""",
            ),
            Section(
                "Fluid and thermal candidates",
                2,
                """
<ul>
  <li>Porous media and heat exchangers: compare pressure drop, mixing, heat-transfer coefficient, hot spots,
  fouling, and manufacturability at matched porosity and hydraulic diameter.</li>
  <li>Electrodes and catalysts: compare accessible area, tortuosity, transport, current distribution, and
  degradation against periodic and stochastic networks.</li>
  <li>Microfluidics and surface texture: test residence-time distribution, recirculation, dispersion, drag,
  and sensitivity to fabrication error. These remain proposals unless linked to direct measurements.</li>
</ul>
""",
            ),
            Section(
                "Controls and geometry provenance",
                2,
                """
<p>
  Match density, feature-size distribution, connectivity, boundary shape, constituent material, and
  manufacturing process before attributing a result to aperiodic order. Sweep patch size and orientation;
  report defects and confidence intervals. Periodic, randomized, and non-monotile quasicrystalline controls
  answer different questions and should not be collapsed into one baseline.
</p>
<p>
  Preserve the canonical polygon and transform table when the research question is about the Hat or
  Spectre. If struts are curved, cells merged, vertices moved, or a 3D lattice merely borrows the silhouette,
  call it <strong>monotile-inspired</strong>. Refs.&nbsp;62, 64, and 65 are examples where that distinction
  matters.
</p>
""",
            ),
            Section(
                "Limitations",
                2,
                """
<p>
  Removing translational symmetry does not remove weak directions, resonances, stress concentrations, or
  processing defects. Benefits may disappear after matching density or boundary conditions. A canonical
  pattern may also be inferior to an optimized derivative. Treat geometry as one design variable, publish
  negative results, and reserve general claims for studies that span multiple patches and controls.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="robotics-and-mobility",
        title="Robotics and mobility",
        summary="Aperiodic surfaces and sensor layouts as localization substrates, coverage geometry, and sampling arrays.",
        categories=["Research frontiers"],
        see_also=["signal-processing", "aliasing", "algorithms-and-machine-learning"],
        infobox={
            "Status": "Research frontier with deep antecedents",
            "Key benefit": "Position-informative local patches; regenerable maps",
            "Sensors": f'{link("signal-processing", "Signal processing and imaging")}',
        },
        sections=[
            Section(
                "The localization argument",
                2,
                f"""
<p>
  Periodic floors are hostile to visual localization: every cell looks like every other cell, so a downward
  camera learns almost nothing about <em>where</em> it is. Random textures are locally distinctive but
  cannot be regenerated, queried, or shared as a ground-truth map across labs. An aperiodic monotile
  surface sits in the useful middle. Finite motifs recur, but within a <em>fixed finite mapped patch</em>, a
  sufficiently large local neighborhood can identify position. A robot that reads enough of the local tile
  configuration can therefore test absolute-pose lookup against a map generated from the same patch.
</p>
{FIG_ROBOTICS_POSE}
<p>
  This is not only a 2023 idea. Autonomous-robot localization from aperiodic floor patterns was already
  proposed for Penrose-like tilings in the 1990s: scan a local patch, decode position from configuration,
  and improve precision as the scanned neighborhood grows. The accessible record is an antecedent and
  implementation discussion, not a modern controlled pose benchmark.{cite(72)} Monotiles sharpen the same program: one prototile, no
  matching rules to paint, stable IDs and affines for every tile, and regenerable patches for any arena size
  from {link("resources-and-tools", "generators")} such as
  <a href="https://aperiodicgenerator.com/" rel="noopener noreferrer">aperiodicgenerator.com</a>.
</p>
""",
            ),
            Section(
                "Sensors, arrays, and sampling",
                2,
                f"""
<p>
  Robotics is not only cameras on floors. Where you <em>place</em> sensors, lidar stations, microphones,
  ultrasonic beacons, pressure taxels, RF nodes, is a spatial sampling problem. Periodic lattices alias;
  purely random deployments are hard to certify. Aperiodic monotile centroids and adjacency graphs give
  <strong>ordered, non-repeating sample layouts</strong> with documented spectral advantages over regular
  grids for wavefield sampling and beamforming.{cite(37)} That literature lives on
  {link("signal-processing", "Signal processing and imaging")} and
  {link("aliasing", "Aliasing")}; robotics inherits it for:
</p>
<ul>
  <li><strong>Multi-robot and WSN coverage</strong>, test centroid layouts for coverage holes and
  directional bias against regular, random, and blue-noise placements.</li>
  <li><strong>Active sensing footprints</strong>, compare hierarchy-following paths with lawnmower and
  spiral paths for travel cost, revisit time, vibration spectra, and wear.</li>
  <li><strong>Tactile and force arrays</strong>, taxel layouts without a single lattice frequency, so
  slip and contact signatures do not lock to the sensor grid.</li>
</ul>
""",
            ),
            Section(
                "SLAM, planning, and shared benchmarks",
                2,
                f"""
<p>
  Because every patch regenerates exactly from a seed, an aperiodic arena is a <strong>shared
  benchmark terrain</strong>: two labs can print or project the same floor, publish trajectories against
  the same tile IDs, and compare SLAM or planning papers without arguing about texture randomness.
  Adjacent algorithmic work can extract repeated rectangular forms from exact finite symbolic grids; it
  does not recover polygonal tilings from camera fragments.{cite(25)} SAT methods can search finite
  polyform placement spaces at scale.{cite(17)} Hierarchical tile counts
  (Fibonacci / Lucas signatures) give multi-scale statistical fingerprints a localizer can use when
  vision is partial.{cite(12)}
</p>
<p>
  Open problems that serious roboticists will recognize as load-bearing:
</p>
<ul>
  <li>How large a neighborhood must a downward camera see to uniquely identify pose under occlusion,
  dirt, and lighting change?</li>
  <li>Can substitution hierarchy be used as a coarse-to-fine localization cascade (cluster → tile →
  sub-vertex)?</li>
  <li>What happens to visual odometry drift on aperiodic vs checkerboard floors at the same spatial
  frequency content?</li>
  <li>How should motion planners exploit unique corridors without reintroducing periodic cost maps?</li>
</ul>
""",
            ),
            Section(
                "Mechanics and contact",
                2,
                f"""
<ul>
  <li>Grasping and traction textures tested for directional slip and wear, related to aperiodic lattice
  mechanics in {link("materials-science", "Materials science and fluids")}</li>
  <li>Tire tread, road surface, and rail-bed studies where periodic patterns excite resonance</li>
  <li>Soft-robot skin layouts and conformal sensor meshes derived from clipped monotile patches</li>
  <li>Deployable / folding mobility structures; flat-foldability synthesis points the way{cite(26)}{cite(51)}</li>
</ul>
<p>
  These are proposed tests, not established monotile advantages. Use matched roughness, material, load,
  speed, and tread geometry, and report whether the canonical tiling or only an inspired texture was used.
</p>
""",
            ),
            Section(
                "Limits and validation",
                2,
                f"""
<p>
  Localization depends on field of view, patch boundary, repeated finite motifs, occlusion, illumination,
  camera calibration, wear, and map accuracy. Ref.&nbsp;72 establishes the broader feasibility of position
  detection from an aperiodic tiling, not turnkey performance for Hat or Spectre floors.{cite(72)} A useful
  benchmark reports pose error and failure rate versus visible neighborhood size, then tests held-out
  starts, rotated cameras, missing lines, dirt, and changed lighting.
</p>
<p>
  Sensor-layout and contact proposals inherit ordinary constraints: wiring, minimum spacing, repair,
  traction, drainage, and safety. Aperiodicity is a layout property, not a guarantee of observability,
  coverage, security, or mechanical advantage.
</p>
""",
            ),
        ],
    ),
    # ------------------------------------------------------------------ #
    Article(
        slug="biology-and-medicine",
        title="Biology and medicine",
        summary="Geometric scaffolds for packing, growth, folding, implant design, and concrete navigation experiments.",
        categories=["Research frontiers"],
        see_also=["materials-science", "robotics-and-mobility", "education"],
        infobox={"Status": "Research frontier", "Suggested experiment": "Aperiodic mouse / rodent maze"},
        sections=[
            Section(
                "Clean scaffolds for messy questions",
                2,
                f"""
<p>
  Natural systems are full of packing, branching, growth, folding, and surface constraints, and they are
  conspicuously non-periodic. Aperiodic monotile patches are not biological models by default, but they are
  clean geometric scaffolds for asking better questions: what does growth on a structured-but-non-repeating
  substrate look like? How do cells or crystals pack when the template forbids periodicity?{cite(6)}{cite(13)}
</p>
{FIG_BIOLOGY}
<p>
  For implants and tissue scaffolds the mechanical argument mirrors {link("materials-science", "materials science")}:
  aperiodic strut layouts avoid the aligned failure planes and resonances of periodic lattices while
  remaining fully specified for regulatory review, every strut position is deterministic and
  documentable.{cite(2)}
</p>
""",
            ),
            Section(
                "Suggested experiment: the aperiodic mouse maze",
                2,
                f"""
<p>
  Spatial navigation labs already know that cue layout changes behavior: radial-arm mazes, Barnes mazes,
  and Morris water mazes carefully control distal landmarks because rodents (and their place / grid cell
  systems) exploit them. An aperiodic monotile floor or wall field is a stronger, still controllable
  intervention: within a fixed mapped arena, a sufficiently large neighborhood may identify location even
  though smaller motifs recur. That creates fewer exact local ambiguities than a checkerboard or brick
  floor, but the required field of view must be measured.
</p>
<p>
  A concrete protocol sketch:
</p>
<ol>
  <li><strong>Build two matched arenas</strong> of equal area and wall height, one with a periodic tile
  or grid floor, one with a Spectre / Tile(1,1) patch generated for the exact footprint (same tile count
  order of magnitude, same contrast paint).</li>
  <li><strong>Train rodents on a goal location</strong> (food / escape / platform) with identical distal
  room cues in both arenas.</li>
  <li><strong>Probe under cue conflict</strong>: rotate or shift a local floor region, or start the animal
  from a geometrically analogous but non-identical monotile neighborhood. Ask whether path efficiency,
  heading error, and re-orientation latency differ between periodic and aperiodic floors.</li>
  <li><strong>Optional electrophysiology / imaging</strong>: compare place-field stability and remapping
  when the animal revisits a visually similar corridor that is <em>not</em> the same tile neighborhood
  (impossible to arrange cleanly on a periodic lattice).</li>
</ol>
<p>
  The point is not that brains “use monotiles.” It is that monotile geometry gives experimentalists a
  regenerable, ID-addressable landmark field whose position information can be quantified, the same reason
  {link("robotics-and-mobility", "robotics")} cares about aperiodic floors for localization.{cite(72)}
</p>
""",
            ),
            Section(
                "Controls, confounds, and ethics",
                2,
                """
<p>
  This is a hypothesis-driven protocol, not evidence that rodents navigate better on monotile cues. Use a
  counterbalanced or randomized design, preregister primary outcomes and exclusions, blind scoring where
  possible, and estimate sample size before collection. Include a uniform-floor control as well as periodic
  and aperiodic conditions, and equalize luminance, contrast, odor, traction, cleaning, reward schedule,
  handling, arena geometry, and distal cues.
</p>
<p>
  Floor patterns can change anxiety, visual salience, or movement independently of spatial coding. Track
  speed, thigmotaxis, freezing, and visual acuity; test whether the animal can resolve the feature scale.
  Animal work requires institutional ethics approval, refinement to minimize stress, humane endpoints, and
  reporting under applicable animal-research standards. Projected or virtual cues may answer preliminary
  questions without changing floor mechanics.
</p>
""",
            ),
            Section(
                "Scaffolds and candidate directions",
                2,
                """
<p>
  Mechanical scaffold results and biological outcomes are separate evidence layers. A lattice can have
  measured stiffness or fracture behavior without evidence for cell adhesion, tissue integration,
  thrombosis, infection risk, or clinical benefit. Any implant proposal must begin with material,
  sterilization, biocompatibility, fatigue, and manufacturability controls.
</p>
<ul>
  <li>Morphogenesis, shell growth, protein folding, cellular packing, and neural geometry studies</li>
  <li>Implants, prosthetics, vascular stents, tissue scaffolds, and surgical planning</li>
  <li>Crystal nucleation templates, catalysts, zeolites, and molecular cage geometry</li>
  <li>Microfluidic channel layouts without periodic recirculation traps</li>
  <li>Behavioral arenas for insects and fish with regenerable aperiodic visual texture</li>
</ul>
""",
            ),
            Section(
                "Limits and reporting",
                2,
                """
<p>
  Aperiodic monotiles are designed mathematical objects, not a general model of biological irregularity.
  Similar-looking branching or packing is not evidence of a shared mechanism. Report canonical versus
  inspired geometry, feature scale, boundary, defects, and negative results; label behavioral, cellular,
  fluidic, and implant ideas as proposals until directly tested.
</p>
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
        see_also=["robotics-and-mobility", "signal-processing", "computational-generation"],
        infobox={
            "Status": "Research frontier",
            "Key property": "Structured, non-periodic, reproducible",
        },
        sections=[
            Section(
                "A structured geometric dataset",
                2,
                f"""
<p>
  A monotile patch can be represented as polygons plus affine transforms, or as a graph whose nodes are
  tiles and whose edges mean “shares a boundary.” Node features may include orientation, hierarchy label,
  area, centroid, or parent metatile. A <strong>graph embedding</strong> is a learned numeric vector that
  summarizes such a node or whole patch for prediction and comparison.
</p>
<p>
  Deterministic generation supports reproducible benchmarks, but it does not prevent memorization. Models
  can memorize finite IDs, seeds, boundaries, or recurring motifs, and web provenance is difficult to rule
  out. Splits must therefore hold out entire parent supertiles, patch regions, scales, or generator
  configurations rather than randomly splitting neighboring tiles.{cite(2)}
</p>
{FIG_ALGORITHMS}
<p>
  The theoretical backdrop is rich. Tiling problems sit at the edge of computability, translational tiling
  is undecidable for three connected polyhypercubes in four dimensions,{cite(24)} and the
  structured-vs-wild dichotomy is an open research
  program.{cite(23)} On the constructive side, SAT solvers detect isohedral polyforms,{cite(17)} exact
  algorithms extract rectangular repeated forms from exact symbolic grids,{cite(25)} and group-theoretic formulations connect
  tilings to algebra.{cite(9)} Percolation thresholds on Hat-family lattices are now being mapped by Monte
  Carlo simulation,{cite(52)} giving concrete statistical signatures for random-process models on monotile
  graphs. Batle and Bednorz extend Li-Boyle quantum error-correcting codes to Hat and Spectre tilings,
  grounding recoverability in the supertile hierarchy and CAP torus parametrization.{cite(55)}
</p>
""",
            ),
            Section(
                "Benchmark tasks and representations",
                2,
                f"""
<ul>
  <li><strong>Node/edge prediction:</strong> infer missing orientation, label, adjacency, or parent cluster
  from a partially observed graph.</li>
  <li><strong>Patch classification:</strong> distinguish canonical legal patches from overlaps, gaps,
  reflected errors, perturbed geometry, or other tiling families.</li>
  <li><strong>Localization:</strong> retrieve a query neighborhood in a larger fixed patch under noise,
  occlusion, rotation, and scale change; connect to {link("robotics-and-mobility", "robotics")}.</li>
  <li><strong>Generation:</strong> complete a legal frontier or predict the next substitution level, with
  geometric validity checked independently of pixel similarity.</li>
  <li><strong>Physics surrogate:</strong> predict a published simulation target only after preserving the
  exact graph, boundary, and material parameters used to create labels.</li>
</ul>
""",
            ),
            Section(
                "Baselines, splits, and metrics",
                2,
                """
<p>
  Baselines should include coordinate-only multilayer perceptrons, convolutional models on rasterized
  patches, message-passing graph networks, SE(2)-equivariant models, nearest-neighbor retrieval, and simple
  hierarchy rules. Compare with periodic grids, Penrose or other aperiodic tilings, and perturbed controls
  at matched node count and density.
</p>
<p>
  Use region- or supertile-held-out splits with no shared descendants across train and test. Report task
  accuracy or F1, localization distance and angular error, graph-edit or validity rate, calibration,
  robustness curves, inference time, parameter count, and seed variance. Release the generator revision,
  split manifest, normalization, and duplicate-detection procedure.
</p>
""",
            ),
            Section(
                "Algorithms and computational limits",
                2,
                f"""
<p>
  Useful non-learning methods include exact or tolerance-aware edge matching, spatial indexes over
  centroids, graph isomorphism tests, geometric hashing, SAT search, and substitution parsers.{cite(17)}
  Tiling undecidability results show that no algorithm solves every unrestricted tiling problem in the
  relevant settings,{cite(24)}{cite(56)} but they do not make routine finite-patch tasks cryptographically
  hard or justify security claims.
</p>
<p>
  Ref.&nbsp;25 is deliberately narrow: it trims and decomposes exact rectangular symbolic matrices. On a
  synthetic 6×8 mixed grid it processed four of 14 composites, extracted 20 primes, and found three
  two-placement decompositions in 8.43 ms; worst-case growth remains exponential. It does not address
  perspective, curved boundaries, measurement noise, or Hat/Spectre hierarchy recovery.{cite(25)}
</p>
<p>
  Percolation likewise requires a declared graph, site-versus-bond occupation, spanning rule, and
  finite-size scaling; a threshold belongs to that model, not to the outline alone.{cite(52)} Proposed
  Hat/Spectre quantum codes must report stabilizer construction, rate, distance, check weight, decoder, and
  threshold over growing systems; a valid finite code is not yet evidence of fault-tolerance advantage.{cite(55)}
  The operational distinctions and implementation contract are developed in
  {link("computational-generation", "Computational generation and navigation")}.
</p>
""",
            ),
            Section(
                "Limitations and crypto caution",
                2,
                """
<p>
  Results can leak through coordinates, clipping boundaries, stable IDs, generation depth, or near-duplicate
  neighborhoods. A model that succeeds on one deterministic family may only have learned its generator.
  Test out-of-distribution scales and alternative legal patches, and distinguish exact geometry from
  rasterization artifacts.
</p>
<p>
  Aperiodicity is not a cryptographic assumption. Do not use monotile geometry for keys, trapdoors,
  authentication, or obfuscation without a formal threat model, reduction or extensive cryptanalysis, and
  review by security specialists. Visual complexity and undecidable tiling theorems do not supply practical
  security.
</p>
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
        see_also=["aperiodic-monotile", "spectre-tile", "substitution-tiling",
                  "cut-and-project-and-model-sets"],
        infobox={
            "Initial idea": "Nan Ma",
            "Exposition": "Arnaud Chéritat with Nan Ma",
            "First dated artifact": "9 June 2023",
            "Ambient space": "ℝ⁴ = ℝ² × ℝ²",
            "Key distinction": "Edge lift ≠ cut-and-project proof",
        },
        sections=[
            Section(
                "A two-shadow analogy",
                2,
                f"""
<p>
  Imagine drawing one path with two transparent inks, then making a flat image by giving each ink a
  different scale. Changing those two scales changes the shadow, while the colored source path stays the
  same. Nan Ma’s lift applies this idea to the two direction classes in the Hat family: store them in two
  separate coordinate planes, producing four coordinates in total, then project back to two or three
  dimensions.{cite(54)}
</p>
<p>
  In that sense the whole Hat or Spectre tiling can be treated as a single static object in four-dimensional space.
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
  algebraic return modules, Galois conjugation, and acceptance windows, not Ma’s edge coloring.
</p>
<p>
  A third meaning of “lift” appears in architecture: van Dongen constructs three-dimensional polyhedral
  Hat and Turtle wall modules from lifted double-kites.{cite(69)} That work concerns a buildable surface
  vocabulary, not ℝ⁴ coordinates or a model set. For formal definitions and a checklist, see
  {link("cut-and-project-and-model-sets", "Cut-and-project schemes and model sets")}.
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
  reprojections plus renormalization cocycles to compute Fourier-Bohr amplitudes through fractal
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
<p>
  A practical visualization starts with a small validated Tile(<em>a,b</em>) patch, assigns the two edge
  classes contrasting colors, integrates lifted vertex coordinates, and animates a linear projection to
  3D. Show the original 2D patch beside the projection and preserve tile IDs so viewers can track one face.
  Self-intersection in the 3D view is a projection effect, not necessarily a defect in the lifted surface.
</p>
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
            "Scope": "Public web resources reviewed August 2026",
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
  community repositories reuse the word “Spectre” for straight-edged outlines, verify the geometry before
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
                "Trust tiers and actual capabilities",
                2,
                f"""
<ul>
  <li><strong>Official theorem sources:</strong> the Hat/Spectre project pages and open-access papers define
  canonical terminology and geometry. Use them before community summaries.</li>
  <li><strong>Official reference code:</strong> <code>hatviz</code> generates Hat patches under BSD-3-Clause;
  <code>hatvalidate</code> replays encoded proof checks. Generation and proof verification are different
  jobs.</li>
  <li><strong>Independent generators:</strong> TileOneOne (MIT) emits straight Tile(1,1) patches; symbolic-
  spectre-tiles (MPL-2.0) emphasizes exact coordinates; Tatham’s tools provide hierarchical navigation and
  transducers. Validate each against official rules.</li>
  <li><strong>Viewers and editors:</strong> WebGPU/deep-zoom tools optimize display. Manual playgrounds may
  permit mirrors, overlaps, or illegal frontiers and are not legality certificates.</li>
  <li><strong>Fabrication assets:</strong> CC0 multi-format outlines, GPL OpenSCAD, community Printables
  models, and laser-sheet generators differ in license, units, geometry variant, and manufacturing intent.
  A downloadable STL is not automatically canonical.</li>
  <li><strong>Education and installations:</strong> museum archives, workshop kits, terraces, grout papers,
  and public builds establish engagement or feasibility, not theorem, pedagogy, or structural performance.</li>
</ul>
<p>
  The computational distinctions, substitution generation, recognition, finite-state navigation, GPU
  rendering, and independent geometry checks, are explained in
  {link("computational-generation", "Computational generation and navigation")}. Discovery accounts are
  evaluated separately in {link("discovery-history", "Discovery history")}.
</p>
<p>
  The <code>funbin</code> package accompanying ref.&nbsp;27 can bin data into arbitrary polygons, including
  Hat-family cells, using point-in-polygon tests and spatial indexing. Its paper is intentionally satirical
  and supplies no controlled bias, error, readability, anti-aliasing, or reconstruction benchmark. Treat it
  as a creative visualization tool, not scientific evidence that aperiodic bins improve inference.{cite(27)}
</p>
""",
            ),
            Section(
                "Catalog",
                2,
                render_web_resources_html(compact=True),
            ),
            Section(
                "Task-oriented starting points",
                2,
                f"""
<ul>
  <li><strong>Learn the theorem:</strong> start with the official Hat and Spectre papers and project pages,
  then compare the independent proof and survey.{cite(1)}{cite(2)}{cite(3)}{cite(4)}</li>
  <li><strong>Generate patches:</strong> choose a repository with an explicit license, documented
  substitution rules, coordinate conventions, and reproducible export.</li>
  <li><strong>Fabricate:</strong> obtain canonical SVG/DXF or a parametric source, verify handedness and
  units, then follow {link("materials-and-fabrication", "Materials and fabrication")}.</li>
  <li><strong>Run research:</strong> begin from a cited physical or computational paper, reproduce its
  geometry and baselines, and archive the exact patch manifest.</li>
  <li><strong>Teach:</strong> use museum/workshop kits whose redistribution terms permit classroom copies,
  and state which observations illustrate rather than prove aperiodicity.</li>
</ul>
""",
            ),
            Section(
                "Licenses, geometry, and provenance",
                2,
                f"""
<p>
  A public URL is not a reuse license. Check the repository root, release asset, and individual file for a
  license; record its version, attribution requirements, and whether commercial use or modification is
  allowed. If no license is present, link to the source but do not redistribute its files.
</p>
<p>
  Validate geometry against an official outline or paper: units, vertex order, edge lengths, handedness,
  straight Tile(1,1) versus edge-modified Spectre, and allowed reflections.{cite(2)} Record source URL,
  commit or release, retrieval date, file hash, generator parameters, seed/root, generation, clipping rule,
  transforms, and any repairs. A screenshot is not adequate data provenance.
</p>
""",
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
    ("Mathematics", [
        "spectre-tile", "hat-tile", "substitution-tiling", "sturmian-lattices",
        "cut-and-project-and-model-sets", "diffraction-and-dynamical-spectrum",
        "four-dimensional-lift", "dimers-and-constrained-models",
    ]),
    ("Applications", [
        "computer-graphics", "design-and-architecture", "materials-and-fabrication", "education",
    ]),
    ("Research frontiers", [
        "signal-processing", "waves-and-photonics", "materials-science",
        "robotics-and-mobility", "biology-and-medicine", "algorithms-and-machine-learning",
    ]),
    ("Meta", ["discovery-history", "computational-generation", "resources-and-tools", "bibliography"]),
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


def wiki_json_ld(article: Article) -> str:
    if article.is_main:
        return ""
    page_url = f"{BASE}/{article.slug}.html"
    payload = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.title,
        "description": article.summary,
        "url": page_url,
        "dateModified": TODAY,
        "author": {"@type": "Organization", "name": "Untiling"},
        "publisher": {
            "@type": "Organization",
            "name": "Untiling",
            "url": "https://untiling.com/",
        },
        "isPartOf": {
            "@type": "WebSite",
            "name": "Untiling Research Wiki",
            "url": f"{BASE}/",
        },
    }
    return (
        '<script type="application/ld+json">'
        + json.dumps(payload, ensure_ascii=False)
        + "</script>"
    )


def render_page(article: Article) -> str:
    canonical = f"{BASE}/" if article.slug == "index" else f"{BASE}/{article.slug}.html"
    page_title = "Research Wiki" if article.is_main else f"{article.title} | Research Wiki"
    crumbs = '<a href="../index.html">Research</a> · <a href="index.html">Wiki</a>'
    if article.slug != "index":
        crumbs += f' · <span aria-current="page">{html.escape(article.title)}</span>'

    toc = render_toc(article.sections)
    infobox = render_infobox(article) if not article.is_main else ""
    json_ld = wiki_json_ld(article)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(page_title)} | Untiling</title>
    <meta name="description" content="{html.escape(article.summary)}" />
    <link rel="canonical" href="{canonical}" />
    <meta name="robots" content="index,follow,max-image-preview:large" />
    <meta property="og:type" content="article" />
    <meta property="og:title" content="{html.escape(article.title)} | Untiling Research Wiki" />
    <meta property="og:description" content="{html.escape(article.summary)}" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:site_name" content="Untiling" />
    <meta name="twitter:card" content="summary" />
    {json_ld}
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
        <a href="../../art.html">Art</a>
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
          <p>Last updated {TODAY}. Established claims, published experiments, and proposals are distinguished; numbered references include peer-reviewed papers, preprints, and documented resources.</p>
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
    <title>Research | Untiling</title>
    <meta name="description" content="Aperiodic monotile research hub: the field guide wiki, bibliography, resources index, and forthcoming papers and datasets." />
    <link rel="canonical" href="https://untiling.com/research/" />
    <meta name="robots" content="index,follow,max-image-preview:large" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="Research | Untiling" />
    <meta property="og:description" content="Wiki, bibliography, and research collections on Hat, Spectre, and Tile(1,1) monotiles." />
    <meta property="og:url" content="https://untiling.com/research/" />
    <meta property="og:site_name" content="Untiling" />
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage","name":"Untiling Research","description":"Research hub for aperiodic monotile wiki, bibliography, and datasets.","url":"https://untiling.com/research/","isPartOf":{"@type":"WebSite","name":"Untiling","url":"https://untiling.com/"}}</script>
    <link rel="stylesheet" href="../styles.css" />
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="../index.html">
        <img class="brand-mark" src="../assets/brand-mark.svg" alt="" width="32" height="32" decoding="async" />
        <span>Untiling</span>
      </a>
      <nav class="nav" aria-label="Primary navigation">
        <a href="../art.html">Art</a>
        <a href="index.html" aria-current="page">Research</a>
        <a class="nav-generator" href="https://aperiodicgenerator.com/">Generator</a>
        <a href="../apparel/">Shop</a>
        <a href="wiki/index.html">Wiki</a>
      </nav>
    </header>
    <main>
      <section class="section docs-hero">
        <p class="eyebrow">Research</p>
        <h1>The field guide to aperiodic monotiles.</h1>
        <p class="hero-text">
          Cross-linked wiki articles, a curated bibliography, a resources index, and an automated literature
          registry, built to be the most complete public reference on Hat, Spectre, and Tile(1,1) geometry.
          Generate patches on <a href="https://aperiodicgenerator.com/">Aperiodic Generator</a>.
        </p>
        <div class="hero-actions">
          <a class="button" href="wiki/index.html">Open the wiki</a>
          <a class="button secondary" href="wiki/bibliography.html">Bibliography</a>
          <a class="button secondary" href="wiki/resources-and-tools.html">Resources &amp; tools</a>
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
            <p>26+ articles on monotile concepts, mathematics, diffraction, fabrication, and application frontiers, with stable citation anchors.</p>
          </article>
          <article class="domain-block">
            <h3><a href="wiki/bibliography.html">Bibliography</a> <span class="research-badge is-live">Live</span></h3>
            <p>Peer-reviewed papers, preprints, proceedings, and patents, human-curated and cited throughout the wiki.</p>
          </article>
          <article class="domain-block">
            <h3><a href="wiki/resources-and-tools.html">Resources &amp; tools</a> <span class="research-badge is-live">Live</span></h3>
            <p>Official generators, OEIS sequences, museum exhibits, fabrication files, and built installations.</p>
          </article>
          <article class="domain-block is-muted">
            <h3>Original papers <span class="research-badge">Soon</span></h3>
            <p>Preprints and notes produced by the Untiling research program.</p>
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
      <p><a href="../index.html">Home</a> · <a href="wiki/index.html">Wiki</a> · <a href="https://aperiodicgenerator.com/docs.html">API Docs</a> · <a href="../attribution.html">Attribution</a></p>
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

    import subprocess
    import sys

    subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "build_sitemaps.py")],
        check=True,
    )


if __name__ == "__main__":
    main()
