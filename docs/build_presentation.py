"""Build the group presentation (docs/Presentation.pptx).

The deck tells the project as a story (problem, solution, value, how it works, findings, trust,
next steps) instead of walking through every metric. Numbers are still read from artifacts/ and
reports/ so the slides agree with docs/Technical_Report.pdf, and the dashboard screenshots in
docs/screenshots are reused as backup demo slides.

Run from the repository root:
    pip install python-pptx matplotlib
    python docs/build_presentation.py
"""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

_ROOT = Path(__file__).resolve().parent.parent


def _load():
    art, rep, docs = _ROOT / "artifacts", _ROOT / "reports", _ROOT / "docs"
    metrics = json.loads((art / "metrics.json").read_text())

    def gains_from_report():
        html = re.sub(r"<img[^>]*>", "", (rep / "training_report.html").read_text(encoding="utf-8"))
        part = html[html.find("7. Business"):]
        return [(int(a), float(b), float(c)) for a, b, c in
                re.findall(r"<td>(\d+)%</td><td>([\d.]+)%</td><td>([\d.]+)x</td>", part)]

    return SimpleNamespace(
        DOCS=docs, REP=rep, FIG=docs / "figures", SHOTS=docs / "screenshots",
        metrics=metrics,
        insights=json.loads((art / "insights.json").read_text()),
        cleaning=json.loads((art / "cleaning_report.json").read_text()),
        MEMBERS=[("Gunathilaka W.A.D.S.", "IT23859456"), ("Edirisinghe E.M.K.L.", "IT23857780"),
                 ("Illesinghe E.S.", "IT23557024"), ("Kaluarachchi R.G.", "IT23544918")],
        GROUP="Data Miners",
        GROUP_ID="Group 1.1",
        by_name=lambda name: next(m for m in metrics["models"] if m["name"] == name),
        pct=lambda x, d=1: f"{x * 100:.{d}f}%",
        gains_from_report=gains_from_report,
    )


R = _load()
OUT = R.DOCS / "Presentation.pptx"
PRODUCT = "Term Deposit Predictor"

INK = RGBColor(0x1D, 0x21, 0x25)          # dark slide background / headline text
PAPER = RGBColor(0xF2, 0xF0, 0xEB)        # light slide background
CARD = RGBColor(0xFA, 0xF9, 0xF6)
CARD_LINE = RGBColor(0xDC, 0xD8, 0xCF)
RULE = RGBColor(0x5F, 0x63, 0x68)
TEXT = RGBColor(0x22, 0x26, 0x2B)
MUTED = RGBColor(0x5F, 0x63, 0x68)
BLUE = RGBColor(0x2F, 0x5F, 0x9E)
RUST = RGBColor(0xB5, 0x54, 0x1C)
SAND = RGBColor(0xA9, 0xA4, 0x98)
DOT_OFF = RGBColor(0xD3, 0xCF, 0xC6)
WHITE = RGBColor(0xF5, 0xF3, 0xEE)
SOFT = RGBColor(0xB8, 0xBC, 0xC2)
TABLE_HEAD = RGBColor(0x14, 0x22, 0x3D)
TABLE_DARK = RGBColor(0x1F, 0x33, 0x55)
NAVY_DEEP = RGBColor(0x0F, 0x1B, 0x33)
NAVY_LIGHT = RGBColor(0x1F, 0x4E, 0x82)
TINT_BLUE = RGBColor(0xE4, 0xED, 0xF7)
TINT_PEACH = RGBColor(0xF8, 0xEB, 0xDD)
ORANGE = RGBColor(0xF2, 0x99, 0x4A)
SANS, MONO = "Arial", "Courier New"
X0 = Inches(0.89)
CW = Inches(11.56)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height
_slide_no = [0]


# ------------------------------------------------------------------ helpers --

def _runs(p, line, size, bold, color, font=SANS, accent=None):
    """Add a line where **bold** spans are emphasised."""
    for part in re.split(r"(\*\*[^*]+\*\*)", line):
        if not part:
            continue
        r = p.add_run()
        strong = part.startswith("**")
        r.text = part[2:-2] if strong else part
        r.font.size = Pt(size)
        r.font.name = font
        r.font.bold = bold or strong
        r.font.color.rgb = (accent or color) if strong else color
    return p


def text(slide, x, y, w, h, content, size=16, bold=False, color=TEXT, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=SANS, spacing=None, accent=None, line_spacing=None):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(content if isinstance(content, list) else [content]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        _runs(p, line, size, bold, color, font, accent)
        if spacing:
            for r in p.runs:
                r.font._element.set("spc", str(spacing))
    return tb


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    if radius is not None:
        s.adjustments[0] = radius
    s.shadow.inherit = False
    return s


def hline(slide, x, y, w, color=RULE, weight=1.0):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, y, x + w, y)
    ln.line.color.rgb = color
    ln.line.width = Pt(weight)
    return ln


