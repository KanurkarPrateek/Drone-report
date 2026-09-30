"""Render the inspection report PDF."""

from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak, Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .profiles import PROFILES, SEVERITY_NAMES, action_label, actions_for

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
RULE = colors.HexColor("#e2e8f0")
PANEL = colors.HexColor("#f8fafc")
BRAND = colors.HexColor("#0b3b5c")
PRIORITY = {"P1": colors.HexColor("#dc2626"), "P2": colors.HexColor("#ea8a00"), "P3": colors.HexColor("#2563eb")}
PRIORITY_TEXT = {"P1": "Immediate (within 24-72 h)", "P2": "Planned (within 30 days)", "P3": "Scheduled / monitor (next maintenance cycle)"}
CONDITION = {"Good": "#16a34a", "Fair": "#ca8a04", "Poor": "#ea580c", "Critical": "#dc2626"}

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=28, leading=34, textColor=INK, alignment=0),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=13, leading=18, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=BRAND, spaceBefore=4, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=INK, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.3, leading=10.5, textColor=INK),
    "kpi": ParagraphStyle("kpi", fontName="Helvetica-Bold", fontSize=24, leading=28, alignment=TA_CENTER),
    "kpil": ParagraphStyle("kpil", fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def E(text) -> str:
    return escape(str(text))


def _fmt_time(t):
    if t is None:
        return "still"
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def _sev_name(v):
    return SEVERITY_NAMES[min(4, max(0, round(v)))]


def _pill(text, color, width=None):
    t = Table([[Paragraph(f"<font color='white'><b>{E(text)}</b></font>", S["cell"])]], colWidths=[width] if width else None)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("ROUNDEDCORNERS", [3, 3, 3, 3])]))
    return t


def _bullets(items, style="body"):
    return ListFlowable([ListItem(P(E(i), style), leftIndent=10, value="•") for i in items],
                        bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8)


