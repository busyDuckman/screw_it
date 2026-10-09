"""Export examples/hole_profiles_2d.scad and restyle it for the README.

    python tools/make_profiles_svg.py [path/to/openscad]

Labels are added here rather than in OpenSCAD so the SVG doesn't depend on
which fonts the exporting machine has. Colours read on light and dark themes.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["pilot", "snug", "clear", "rib", "tri", "drop"]
SPACING = 10
FILL, INK = "#2a78d6", "#898781"


def main():
    openscad = sys.argv[1] if len(sys.argv) > 1 else "openscad"
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "profiles.svg"
        subprocess.run([openscad, "-o", str(raw), str(ROOT / "examples" / "hole_profiles_2d.scad")],
                       check=True)
        svg = raw.read_text()

    # Work in 10x units: tiny font sizes render badly in some rasterisers.
    svg = svg.replace('stroke="black" fill="lightgray" stroke-width="0.5"', f'fill="{FILL}"')
    svg = svg.replace("<path ", '<g transform="scale(10)"><path ', 1)
    svg = re.sub(r'width="[^"]*" height="[^"]*" viewBox="[^"]*"',
                 f'width="{6 * SPACING * 14}" height="{14 * 14}" viewBox="-50 -55 {60 * SPACING} 140"',
                 svg, count=1)
    labels = "".join(
        f'<text x="{i * SPACING * 10}" y="70" font-family="sans-serif" font-size="17" '
        f'text-anchor="middle" fill="{INK}">{n}</text>\n' for i, n in enumerate(NAMES))
    svg = svg.replace("</svg>", "</g>\n" + labels + "</svg>")
    out = ROOT / "docs" / "img" / "hole_profiles.svg"
    out.write_text(svg)
    print("wrote", out)


if __name__ == "__main__":
    main()
