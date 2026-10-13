"""Bundle the manuscript sources into a zip that Overleaf accepts (main.tex at the zip root).

Run from the repository root:  python paper/scripts/make_overleaf_zip.py
Output: COBRA_IGDCTF_paper_overleaf.zip next to the repository root (*.zip is git-ignored).
"""
import glob
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.normpath(os.path.join(PAPER, "..", "COBRA_IGDCTF_paper_overleaf.zip"))

README = """OVERLEAF QUICK START
====================
1. Overleaf > New Project > Upload Project > select this zip. Set main.tex as Main document, compiler pdfLaTeX.
2. The paper embeds figures/figNN_*.pdf. A figure whose PDF is missing shows a labelled placeholder box.
3. All ten figure PDFs in figures/ are final and match their .tex sources. If you edit a figure, recompile it
   (set figures/figNN_*.tex as Main document, Recompile, download the PDF over figures/figNN_*.pdf), then set
   main.tex back as Main document.
4. SEE ALL FIGURES AT ONCE (review only): set figures_preview.tex as Main document and Recompile: one page per figure,
   always built from the current .tex files.
Bibliography: BibTeX (automatic in Overleaf). Author names and bibliography entries marked VERIFY are placeholders.
"""

files = ["main.tex", "references.bib", "figures_preview.tex"] + \
        sorted(os.path.join("figures", os.path.basename(p))
               for ext in ("*.tex", "*.pdf") for p in glob.glob(os.path.join(PAPER, "figures", ext)))

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        z.write(os.path.join(PAPER, rel), rel.replace(os.sep, "/"))
    z.writestr("OVERLEAF_README.txt", README)

with zipfile.ZipFile(OUT) as z:
    for info in z.infolist():
        print(f"{info.file_size:8d}  {info.filename}")
print("->", OUT)