def card(slide, x, y, w, h, top_accent=False):
    c = rect(slide, x, y, w, h, CARD, CARD_LINE, MSO_SHAPE.ROUNDED_RECTANGLE, 0.05)
    if top_accent:
        rect(slide, x + Inches(0.04), y, w - Inches(0.08), Inches(0.05), BLUE)
    return c


def picture(slide, path, x, y, w, h, border=True):
    """Insert an image scaled to fit inside the box, centred."""
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = int(iw * scale), int(ih * scale)
    pic = slide.shapes.add_picture(str(path), x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)
    if border:
        pic.line.color.rgb = CARD_LINE
        pic.line.width = Pt(0.75)
    return pic


def _gradient(fill, stops, angle):
    fill.gradient()
    fill.gradient_angle = angle
    for stop, (pos, color) in zip(fill.gradient_stops, stops):
        stop.position = pos
        stop.color.rgb = color


def background(slide, dark=False):
    if dark:
        _gradient(slide.background.fill, [(0.0, NAVY_DEEP), (1.0, NAVY_LIGHT)], 315)
        return
    _gradient(slide.background.fill, [(0.0, TINT_BLUE), (1.0, TINT_PEACH)], 315)
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(0.1))
    strip.line.fill.background()
    strip.shadow.inherit = False
    _gradient(strip.fill, [(0.0, BLUE), (1.0, RGBColor(0xE0, 0x8A, 0x3C))], 0)


def new_slide(eyebrow, headline, presenter=None, notes="", dark=False, footer=True, head_size=34, footnote=None):
    _slide_no[0] += 1
    s = prs.slides.add_slide(BLANK)
    background(s, dark)
    text(s, X0, Inches(0.89), Inches(11.9), Inches(0.3), eyebrow.upper(), 11, color=ORANGE if dark else RUST,
         font=MONO, spacing=300)
    if headline:
        text(s, X0, Inches(1.36), Inches(11.9), Inches(0.7), headline, head_size, True, WHITE if dark else INK)
    if footer:
        text(s, X0, Inches(6.82), Inches(10), Inches(0.3), footnote or f"{PRODUCT}  ·  {R.GROUP}", 11,
             color=SOFT if dark else MUTED)
        text(s, Inches(11.45), Inches(6.82), Inches(1.0), Inches(0.3), f"{_slide_no[0]:02d}", 11,
             color=SOFT if dark else MUTED, align=PP_ALIGN.RIGHT)
    scripted = SCRIPT.get(_slide_no[0])
    lead = f"Presenter: {R.MEMBERS[presenter][0]}\n\n" if presenter is not None else ""
    if scripted:
        s.notes_slide.notes_text_frame.text = scripted
    elif lead or notes:
        s.notes_slide.notes_text_frame.text = lead + notes
    return s


def _load_script(path):
    """Map slide number -> that slide's section of the presenter script, as plain text."""
    if not path.exists():
        return {}
    sections = {}
    for m in re.finditer(r"^## Slide (\d+) · .*?\n(.*?)(?=^---\s*$|^## |\Z)", path.read_text(encoding="utf-8"),
                         re.M | re.S):
        body = re.sub(r"^### ", "", m.group(2), flags=re.M)
        body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)
        body = re.sub(r"\*(\[[^\]]+\])\*", r"\1", body)
        body = re.sub(r"(?<!\n)\n(?!\n)", " ", body.strip())
        sections[int(m.group(1))] = re.sub(r"\n{3,}", "\n\n", body)
    return sections


SCRIPT = _load_script(R.DOCS / "Presentation_Script.md")


def bar_row(slide, y, label, sub, before, after, scale_max, fmt, change, change_color=RUST,
            bar_x=Inches(3.53), bar_w=Inches(6.0)):
    """Two stacked bars (grey = before, blue = after) with a big change figure on the right."""
    text(slide, X0, y + Inches(0.02), Inches(2.5), Inches(0.3), label, 16, True, INK)
    text(slide, X0, y + Inches(0.34), Inches(2.5), Inches(0.3), sub, 12, color=MUTED)
    for i, (v, col, bold) in enumerate(((before, SAND, False), (after, BLUE, True))):
        yy = y + Inches(i * 0.32)
        w = max(int(bar_w * v / scale_max), Inches(0.05))
        rect(slide, bar_x, yy, w, Inches(0.25), col)
        text(slide, bar_x + w + Inches(0.1), yy, Inches(1.4), Inches(0.26), fmt(v), 12, bold,
             TEXT if bold else MUTED, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, Inches(10.2), y - Inches(0.04), Inches(2.25), Inches(0.66), change, 32, True, change_color,
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def legend(slide, y, items):
    x = X0
    for label, col, width in items:
        rect(slide, x, y + Inches(0.04), Inches(0.22), Inches(0.17), col)
        text(slide, x + Inches(0.3), y, Inches(width), Inches(0.26), label, 12, color=MUTED)
        x += Inches(width + 0.55)


def _cell_borders(cell, color="3A5580", width=9525):
    tcPr = cell._tc.get_or_add_tcPr()
    # Border lines must precede the cell fill inside a:tcPr.
    for i, tag in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        for old in tcPr.findall(qn(tag)):
            tcPr.remove(old)
        ln = tcPr.makeelement(qn(tag), {"w": str(width)})
        fill = ln.makeelement(qn("a:solidFill"), {})
        fill.append(fill.makeelement(qn("a:srgbClr"), {"val": color}))
        ln.append(fill)
        tcPr.insert(i, ln)


def dark_table(slide, x, y, w, headers, rows, col_w, row_h=0.43, size=13, first_col_rust=True):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, Inches(row_h * (len(rows) + 1)))
    tbl = shape.table
    tbl.first_row = False
    tbl.horz_banding = False
    total = sum(col_w)
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Emu(int(w * cw / total))
    for r in range(len(rows) + 1):
        tbl.rows[r].height = Inches(row_h)
        for c in range(len(headers)):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.15)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = TABLE_HEAD if r == 0 else TABLE_DARK
            tf = cell.text_frame
            tf.paragraphs[0].text = ""
            val = headers[c] if r == 0 else rows[r - 1][c]
            col = SOFT if r == 0 else (RUST if c == 0 and first_col_rust else WHITE)
            _runs(tf.paragraphs[0], str(val), size, False, col)
            _cell_borders(cell)
    return tbl


