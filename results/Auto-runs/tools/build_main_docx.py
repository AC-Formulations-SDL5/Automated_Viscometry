"""Build the main manuscript .docx from AutoVisco_Submission.md.

Auto_Visco.docx is used as the template: its title/author block, the twelve Word equations
(Eq. 1-12) and Table 1 are copied verbatim; all other text, figures and references come from
the Markdown. Usage: python tools/build_main_docx.py  (run from results/Auto-runs)
"""
import copy
import re
from pathlib import Path

import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from title import TITLE, set_title  # noqa: E402
SRC = HERE / "Auto_Visco.docx"
MD = HERE / "AutoVisco_Submission.md"
OUT = HERE / "Auto_Visco_v2.docx"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def text_of(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


d = docx.Document(SRC)
body = d.element.body
children = [c for c in body.iterchildren() if c.tag != qn("w:sectPr")]

front = []
for c in children:
    if c.tag == qn("w:p") and text_of(c).strip() == "Abstract":
        break
    front.append(c)

equations, table1 = {}, None
for i, c in enumerate(children):
    if c.tag == qn("w:tbl") and next(c.iter(M + "oMath"), None) is not None:
        m = re.search(r"Eq\.\s*(\d+)", text_of(c))
        equations[int(m.group(1))] = c
    if c.tag == qn("w:p") and text_of(c).startswith("Table 1."):
        table1 = (c, children[i + 1])
assert sorted(equations) == list(range(1, 13)) and table1

for c in children:
    body.remove(c)
for c in front + list(equations.values()) + list(table1):  # drop co-author comment anchors from copied parts
    for tag in ("w:commentRangeStart", "w:commentRangeEnd"):
        for el in list(c.iter(qn(tag))):
            el.getparent().remove(el)
    for el in list(c.iter(qn("w:commentReference"))):
        run = el.getparent()
        run.getparent().remove(run)
set_title(front[0])
sectPr = body.find(qn("w:sectPr"))


def append(el):
    sectPr.addprevious(el)


INLINE = re.compile(r"(<sup>.*?</sup>|<sub>.*?</sub>|\*\*.+?\*\*)")


def add_inline(p, s, bold=False):
    s = s.replace("\\*", "*")
    for tok in INLINE.split(s):
        if not tok:
            continue
        if tok.startswith("<sup>"):
            add_inline_run(p, tok[5:-6], bold).font.superscript = True
        elif tok.startswith("<sub>"):
            add_inline_run(p, tok[5:-6], bold).font.subscript = True
        elif tok.startswith("**"):
            add_inline(p, tok[2:-2], bold=True)
        else:
            add_inline_run(p, tok, bold)


def add_inline_run(p, s, bold):
    r = p.add_run(s)
    r.bold = bold or None
    return r


def para(s="", style=None, align=None):
    p = d.add_paragraph(style=style)
    if s:
        add_inline(p, s)
    if align is not None:
        p.alignment = align
    append(p._p)
    return p


def picture(path):
    w, h = Image.open(path).size
    width = 6.5 if h / w * 6.5 <= 8.0 else 8.0 * w / h
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER)
    p.add_run().add_picture(str(path), width=Inches(width))


md = MD.read_text(encoding="utf-8")
md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
head, rest = md.split("# Abstract", 1)

for el in front:
    append(el)
for blk in head.split("\n\n"):  # only the ESI note is new in the front matter
    if blk.strip().startswith("†"):
        para(blk.strip())

blocks = [b.strip() for b in ("# Abstract" + rest).split("\n\n") if b.strip()]
for b in blocks:
    if b.startswith("### "):
        para(b[4:], style="Heading 3")
    elif b.startswith("## "):
        para(b[3:], style="Heading 2")
    elif b.startswith("# "):
        para(b[2:], style="Heading 1")
    elif b.startswith("$$"):
        n = int(re.search(r"\\tag\{(\d+)\}", b).group(1))
        append(copy.deepcopy(equations[n]))
    elif b.startswith("**Table 1.**"):
        para(b, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    elif b.startswith("|"):
        append(copy.deepcopy(table1[1]))
    elif b.startswith("!["):
        picture(HERE / re.search(r"\]\(([^)]+)\)", b).group(1))
    elif re.match(r"\*\*Figure \d+\.\*\*", b):
        para(b, align=WD_ALIGN_PARAGRAPH.JUSTIFY)  # caption in body-text style, bold label
    elif re.match(r"\[\d+\] ", b):
        p = para(b)
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)
        for r in p.runs:
            r.font.size = Pt(10)
    else:
        para(b, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

d.save(OUT)
print("wrote", OUT)
