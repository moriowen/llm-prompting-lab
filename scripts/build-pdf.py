"""Render the HW1 submission markdown to PDF via Chrome's headless print pipeline.

No pandoc/LaTeX on this machine, so: markdown -> styled HTML -> Chrome --print-to-pdf.
The wide result tables are the whole reason for the CSS: they get a small monospace
face and are allowed to break across pages rather than overflowing the sheet.
"""

import subprocess
import sys
from pathlib import Path

import markdown

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4 portrait; margin: 14mm 12mm; }
body { font: 10pt/1.45 "Charter","Georgia",serif; color:#111; max-width:none; margin:0; }
h1 { font-size: 15pt; margin: 1.4em 0 .5em; padding-top:.3em; border-top:2px solid #222;
     page-break-after: avoid; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 12.5pt; margin: 1.2em 0 .4em; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 1em 0 .35em; page-break-after: avoid; }
h4 { font-size: 10pt; margin: .9em 0 .3em; page-break-after: avoid; }
p, li { orphans: 2; widows: 2; }
code { font-family:"SF Mono","Menlo",monospace; font-size:.85em; background:#f2f2f2;
       padding:.08em .28em; border-radius:2px; }
pre { background:#f6f6f6; border-left:3px solid #bbb; padding:.6em .8em; font-size:8.5pt;
      line-height:1.35; overflow-x:auto; page-break-inside:avoid; }
pre code { background:none; padding:0; font-size:inherit; }
blockquote { margin:.5em 0 .5em .4em; padding:.35em .8em; border-left:3px solid #999;
             background:#fafafa; font-family:"SF Mono","Menlo",monospace; font-size:8pt;
             line-height:1.4; color:#333; page-break-inside:avoid; }
blockquote p { margin:.2em 0; }
table { border-collapse:collapse; width:100%; margin:.7em 0; font-size:7.4pt;
        table-layout:auto; }
th, td { border:1px solid #ccc; padding:2.5px 4px; text-align:left; vertical-align:top;
         word-break:break-word; }
th { background:#ececec; font-weight:600; }
/* Wrong answers are bold in the markdown source; the handout asks for red. */
td strong { color:#c00; font-weight:600; }
table code { background:none; padding:0; font-size:1em; }
a { color:#0b4ea2; text-decoration:none; }
hr { border:none; border-top:1px solid #ddd; margin:1.4em 0; }
#toc-table td:first-child { width:46%; }
"""


def build(md_path: Path, pdf_path: Path) -> None:
    text = md_path.read_text()
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "md_in_html", "attr_list"])
    html = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{md_path.stem}</title><style>{CSS}</style></head>"
            f"<body>{body}</body></html>")
    html_path = pdf_path.with_suffix(".html")
    html_path.write_text(html)

    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", "--virtual-time-budget=10000",
         f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
        check=True, capture_output=True)
    html_path.unlink()  # the HTML is a build artefact, not a deliverable
    print(f"{pdf_path} ({pdf_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/HW1_P_Mohite_Atharva.md")
    build(src, src.with_suffix(".pdf"))