def _fit_image(path, max_w, max_h):
    img = Image(str(path))
    ratio = min(max_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
    return img


def _on_page(d):
    def draw(canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFillColor(BRAND)
            canvas.rect(0, PAGE_H - 10 * mm, PAGE_W, 10 * mm, stroke=0, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8.5)
            canvas.drawString(MARGIN, PAGE_H - 6.5 * mm, f"Drone Inspection Report  |  {d['site']}")
            canvas.setFont("Helvetica", 8.5)
            canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 6.5 * mm, d["date"])
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(MARGIN, 10 * mm, "AI-assisted inspection. Findings must be verified on site by a qualified inspector before repair.")
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
        if d["mock"]:
            canvas.setFillColor(colors.Color(0.86, 0.15, 0.15, alpha=0.12))
            canvas.setFont("Helvetica-Bold", 70)
            canvas.translate(PAGE_W / 2, PAGE_H / 2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "DEMO DATA")
        canvas.restoreState()
    return draw


def _cover(d, counts):
    s = d["summary"]
    cond = s.overall_condition if s else "Good"
    out = [Spacer(1, 30 * mm),
           P("DRONE INSPECTION REPORT", "small"), Spacer(1, 3 * mm),
           P(E(d["site"]), "title"), Spacer(1, 2 * mm),
           P(f"{E(d['profile_name'])} &nbsp;·&nbsp; {E(d['date'])}", "subtitle"), Spacer(1, 14 * mm)]

    cond_cell = [P("OVERALL CONDITION", "kpil"), Spacer(1, 2 * mm), _pill(cond.upper(), colors.HexColor(CONDITION[cond]), 38 * mm)]
    kpis = [[cond_cell]]
    for label, value, color in (("Findings", counts["total"], INK), ("P1 Immediate", counts["P1"], PRIORITY["P1"]),
                                ("P2 Planned", counts["P2"], PRIORITY["P2"]), ("P3 Monitor", counts["P3"], PRIORITY["P3"])):
        kpis[0].append([Paragraph(f"<font color='{color.hexval()}'>{value}</font>", S["kpi"]), P(label, "kpil")])
    t = Table(kpis, colWidths=[46 * mm] + [(CONTENT_W - 46 * mm) / 4] * 4)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE),
                           ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 10),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    out += [t, Spacer(1, 14 * mm)]

    m = d["meta"]
    rows = [["Source footage", d["source"]],
            ["Footage length", f"{m['duration_s']} s" if m.get("duration_s") else "Still images"],
            ["Frames analysed", f"{d['frames_total']}" + (f" (one every {m['interval_s']} s)" if m.get("interval_s") else "")],
            ["Raw observations", f"{d['observations_raw']} ({d['dropped_false_alarms']} rejected as likely false alarms)"],
            ["Detection model", d["models"]["vision"]],
            ["Triage model", f"TypeSafe Jev ({d['models']['judgment']})"],
            ["Processing time", f"{d['elapsed_s']} s"]]
    t = Table([[P(a, "small"), P(E(b), "cell")] for a, b in rows], colWidths=[40 * mm, CONTENT_W - 40 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    legend = Table([[_pill(p, PRIORITY[p], 12 * mm), P(PRIORITY_TEXT[p], "cell")] for p in ("P1", "P2", "P3")],
                   colWidths=[16 * mm, CONTENT_W - 16 * mm])
    legend.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    out += [t, Spacer(1, 12 * mm), P("How urgent is each priority", "h2"), legend, PageBreak()]
    return out


def _summary(d, counts):
    s, out = d["summary"], [P("1. Executive summary", "h1")]
    if not s:
        return out + [P("No defects were detected in the analysed footage. See the methodology section for coverage limits."), PageBreak()]
    out += [P(E(s.summary)), Spacer(1, 4 * mm), P("Key risks", "h2"), _bullets(s.key_risks)]

    out += [P("Findings by category", "h2"), _category_chart(d["findings"]), Spacer(1, 2 * mm)]

    out += [P("2. Action plan", "h1")]
    plan = [("Immediate (24-72 hours)", s.immediate_actions, PRIORITY["P1"]),
            ("Next 30 days", s.next_30_days, PRIORITY["P2"]),
            ("Next 90 days", s.next_90_days, PRIORITY["P3"])]
    for title, items, color in plan:
        box = Table([[P(f"<font color='{color.hexval()}'><b>{title}</b></font>", "body")], [_bullets(items or ["None"])]],
                    colWidths=[CONTENT_W])
        box.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, color), ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 4),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        out += [KeepTogether(box), Spacer(1, 3 * mm)]
    out.append(PageBreak())
    return out


def _category_chart(findings):
    by_cat = Counter(f["judgment"]["category"] for f in findings)
    rows = by_cat.most_common()
    bar_h, gap, label_w = 11, 5, 150
    height = len(rows) * (bar_h + gap) + 4
    dwg = Drawing(CONTENT_W, height)
    top = max(by_cat.values())
    usable = CONTENT_W - label_w - 30
    for i, (cat, n) in enumerate(rows):
        y = height - (i + 1) * (bar_h + gap)
        dwg.add(String(0, y + 2, cat.replace("_", " ").capitalize(), fontName="Helvetica", fontSize=8, fillColor=INK))
        x = label_w
        for pr in ("P1", "P2", "P3"):
            k = sum(1 for f in findings if f["judgment"]["category"] == cat and f["judgment"]["priority"] == pr)
            if k:
                w = usable * k / top
                dwg.add(Rect(x, y, w, bar_h, fillColor=PRIORITY[pr], strokeColor=None))
                x += w
        dwg.add(String(x + 4, y + 2, str(n), fontName="Helvetica-Bold", fontSize=8, fillColor=INK))
    return dwg