def light_table(slide, x, y, w, headers, rows, col_w, row_h=0.46, size=14, highlight=0):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, Inches(row_h * (len(rows) + 1)))
    tbl = shape.table
    tbl.first_row = False
    tbl.horz_banding = False
    total = sum(col_w)
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Emu(int(w * cw / total))
    for r in range(len(rows) + 1):
        tbl.rows[r].height = Inches(row_h)
        for c in range(len(headers)):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            hl = highlight is not None and r == highlight + 1
            cell.fill.fore_color.rgb = RGBColor(0xE3, 0xEA, 0xF4) if hl else (PAPER if r == 0 else CARD)
            tf = cell.text_frame
            tf.word_wrap = True
            tf.paragraphs[0].text = ""
            val = headers[c] if r == 0 else rows[r - 1][c]
            _runs(tf.paragraphs[0], str(val), 12 if r == 0 else size, hl and c == 0,
                  MUTED if r == 0 else (BLUE if hl and c == 0 else TEXT))
            if c > 0:
                tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    return tbl


def gains_figure(gains, path):
    """Decorative cumulative-gains curve for the dark title and closing slides."""
    xs = [0] + [p for p, _, _ in gains] + [100]
    ys = [0] + [c for _, c, _ in gains] + [100]
    fig = plt.figure(figsize=(13.333, 2.78), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.fill_between(xs, ys, 0, color="#6FA3E0", alpha=0.22, lw=0)
    ax.plot(xs, ys, color="#F2994A", lw=2.4, solid_joinstyle="round")
    ax.plot([0, 100], [0, 100], color="#9FB3CF", lw=1.2, ls=(0, (4, 4)), alpha=0.7)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 104)
    ax.axis("off")
    fig.savefig(path, transparent=True)
    plt.close(fig)


