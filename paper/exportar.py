"""Genera el artículo en PDF y Word a partir de paper.md.

    python paper/exportar.py

Requisitos: ``pip install markdown python-docx`` y Microsoft Edge (para el PDF).
Salida: paper/radar-de-gastos-articulo.pdf y paper/radar-de-gastos-articulo.docx.

El formato sigue la plantilla de artículo del autor: título, autores y filiación a una columna;
cuerpo a dos columnas en Aptos 11 con interlineado 1,08 y 8 pt después de cada párrafo;
secciones numeradas en 14 pt; pies de tabla y figura en 10 pt, centrados y sobre el contenido;
referencias APA con sangría francesa. Las tablas de cuatro o más columnas ocupan el ancho de
la página porque no caben en media columna.

El Markdown es la fuente de verdad: los dos formatos se regeneran desde él.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "paper.md"
OUT = HERE / "radar-de-gastos-articulo"
EDGE_PATHS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]
FONT = "Aptos"
LINE = 259 / 240  # interlineado "múltiple 1,08" de Word
WIDE_TABLE_COLUMNS = 4


# ---------------------------------------------------------------- lectura
def read_source() -> tuple[dict[str, object], str]:
    text = SOURCE.read_text(encoding="utf-8")
    meta: dict[str, object] = {"authors": []}
    _, front, body = text.split("---", 2)
    for line in front.strip().splitlines():
        if line.startswith("title:"):
            meta["title"] = line.split(":", 1)[1].strip().strip('"')
        elif line.strip().startswith("- "):
            meta["authors"].append(line.strip()[2:].strip().strip('"'))  # type: ignore[union-attr]
    return meta, body.strip()


# ---------------------------------------------------------------- PDF (HTML + Edge)
def aptos_font_faces() -> str:
    """@font-face de Aptos desde la caché de fuentes de Office; Edge no ve las fuentes en la nube."""
    folder = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "FontCache" / "4" / "CloudFonts" / "Aptos"
    styles: dict[str, tuple[str, str] | None] = {  # nombre completo en la tabla de nombres -> (peso, estilo)
        "Aptos Bold Italic": ("bold", "italic"), "Aptos Bold": ("bold", "normal"),
        "Aptos Italic": ("normal", "italic"), "Aptos Light": None, "Aptos SemiBold": None,
        "Aptos ExtraBold": None, "Aptos Black": None, "Aptos": ("normal", "normal"),
    }
    faces = []
    for font in sorted(folder.glob("*.ttf")) if folder.is_dir() else []:
        data = font.read_bytes()
        for name in styles:
            if name.encode("utf-16-be") in data:
                if not (weight_style := styles[name]):
                    break  # variantes que no usa el artículo
                weight, style = weight_style
                faces.append(
                    f"@font-face {{ font-family: '{FONT}'; src: url('{font.as_uri()}'); "
                    f"font-weight: {weight}; font-style: {style}; }}"
                )
                break
    return "\n".join(faces)


CSS = aptos_font_faces() + f"""
@page {{ size: Letter; margin: 2.5cm 3cm; }}
body {{ font-family: '{FONT}', 'Segoe UI', Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.08; color: #000; }}
.titulo {{ text-align: center; margin-bottom: 18pt; }}
.titulo .tt {{ font-size: 20pt; font-weight: normal; line-height: 1.15; margin: 0 0 12pt; }}
.titulo .autor {{ font-weight: bold; margin: 0; }}
.cuerpo {{ column-count: 2; column-gap: 1.25cm; text-align: justify; }}
p {{ margin: 0 0 8pt; }}
h1 {{ font-size: 14pt; font-weight: bold; margin: 12pt 0 8pt; break-after: avoid; }}
h1.resumen {{ margin-top: 0; }}
h2 {{ font-size: 11pt; font-weight: bold; margin: 10pt 0 6pt; break-after: avoid; }}
ul, ol {{ margin: 0 0 8pt; padding-left: 1.1em; }}
li {{ margin-bottom: 4pt; }}
.pie {{ font-size: 10pt; text-align: center; margin: 8pt 0 4pt; break-after: avoid; }}
.ancho {{ column-span: all; margin: 4pt 0 10pt; }}
table {{ border-collapse: collapse; width: 100%; font-size: 8.5pt; line-height: 1.15; margin-bottom: 8pt; break-inside: avoid; text-align: left; }}
th, td {{ border: 1px solid #777; padding: 2px 4px; vertical-align: top; }}
th {{ background: #e8e8e8; }}
code {{ font-family: Consolas, monospace; font-size: 9pt; }}
pre {{ font-size: 7.5pt; line-height: 1.2; background: #f4f4f4; border: 1px solid #ddd; padding: 5px 6px; white-space: pre-wrap; break-inside: avoid; text-align: left; }}
.referencias p {{ text-align: left; padding-left: 1.27cm; text-indent: -1.27cm; }}
.referencias a, .referencias .url {{ word-break: break-all; }}
"""


def build_html(meta: dict[str, object], body: str) -> str:
    content = markdown.markdown(body, extensions=["tables", "fenced_code", "sane_lists"])
    content = content.replace("<h1>Resumen</h1>", '<h1 class="resumen">Resumen:</h1>', 1)
    # Pies de tabla y de figura.
    content = re.sub(r"<p><em>((?:Tabla|Figura) [A-Z]?\d+\..*?)</em></p>", r'<p class="pie">\1</p>', content)

    # Tablas anchas (con su pie) a todo el ancho de la página.
    def widen(m: re.Match) -> str:
        cols = len(re.findall(r"<th[ >]", m.group(2).split("</tr>")[0]))
        block = m.group(1) + m.group(2)
        return f'<div class="ancho">{block}</div>' if cols >= WIDE_TABLE_COLUMNS else block

    content = re.sub(r'(<p class="pie">Tabla[^<]*</p>\s*)(<table>.*?</table>)', widen, content, flags=re.S)
    # Las URL largas se parten en cualquier carácter para no invadir la otra columna.
    content = re.sub(r"(https?://[^\s<]+)", r'<span class="url">\1</span>', content)
    # La sangría francesa aplica solo a las referencias: el bloque se cierra en el siguiente título (anexos).
    refs = "<h1>Referencias bibliográficas</h1>"
    before, sep, after = content.partition(refs)
    if sep:
        cut = after.find("<h1>")
        after = after + "</div>" if cut < 0 else after[:cut] + "</div>" + after[cut:]
        content = before + refs + '<div class="referencias">' + after
    authors = "".join(f'<p class="autor">{html.escape(a)}</p>' for a in meta["authors"])  # type: ignore[union-attr]
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>{html.escape(str(meta.get("title", "")))}</title><style>{CSS}</style></head><body>
<div class="titulo"><p class="tt">{html.escape(str(meta.get("title", "")))}</p>{authors}</div>
<div class="cuerpo">{content}</div></body></html>"""


def export_pdf(page: str) -> Path:
    edge = next((p for p in EDGE_PATHS if p.exists()), None)
    if edge is None:
        sys.exit("No se encontró Microsoft Edge para generar el PDF.")
    pdf = OUT.with_suffix(".pdf")
    pdf.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        page_file = Path(tmp) / "articulo.html"
        page_file.write_text(page, encoding="utf-8")
        subprocess.run(
            [
                str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--user-data-dir={Path(tmp) / 'perfil'}", f"--print-to-pdf={pdf}", page_file.as_uri(),
            ],
            check=True, capture_output=True, timeout=120,
        )
        for _ in range(60):  # Edge puede terminar de escribir el archivo después de salir
            if pdf.exists() and pdf.stat().st_size > 0:
                break
            time.sleep(0.5)
    if not pdf.exists():
        sys.exit("Edge no generó el PDF.")
    return pdf


# ---------------------------------------------------------------- Word (python-docx)
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def add_inline(paragraph, text: str, *, size: float | None = None, bold: bool = False) -> None:  # type: ignore[no-untyped-def]
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2]); run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1]); run.font.name = "Consolas"
        elif part.startswith("[") and "](" in part:
            run = paragraph.add_run(part[1:].split("](", 1)[0])
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = paragraph.add_run(part[1:-1]); run.italic = True
        else:
            run = paragraph.add_run(part)
        if bold:
            run.bold = True
        if size:
            run.font.size = Pt(size)


def set_columns(section, count: int) -> None:  # type: ignore[no-untyped-def]
    sect = section._sectPr
    for old in sect.findall(qn("w:cols")):
        sect.remove(old)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), "708")
    sect.append(cols)


def new_section(doc, columns: int):  # type: ignore[no-untyped-def]
    section = doc.add_section(WD_SECTION.CONTINUOUS)
    set_columns(section, columns)
    return section


def shade(cell, color: str) -> None:  # type: ignore[no-untyped-def]
    props = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear"); shading.set(qn("w:color"), "auto"); shading.set(qn("w:fill"), color)
    props.append(shading)


def add_table(doc, rows: list[list[str]], size: float) -> None:  # type: ignore[no-untyped-def]
    header, data = rows[0], rows[2:]  # rows[1] es el separador |---|
    table = doc.add_table(rows=1 + len(data), cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r, values in enumerate([header, *data]):
        for c in range(len(header)):
            cell = table.rows[r].cells[c]
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_inline(para, values[c] if c < len(values) else "", size=size, bold=r == 0)
            if r == 0:
                shade(cell, "E8E8E8")
    spacer = doc.add_paragraph(); spacer.paragraph_format.space_after = Pt(4)


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def caption(doc, text: str) -> None:  # type: ignore[no-untyped-def]
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(4)
    add_inline(p, text, size=10)


def build_docx(meta: dict[str, object], body: str) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.59), Cm(27.94)  # carta
    section.left_margin = section.right_margin = Cm(3)
    section.top_margin = section.bottom_margin = Cm(2.5)
    set_columns(section, 1)

    normal = doc.styles["Normal"]
    normal.font.name = FONT; normal.font.size = Pt(11)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        normal.element.rPr.rFonts.set(qn(attr), FONT)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = LINE
    for level, size in ((1, 14), (2, 11)):
        style = doc.styles[f"Heading {level}"]
        style.font.name = FONT; style.font.size = Pt(size); style.font.bold = True; style.font.italic = False
        style.font.color.rgb = RGBColor(0, 0, 0)
        for attr in ("w:ascii", "w:hAnsi"):
            style.element.rPr.rFonts.set(qn(attr), FONT)
        style.paragraph_format.space_before = Pt(12 if level == 1 else 10)
        style.paragraph_format.space_after = Pt(8 if level == 1 else 6)
        style.paragraph_format.keep_with_next = True

    # Título, autores y filiación a una columna.
    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(12)
    run = title.add_run(str(meta.get("title", ""))); run.font.size = Pt(20)
    for author in meta["authors"]:  # type: ignore[union-attr]
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.add_run(author).bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    new_section(doc, 2)  # el cuerpo va a dos columnas
    state = {"columns": 2, "in_refs": False}

    lines = body.splitlines()
    i, para, pending_caption = 0, [], None

    def flush() -> None:
        if para:
            p = doc.add_paragraph()
            if state["in_refs"]:  # APA: sangría francesa, alineado a la izquierda
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.left_indent = Cm(1.27)
                p.paragraph_format.first_line_indent = Cm(-1.27)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_inline(p, " ".join(s.strip() for s in para))
            para.clear()

    while i < len(lines):
        line = lines[i]
        cap = re.match(r"^\*((?:Tabla|Figura) [A-Z]?\d+\..*)\*$", line.strip())
        if cap:
            flush(); pending_caption = cap.group(1); i += 1
            continue
        if line.startswith("```"):
            flush(); i += 1; code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i += 1
            if pending_caption:
                caption(doc, pending_caption); pending_caption = None
            for c in code:
                p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0; p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(c or " "); r.font.name = "Consolas"; r.font.size = Pt(7.5)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            i += 1
            continue
        if line.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_row(lines[i])); i += 1
            wide = len(rows[0]) >= WIDE_TABLE_COLUMNS
            if wide and state["columns"] == 2:
                new_section(doc, 1); state["columns"] = 1
            if pending_caption:
                caption(doc, pending_caption); pending_caption = None
            add_table(doc, rows, size=8.5)
            if wide:
                new_section(doc, 2); state["columns"] = 2
            continue
        heading = re.match(r"^(#{1,2})\s+(.*)", line)
        if heading:
            flush()
            text = heading.group(2).replace("*", "")
            state["in_refs"] = text.startswith("Referencias")
            if text == "Resumen":
                p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run("Resumen:"); r.bold = True; r.font.size = Pt(14)
            else:
                doc.add_heading(text, level=len(heading.group(1)))
            i += 1
            continue
        item = re.match(r"^(\d+\.|-)\s+(.*)", line)
        if item and not state["in_refs"]:
            flush(); text = [item.group(2)]; i += 1
            while i < len(lines) and lines[i].startswith(("   ", "  ")) and lines[i].strip():
                text.append(lines[i].strip()); i += 1
            if item.group(1) == "-":
                p = doc.add_paragraph(style="List Bullet")
            else:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.6); p.paragraph_format.first_line_indent = Cm(-0.6)
                p.add_run(item.group(1) + " ")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_inline(p, " ".join(text))
            continue
        if not line.strip():
            flush(); i += 1
            continue
        para.append(line); i += 1
    flush()

    out = OUT.with_suffix(".docx")
    doc.save(out)
    return out


def main() -> None:
    meta, body = read_source()
    pdf = export_pdf(build_html(meta, body))
    docx_file = build_docx(meta, body)
    for f in (pdf, docx_file):
        print(f"{f.name}: {f.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