def _register(d):
    out = [P("3. Findings register", "h1"),
           P("All findings, most urgent first. Each is detailed with photos and repair steps in section 4.", "small"),
           Spacer(1, 3 * mm)]
    head = ["ID", "Time", "Issue", "Category", "Severity", "Priority", "Action"]
    data = [[P(f"<b>{h}</b>", "cell") for h in head]]
    for f in d["findings"]:
        j = f["judgment"]
        data.append([P(f"<b>{f['id']}</b>", "cell"), P(_fmt_time(f["frame"].timestamp_s), "cell"),
                     P(E(f["obs"]["label"]) + (" <font color='#dc2626'><b>[verify on site]</b></font>" if j.get("needs_review") else ""), "cell"), P(E(j["category"].replace("_", " ")), "cell"),
                     P(f"{_sev_name(j['severity'])} ({j['severity']:.1f})", "cell"),
                     _pill(j["priority"], PRIORITY[j["priority"]], 12 * mm),
                     P(E(action_label(d["profile"], j["action"])), "cell")])
    widths = [12 * mm, 15 * mm, 52 * mm, 28 * mm, 24 * mm, 17 * mm, CONTENT_W - 148 * mm]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), PANEL), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return out + [t, PageBreak()]


def _severity_bars(probs: dict):
    dwg = Drawing(60 * mm, 26)
    w = 60 * mm / 5
    for lvl in range(5):
        p = probs.get(lvl, 0.0)
        dwg.add(Rect(lvl * w + 1, 8, w - 2, 16, fillColor=PANEL, strokeColor=RULE, strokeWidth=0.4))
        dwg.add(Rect(lvl * w + 1, 8, w - 2, 16 * p, fillColor=BRAND, strokeColor=None))
        dwg.add(String(lvl * w + w / 2, 0, f"{lvl} {SEVERITY_NAMES[lvl]}", fontName="Helvetica", fontSize=5.5,
                       fillColor=MUTED, textAnchor="middle"))
    return dwg


def _finding(f, d):
    j, o, g = f["judgment"], f["obs"], f["guidance"]
    color = PRIORITY[j["priority"]]
    head = Table([[P(f"<font color='white'><b>{f['id']} &nbsp; {E(o['label'])}</b></font>", "body"),
                   P(f"<font color='white'><b>{j['priority']} · {PRIORITY_TEXT[j['priority']]}</b></font>", "cell")]],
                 colWidths=[CONTENT_W * 0.6, CONTENT_W * 0.4])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))

    imgs = Table([[_fit_image(f["image"], CONTENT_W * 0.64, 68 * mm), _fit_image(f["crop"], CONTENT_W * 0.34, 68 * mm)],
                  [P("Full frame with approximate location", "small"), P("Zoomed detail", "small")]],
                 colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35])
    imgs.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    seen = f"{len(f['frames'])} frame(s)" + (f", from {_fmt_time(f['frames'][0].timestamp_s)}" if f["frames"][0].timestamp_s is not None else "")
    facts = [
        ("Timestamp", f"{_fmt_time(f['frame'].timestamp_s)} (seen in {seen})"),
        ("Component", o["component"]),
        ("Extent", o["extent"]),
        ("Category", f"{j['category'].replace('_', ' ')} ({j['category_confidence']:.0%} confidence)"),
        ("Severity", f"{_sev_name(j['severity'])}, score {j['severity']:.2f} / 4"),
        ("Safety / environmental hazard", f"{j['hazard']:.0%} probability"),
        ("Likelihood it is a real defect", f"{j['genuine']:.0%}" + (" - VERIFY ON SITE before work" if j.get("needs_review") else "")),
        ("First action", f"{action_label(d['profile'], j['action'])}: {actions_for(d['profile']).get(j['action'], '')}"),
        ("Crew", g["crew"]),
    ]
    ft = Table([[P(k, "small"), P(E(v), "cell")] for k, v in facts] +
               [[P("Severity spread (Jev)", "small"), _severity_bars(j["severity_probabilities"])]],
               colWidths=[48 * mm, CONTENT_W - 48 * mm])
    ft.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

    body = [P("What we saw", "h2"), P(E(o["description"])),
            P(f"<i>Visual evidence:</i> {E(o['visual_evidence'])}", "small"),
            P("How to fix it", "h2"), P(f"<b>For this finding:</b> {E(o['suggested_fix'])}"), Spacer(1, 2 * mm),
            P("<b>Standard procedure</b>", "body"),
            ListFlowable([ListItem(P(E(s)), leftIndent=12) for s in g["steps"]], bulletType="1", leftIndent=14,
                         bulletFontSize=8.5)]
    if g["references"]:
        body.append(P("References: " + E("; ".join(g["references"])), "small"))

    return [CondPageBreak(120 * mm), KeepTogether([head, Spacer(1, 3 * mm), imgs]), Spacer(1, 3 * mm), ft,
            *body, Spacer(1, 9 * mm)]