def dots_figure(rate, path, cols=46, rows=7):
    """Decorative dot field for the title slide: dots fade in left to right and 'yes' clients
    (orange) become more frequent, hinting at ranking clients by score."""
    import random
    rng = random.Random(42)
    fig = plt.figure(figsize=(13.333, 2.78), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    for c in range(cols):
        t = c / (cols - 1)
        p_yes = rate * (0.3 + 3.2 * t ** 2)
        for r in range(rows):
            yes = rng.random() < p_yes
            ax.scatter(c + 0.5, r + 0.5, s=130 if yes else 70, color="#F2994A" if yes else "#9FC2EC",
                       alpha=0.12 + 0.83 * t if not yes else 0.35 + 0.65 * t, lw=0)
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.axis("off")
    fig.savefig(path, transparent=True)
    plt.close(fig)


# ------------------------------------------------------------------- slides --

def build() -> None:
    m, ins, cl = R.metrics, R.insights, R.cleaning
    best = m["best_model"]
    tuned = m["best_model_tuned_test"]
    cm = tuned["confusion_matrix"]
    bm = R.by_name(best)
    d = bm["test"]["confusion_matrix"]
    cb = ins["class_balance"]
    ranked = sorted(m["models"], key=lambda x: x["cv_roc_auc"], reverse=True)
    rate = {k: {r["category"]: r for r in v} for k, v in ins["rate_by"].items()}
    cr = {r["category"]: r["rate"] for r in ins["campaign_rate"]}
    gains = R.gains_from_report()
    g = {p: (c, lift) for p, c, lift in gains}
    pct = R.pct
    avg = cb["positive_rate"]
    n_rows = cl["raw_rows"]
    test_n = m["test_size"]
    M1, M2, M3, M4 = 0, 1, 2, 3
    curve = R.FIG / "title_gains_curve.png"
    gains_figure(gains, curve)
    dots = R.FIG / "title_dots.png"
    dots_figure(avg, dots)

    # 1 Title ---------------------------------------------------------------
    s = new_slide(f"{R.GROUP} · {R.GROUP_ID} · IT3051 · Final presentation", None, M1,
                  "Introduce the team and the project in one line: we help a bank's call team phone the clients "
                  "most likely to open a term deposit first.", dark=True, footer=False)
    text(s, X0, Inches(1.36), Inches(11), Inches(1.8), ["Call the clients who are", "ready to say yes"],
         54, True, WHITE, line_spacing=0.95)
    text(s, X0, Inches(3.2), Inches(11), Inches(0.45),
         f"{PRODUCT} · showing a bank's call team who is most likely to open a term deposit", 18, color=SOFT)
    s.shapes.add_picture(str(dots), 0, Inches(4.72), SW, Inches(2.78))
    for i, (name, sid) in enumerate(R.MEMBERS):
        x = X0 + Inches(i * 2.95)
        text(s, x, Inches(4.0), Inches(2.8), Inches(0.3), name, 15, True, WHITE)
        text(s, x, Inches(4.32), Inches(2.8), Inches(0.3), sid, 12, color=RGBColor(0xE0, 0x8A, 0x3C), font=MONO,
             spacing=100)

    # 2 Problem -------------------------------------------------------------
    s = new_slide("The problem", "Nearly nine in ten sales calls end in a “no”", M1,
                  f"The bank phoned {n_rows:,} clients. Only {pct(avg)} opened a term deposit. Calling everyone in "
                  "turn wastes agent hours on people who were never going to say yes.")
    on = round(avg * 100)
    size, gap = Inches(0.3), Inches(0.1)
    for k in range(100):
        r, c = divmod(k, 10)
        col = BLUE if k >= 100 - on else DOT_OFF
        rect(s, X0 + c * (size + gap), Inches(2.3) + r * (size + gap), size, size, col, shape=MSO_SHAPE.OVAL)
    text(s, X0, Inches(6.38), Inches(6.5), Inches(0.3),
         f"Each dot = 1% of calls  ·  blue = client opened a term deposit ({pct(avg)})", 12, color=MUTED)
    text(s, Inches(6.6), Inches(2.35), Inches(5.8), Inches(0.6), f"{n_rows:,}", 34, True, INK)
    text(s, Inches(6.6), Inches(2.98), Inches(5.8), Inches(0.3), "phone calls in the bank's campaigns, 2008–2010",
         13, color=MUTED)
    text(s, Inches(6.6), Inches(3.5), Inches(5.8), Inches(0.6), f"only {pct(avg)}", 34, True, BLUE)
    text(s, Inches(6.6), Inches(4.13), Inches(5.8), Inches(0.3), "ended with the client saying yes", 13, color=MUTED)
    hline(s, Inches(6.6), Inches(4.75), Inches(5.85), INK, 0.75)
    text(s, Inches(6.6), Inches(4.95), Inches(5.85), Inches(1.0),
         "Calling everyone in turn wastes agent time and annoys clients who were never going to say yes.",
         17, True, INK)

    # 3 Solution ------------------------------------------------------------
    s = new_slide("Our solution", None, M1,
                  "The idea in one sentence, then the three things the app does.")
    text(s, X0, Inches(2.2), Inches(11.2), Inches(2.4),
         ["Our predictor scores every client **before the call**, so the team phones the most promising people first."],
         38, True, INK, accent=BLUE, line_spacing=1.05)
    cols = [("Score one client", "Fill in a short form and instantly get a yes / no and how likely it is."),
            ("Rank a whole call list", "Upload a CSV and get it back sorted from most to least promising."),
            ("Understand why", "Charts show which clients and which timing tend to lead to a yes.")]
    for i, (t, sub) in enumerate(cols):
        x = X0 + Inches(i * 3.92)
        hline(s, x, Inches(5.1), Inches(3.7), INK, 0.75)
        text(s, x, Inches(5.27), Inches(3.8), Inches(0.3), t, 17, True, INK)
        text(s, x, Inches(5.62), Inches(3.6), Inches(0.8), sub, 13, color=MUTED)

    # 4 Value ---------------------------------------------------------------
    s = new_slide("The value", "What scoring clients first gives the bank", M1,
                  "Four business benefits. Keep it non-technical; the numbers come later.")
    vals = [("Fewer wasted calls", "Agents spend their time on the clients most likely to say yes."),
            ("More sales from the same effort", f"Calling the top 20% of the list reaches {g[20][0]:.0f}% of all "
                                                f"subscribers."),
            ("Smarter campaign timing", "The data shows when and how to call, and when not to bother."),
            ("Kinder to clients", "Fewer repeat calls to people who were never interested.")]
    for i, (t, sub) in enumerate(vals):
        x = X0 + Inches((i % 2) * 5.89)
        y = Inches(2.28 + (i // 2) * 2.17)
        card(s, x, y, Inches(5.66), Inches(1.94))
        text(s, x + Inches(0.28), y + Inches(0.3), Inches(5.1), Inches(0.35), t, 20, True, INK)
        text(s, x + Inches(0.28), y + Inches(0.78), Inches(5.1), Inches(0.9), sub, 15, color=MUTED)

    # 5 How it works --------------------------------------------------------
    s = new_slide("How it works", "From past calls to a prediction in four steps", M2,
                  "Data → cleaning → six models compared → web app. Gradient Boosting builds many small decision "
                  "trees, each one correcting the mistakes of the previous ones.")
    steps = [("Learn from past calls", f"{n_rows:,} real calls from a Portuguese bank, each with its outcome."),
             ("Clean it and keep it fair", "Checked quality and removed call length, which is only known after "
                                           "the call."),
             ("Compare six models", "Each one tuned and tested the same way. The best one wins."),
             ("Serve it in an app", "A web dashboard and API give predictions on demand.")]
    for i, (t, sub) in enumerate(steps):
        x = X0 + Inches(i * 3.03)
        card(s, x, Inches(2.28), Inches(2.47), Inches(3.0))
        text(s, x + Inches(0.28), Inches(2.56), Inches(1.9), Inches(0.45), f"{i + 1:02d}", 22, color=BLUE, font=MONO)
        text(s, x + Inches(0.28), Inches(3.1), Inches(1.95), Inches(0.7), t, 17, True, INK)
        text(s, x + Inches(0.28), Inches(3.85), Inches(1.95), Inches(1.3), sub, 13, color=MUTED)
        if i < 3:
            rect(s, x + Inches(2.57), Inches(3.62), Inches(0.36), Inches(0.3), BLUE, shape=MSO_SHAPE.RIGHT_ARROW)
    text(s, X0, Inches(5.6), Inches(11.9), Inches(0.35),
         f"Behind the scenes, **{best}** builds many small decision trees, each one fixing the mistakes of the last.",
         15, color=MUTED, accent=INK)

    # 6 What the data told us -------------------------------------------------
    mo, po = rate["month"], rate["poutcome"]
    s = new_slide("What the data told us", "When and how you call matters most", M2,
                  f"Bars show the share of each group that subscribed; the dashed line is the {pct(avg)} average. "
                  f"May had {mo['may']['count'] / n_rows:.0%} of all calls but one of the lowest success rates.")
    segs = [("Said yes in the last campaign", po["success"]["rate"]),
            ("Called in March", mo["mar"]["rate"]),
            ("Called in September", mo["sep"]["rate"]),
            ("Aged over 65", rate["age_group"]["65+"]["rate"]),
            ("Students", rate["job"]["student"]["rate"]),
            ("Called on a mobile", rate["contact"]["cellular"]["rate"]),
            ("Called in May", mo["may"]["rate"]),
            ("Called 10+ times", cr["10+"]),
            ("Contact channel unknown", rate["contact"]["unknown"]["rate"])]
    bx, bw, top, rh = Inches(4.0), Inches(4.3), Inches(2.2), Inches(0.46)
    vmax = max(v for _, v in segs)
    for i, (label, v) in enumerate(segs):
        y = top + rh * i
        text(s, X0, y, Inches(3.0), Inches(0.3), label, 13, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)
        w = int(bw * v / vmax)
        rect(s, bx, y + Inches(0.03), w, Inches(0.26), BLUE if v > avg else RUST)
        text(s, bx + w + Inches(0.08), y, Inches(0.9), Inches(0.3), pct(v), 12, True, TEXT, anchor=MSO_ANCHOR.MIDDLE)
    ax = bx + int(bw * avg / vmax)
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, ax, top - Inches(0.1), ax, top + rh * len(segs))
    ln.line.color.rgb = INK
    ln.line.width = Pt(1)
    ln.line.dash_style = MSO_LINE.DASH
    text(s, ax - Inches(0.6), top + rh * len(segs) + Inches(0.02), Inches(1.6), Inches(0.25),
         f"average {pct(avg)}", 11, color=MUTED, align=PP_ALIGN.CENTER)
    text(s, Inches(9.55), Inches(2.25), Inches(2.9), Inches(0.7), f"{po['success']['rate'] / avg:.1f}×", 40, True, BLUE)
    text(s, Inches(9.55), Inches(2.98), Inches(2.9), Inches(0.6),
         "more likely to say yes if they said yes last time", 13, color=MUTED)
    text(s, Inches(9.55), Inches(3.95), Inches(2.9), Inches(0.7), f"{mo['may']['count'] / n_rows:.0%}", 40, True, RUST)
    text(s, Inches(9.55), Inches(4.68), Inches(2.9), Inches(0.6),
         f"of all calls were made in May, when only {pct(mo['may']['rate'])} said yes", 13, color=MUTED)

    # 7 Demo ----------------------------------------------------------------
    s = new_slide("Live demo · about 4 minutes", "Following one call list through the app", M4,
                  "Demo order: Home → Prediction (single client: defaults, then a likely client) → Prediction "
                  "(Batch CSV: upload, show the sorted list, Download CSV) → EDA → Models. Backup screenshots are "
                  "at the end of the deck.", dark=True, footer=False)
    dark_table(s, Inches(0.9), Inches(2.29), Inches(11.54), ["", "Page", "What we show", "Look for"], [
        ["1", "Home", "What the tool does and the model in use", "One-line summary of the serving model"],
        ["2", "Prediction · single client", "Score a likely and an unlikely client", "Probability bar and priority"],
        ["3", "Prediction · batch (CSV)", "Upload a whole call list", "Best leads sorted to the top, export"],
        ["4", "EDA", "Key findings and interactive charts", "Which clients say yes most often"],
        ["5", "Models", "Six models side by side", f"Why {best} was chosen"],
    ], [0.5, 2.6, 4.2, 4.2], 0.56, 15)

    # 8 Findings: lift ------------------------------------------------------
    s = new_slide("Findings", "Calling by score finds subscribers far faster", M3,
                  f"If the team calls clients in the model's order, the first 10% of calls reach {g[10][0]:.0f}% of "
                  f"all subscribers, {g[10][1]:.1f} times better than calling in random order.",
                  footnote=f"Measured on {test_n:,} test clients the model never saw during training")
    legend(s, Inches(2.17), [("Calling in random order", SAND, 2.2), (f"Calling in our model's order ({best})", BLUE, 4.0)])
    hline(s, X0, Inches(2.68), CW)
    for i, p in enumerate((10, 20, 30)):
        y = Inches(2.9 + i * 0.96)
        bar_row(s, y, f"Top {p}% of the list", "share of subscribers reached", p, g[p][0], 100,
                lambda v: f"{v:.0f}%", f"{g[p][1]:.1f}×")
        hline(s, X0, y + Inches(0.75), CW, CARD_LINE, 0.75)

    # 9 Findings: threshold -------------------------------------------------
    fp_cut = 1 - cm["fp"] / d["fp"]
    s = new_slide("Findings", f"Tuning the decision point cut wasted calls by {fp_cut:.0%}", M3,
                  f"By default a model says 'yes' above 50%. We tuned that cut-off to {tuned['threshold']:.0%} using "
                  "training data only. Fewer clients are flagged wrongly; we find somewhat fewer subscribers, but "
                  "each call is far more likely to succeed. The cut-off is a business choice.",
                  footnote=f"Same {test_n:,} test clients for both  ·  balance score (F1) "
                           f"{bm['test']['f1']:.2f} → {tuned['f1']:.2f}")
    legend(s, Inches(2.17), [("Default cut-off (50%)", SAND, 2.0), (f"Tuned cut-off ({tuned['threshold']:.0%})", BLUE, 2.4)])
    hline(s, X0, Inches(2.68), CW)
    p0, p1 = bm["test"]["precision"], tuned["precision"]
    rows9 = [("Wasted calls", "clients flagged who said no", d["fp"], cm["fp"], lambda v: f"{v:,.0f}",
              f"−{fp_cut:.0%}", RUST),
             ("Hit rate", "flagged clients who said yes", p0 * 100, p1 * 100, lambda v: f"{v:.0f}%",
              f"+{(p1 - p0) * 100:.0f} pts", RUST),
             ("Subscribers found", "out of " + f"{cm['tp'] + cm['fn']:,}", d["tp"], cm["tp"], lambda v: f"{v:,.0f}",
              f"−{1 - cm['tp'] / d['tp']:.0%}", SAND)]
    for i, (lab, sub, a, b, fmt, ch, col) in enumerate(rows9):
        y = Inches(2.9 + i * 0.96)
        bar_row(s, y, lab, sub, a, b, max(a, b), fmt, ch, col)
        hline(s, X0, y + Inches(0.75), CW, CARD_LINE, 0.75)

    # 10 Model choice -------------------------------------------------------
    knn = R.by_name("K-Nearest Neighbours")
    s = new_slide("Model choice", f"Why we chose {best} from six models", M3,
                  "All six were tuned with cross-validation on training data and compared on ROC-AUC, which "
                  "measures how well a model ranks likely subscribers above unlikely ones. KNN shows why accuracy "
                  "alone is misleading when only 12% say yes.",
                  footnote="Test set, default 50% cut-off. The winner was picked on cross-validated ROC-AUC, never "
                           "on test results.")
    light_table(s, Inches(0.9), Inches(2.18), Inches(11.54),
                ["Model", "Ranks clients well (ROC-AUC)", "Finds subscribers (recall)", "Hit rate (precision)",
                 "Accuracy"],
                [[x["name"] + ("  · selected" if x["name"] == best else ""), f"{x['test']['roc_auc']:.3f}",
                  pct(x["test"]["recall"], 0), pct(x["test"]["precision"], 0), pct(x["test"]["accuracy"], 0)]
                 for x in ranked], [3.6, 2.2, 2.0, 1.9, 1.4], 0.44, 14,
                highlight=next(i for i, x in enumerate(ranked) if x["name"] == best))
    text(s, X0, Inches(5.5), Inches(11.5), Inches(0.6),
         [f"{best} ranked clients best both in cross-validation and on unseen data. KNN looks most accurate "
          f"({pct(knn['test']['accuracy'], 0)}) but finds only **{pct(knn['test']['recall'], 0)}** of subscribers."],
         15, True, INK, accent=RUST)

    # 11 Drivers ------------------------------------------------------------
    friendly = {"month": "Month of the call", "contact": "Contact channel", "poutcome": "Last campaign's outcome",
                "day": "Day of the month", "age": "Age", "housing": "Has a housing loan", "balance": "Account balance",
                "campaign": "Calls in this campaign", "loan": "Has a personal loan", "pdays": "Days since last call",
                "job": "Job", "education": "Education", "marital": "Marital status", "default": "Credit in default",
                "previous": "Previous contacts"}
    imp = m["feature_importance"][:7]
    s = new_slide("What drives a prediction", "The model listens to timing, channel and history", M2,
                  "Permutation importance: shuffle one input and measure how much worse the model ranks clients. "
                  "This agrees with the EDA: timing, channel and the previous outcome dominate.")
    vmax = imp[0]["importance"]
    for i, f in enumerate(imp):
        y = Inches(2.3) + Inches(0.55) * i
        text(s, X0, y, Inches(2.9), Inches(0.34), friendly.get(f["feature"], f["feature"]), 14,
             i < 3, INK if i < 3 else TEXT, anchor=MSO_ANCHOR.MIDDLE)
        w = int(Inches(4.6) * f["importance"] / vmax)
        rect(s, Inches(3.9), y + Inches(0.04), w, Inches(0.27), BLUE if i < 3 else SAND)
    card(s, Inches(9.0), Inches(2.3), Inches(3.45), Inches(3.6), top_accent=True)
    text(s, Inches(9.25), Inches(2.6), Inches(3.0), Inches(0.35), "How we measured it", 16, True, INK)
    text(s, Inches(9.25), Inches(3.05), Inches(3.0), Inches(1.4),
         "Shuffle one input and see how much worse the model gets. The bigger the drop, the more it matters.",
         13, color=MUTED)
    text(s, Inches(9.25), Inches(4.15), Inches(3.0), Inches(1.3),
         "Job, education and marital status barely matter once timing and history are known.", 13, True, INK)

    # 12 Trust --------------------------------------------------------------
    s = new_slide("Trust", "Built to be honest about what it knows", M4,
                  "Leakage: duration is only known after the call ends, so using it would be cheating. All learned "
                  "steps (outlier limits, scaling, encoding) are fitted on training folds only.")
    gaps = max(abs(x["cv_roc_auc"] - x["test"]["roc_auc"]) for x in m["models"])
    trust = [("No peeking at the answer", "Call length is only known after the call, so we removed it. Every "
                                          "cleaning step learns from training data only."),
             ("Tested on unseen clients", f"20% of clients were locked away until the end. Training and test "
                                          f"scores agree within {gaps:.2f}."),
             ("Honest about limits", f"About {pct(tuned['precision'], 0)} of flagged clients say yes. Scores rank "
                                     "clients well but are not exact probabilities.")]
    for i, (t, sub) in enumerate(trust):
        x = X0 + Inches(i * 3.92)
        card(s, x, Inches(2.28), Inches(3.7), Inches(2.1), top_accent=True)
        text(s, x + Inches(0.28), Inches(2.6), Inches(3.24), Inches(0.35), t, 17, True, INK)
        text(s, x + Inches(0.28), Inches(3.02), Inches(3.24), Inches(1.3), sub, 13, color=MUTED)
    text(s, X0, Inches(4.7), Inches(11.9), Inches(0.35),
         "Verified with **8 passing automated API tests**, a frontend routing test and manual end-to-end checks of "
         "every page.", 14, color=MUTED, accent=INK)

    # 13 Next steps ---------------------------------------------------------
    s = new_slide("Next steps", "From a working prototype to the call centre", M4,
                  "Concrete improvements, most important first.")
    nxt = [("Retrain on recent data", "The calls are from 2008–2010; client behaviour has changed since."),
           ("Put a price on each call", "Set the cut-off from real call costs and deposit profits."),
           ("Explain every prediction", "Show the reasons behind each client's score in the dashboard."),
           ("Ship it securely", "Add login, cloud hosting and monitoring for real use.")]
    hline(s, X0, Inches(2.28), CW)
    for i, (t, sub) in enumerate(nxt):
        y = Inches(2.5 + i * 0.85)
        text(s, X0, y, Inches(0.7), Inches(0.42), f"{i + 1:02d}", 22, color=BLUE, font=MONO)
        text(s, Inches(1.78), y + Inches(0.02), Inches(4.6), Inches(0.4), t, 19, True, INK)
        text(s, Inches(6.56), y + Inches(0.06), Inches(5.9), Inches(0.4), sub, 14, color=MUTED)
        hline(s, X0, y + Inches(0.63), CW, CARD_LINE, 0.75)

    # 14 Team ---------------------------------------------------------------
    s = new_slide("The team", "Four members, one pipeline · 25% each", None,
                  "Each member owned one stage of the data mining process and the matching part of the app. "
                  "Shared: problem definition, code reviews, integration testing, report and this presentation.")
    team = [("Data & batch scoring", ["Data download & cleaning", "Data leakage checks",
                                      "Batch CSV scoring"]),
            ("EDA & features", ["Exploratory analysis", "Feature engineering", "Outlier capping", "EDA page"]),
            ("Models & evaluation", ["Six models compared", "Cut-off tuning", "Feature importance",
                                     "Models page & report"]),
            ("API, app & testing", ["FastAPI backend", "Home & prediction pages", "App shell & routing",
                                    "Automated tests"])]
    for i, ((name, sid), (role, items)) in enumerate(zip(R.MEMBERS, team)):
        x = X0 + Inches(i * 2.94)
        card(s, x, Inches(2.28), Inches(2.74), Inches(3.95), top_accent=True)
        text(s, x + Inches(0.22), Inches(2.55), Inches(2.4), Inches(0.35), name, 15, True, INK)
        text(s, x + Inches(0.22), Inches(2.9), Inches(2.4), Inches(0.3), sid, 12, color=RUST, font=MONO, spacing=100)
        hline(s, x + Inches(0.22), Inches(3.35), Inches(2.3), CARD_LINE, 0.75)
        text(s, x + Inches(0.22), Inches(3.5), Inches(2.4), Inches(0.35), role, 14, True, BLUE)
        text(s, x + Inches(0.22), Inches(3.95), Inches(2.35), Inches(2.0), [f"•  {it}" for it in items], 13,
             color=MUTED, line_spacing=1.4)

    # 15 Close --------------------------------------------------------------
    s = new_slide("In one sentence", None, M4, "Summarise in one sentence, thank the panel, open for questions.",
                  dark=True, footer=False)
    s.shapes.add_picture(str(curve), 0, Inches(4.72), SW, Inches(2.78))
    text(s, X0, Inches(1.36), Inches(11.3), Inches(1.9),
         f"Our predictor tells the call team who to phone first, reaching {g[10][0]:.0f}% of subscribers in the "
         "first 10% of calls.", 36, True, WHITE, line_spacing=1.05)
    text(s, X0, Inches(3.45), Inches(11.9), Inches(0.5), "Thank you · questions?", 22, color=SOFT)
    text(s, X0, Inches(4.05), Inches(11.9), Inches(0.3),
         "   ·   ".join(f"{n} ({sid})" for n, sid in R.MEMBERS), 12, color=RGBColor(0xE0, 0x8A, 0x3C))

    # Backups ---------------------------------------------------------------
    shots = [("00_home.png", "Home · what the tool does and the model in use"),
             ("01_predict.png", "Prediction · scoring a single client"),
             ("02_batch.png", "Prediction · scoring a whole call list from a CSV"),
             ("04_insights.png", "EDA · key findings at a glance"),
             ("03_models.png", "Models · six models compared")]
    for fname, title in shots:
        _slide_no[0] += 1
        s = prs.slides.add_slide(BLANK)
        background(s)
        text(s, Inches(2.0), Inches(0.6), Inches(9.6), Inches(0.3), "BACKUP · DEMO SCREEN", 11, color=RUST,
             font=MONO, spacing=300)
        text(s, Inches(2.0), Inches(0.95), Inches(9.6), Inches(0.45), title, 22, True, INK)
        picture(s, R.SHOTS / fname, Inches(2.0), Inches(1.6), Inches(9.33), Inches(5.6))

    s = new_slide("Backup · full results", "Every model on the test set", None,
                  f"Test set ({test_n:,} clients), default 50% cut-off; tuned {best} shown in the last row.",
                  head_size=28)
    rows = [[x["name"], f"{x['cv_roc_auc']:.3f}", f"{x['test']['roc_auc']:.3f}", f"{x['test']['pr_auc']:.3f}",
             f"{x['test']['f1']:.3f}", f"{x['test']['precision']:.3f}", f"{x['test']['recall']:.3f}",
             f"{x['test']['accuracy']:.3f}"] for x in ranked]
    rows.append([f"{best} (cut-off {tuned['threshold']:.2f})", "–", f"{tuned['roc_auc']:.3f}", f"{tuned['pr_auc']:.3f}",
                 f"{tuned['f1']:.3f}", f"{tuned['precision']:.3f}", f"{tuned['recall']:.3f}", f"{tuned['accuracy']:.3f}"])
    light_table(s, Inches(0.9), Inches(2.1), Inches(11.54),
                ["Model", "CV ROC-AUC", "Test ROC-AUC", "PR-AUC", "F1", "Precision", "Recall", "Accuracy"],
                rows, [3.6, 1.3, 1.3, 1.1, 1.0, 1.2, 1.1, 1.2], 0.44, 13, highlight=len(rows) - 1)
    text(s, X0, Inches(5.95), Inches(11.5), Inches(0.6),
         f"Stratified 80/20 split ({m['train_size']:,} train / {test_n:,} test), grid search with 3-fold "
         "cross-validation, balanced class weights, cut-off tuned for F1 on out-of-fold training predictions.",
         12, color=MUTED)

    prs.save(OUT)
    print(f"Saved {OUT}  ({_slide_no[0]} slides)")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    build()