def _method(d):
    th = d["thresholds"]
    out = [PageBreak(), P("5. Methodology and limitations", "h1"),
           P("How this report was produced", "h2"),
           _bullets([
               f"Frames were sampled from the footage "
               f"({'one every ' + str(d['meta']['interval_s']) + ' s' if d['meta'].get('interval_s') else 'still images'}, "
               f"{d['frames_total']} in total).",
               f"Detection: each frame was examined by a vision-language model ({d['models']['vision']}) that listed every "
               "visible defect with its location, extent and visual evidence. It did not assign severity.",
               f"Triage: each observation was scored by TypeSafe Jev ({d['models']['judgment']}), a System One model that returns "
               "typed answers with probabilities: defect category, severity on a 5-level rubric, first action, the probability that "
               "the defect is genuine, and the probability of an immediate safety or environmental hazard.",
               f"Rules applied by code: observations with less than {th['drop_if_genuine_below']:.0%} probability of being genuine "
               f"were dropped; P1 if expected severity is {th['p1_min_severity']} or higher or hazard probability is "
               f"{th['hazard_forces_p1']:.0%} or higher, or the recommended action is shutdown and severity is {th['shutdown_min_severity']} or higher; P2 if severity is {th['p2_min_severity']} or higher; "
               f"otherwise P3. Findings with less than {th['review_if_genuine_below']:.0%} probability of being genuine are capped at P2 and marked 'verify on site'.",
               "The same defect seen in neighbouring frames was merged into one finding.",
               "Repair procedures come from a reviewed playbook for this asset type; the per-finding fix is model-generated.",
           ]),
           P("Severity scale", "h2")]
    from .profiles import SEVERITY_LEVELS
    out.append(_bullets([f"{i}: {s}" for i, s in enumerate(SEVERITY_LEVELS)]))
    out += [P("Limitations", "h2"), _bullets([
        "Only what is visible from the air is assessed. Internal corrosion, wall thickness, electrical faults and gas leaks "
        "without a visible sign cannot be detected from RGB footage.",
        "Hotspot findings need radiometric thermal footage; on RGB footage they are not reliable.",
        "Locations are approximate boxes on the frame, not GPS coordinates.",
        "AI findings can be wrong. Every P1 and P2 finding should be confirmed on site before work starts.",
    ])]
    if d.get("credits"):
        out += [P("Image credits", "h2"), _bullets(d["credits"], "small")]
    if d["frames_failed"]:
        out += [P("Frames that could not be analysed", "h2"),
                _bullets([f"Frame {e['frame']}: {e['error']}" for e in d["frames_failed"]], "small")]
    return out


def build_pdf(d: dict, path: Path):
    counts = Counter(f["judgment"]["priority"] for f in d["findings"])
    counts["total"] = len(d["findings"])
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Drone Inspection Report - {d['site']}", author="droneinspect")
    story = _cover(d, counts) + _summary(d, counts)
    if d["findings"]:
        story += _register(d)
        story.append(P("4. Detailed findings", "h1"))
        for f in d["findings"]:
            story += _finding(f, d)
    story += _method(d)
    doc.build(story, onFirstPage=_on_page(d), onLaterPages=_on_page(d))
