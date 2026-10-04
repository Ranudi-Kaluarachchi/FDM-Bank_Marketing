"""Human-readable training outputs: console tables, PNG charts and an HTML report.

Everything is written to reports/ so results can be reviewed without the web app:
  reports/training_report.html   single self-contained page (open in any browser)
  reports/*.png                  individual charts
  reports/model_comparison.csv   comparison table for Excel / Sheets
"""
import base64
import html
import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score, f1_score, precision_recall_curve, precision_score,
    recall_score, roc_auc_score, roc_curve,
)

from ml.config import ROOT  # noqa: E402

REPORTS_DIR = ROOT / "reports"
COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]
METRIC_LABELS = {
    "roc_auc": "ROC-AUC", "pr_auc": "PR-AUC", "f1": "F1",
    "precision": "Precision", "recall": "Recall", "accuracy": "Accuracy",
}

plt.rcParams.update({
    "figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "font.size": 10,
})


# ---------------------------------------------------------------- console ----

def format_table(headers: list[str], rows: list[list], align: str | None = None) -> str:
    """Render a plain-text table with box-drawing borders."""
    cells = [[str(c) for c in r] for r in rows]
    widths = [max(len(str(h)), *(len(r[i]) for r in cells)) for i, h in enumerate(headers)]
    align = align or "l" + "r" * (len(headers) - 1)

    def line(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def fmt(row):
        parts = [(c.ljust(w) if a == "l" else c.rjust(w)) for c, w, a in zip(row, widths, align)]
        return "│ " + " │ ".join(parts) + " │"

    out = [line("┌", "┬", "┐"), fmt([str(h) for h in headers]), line("├", "┼", "┤")]
    out += [fmt(r) for r in cells]
    out.append(line("└", "┴", "┘"))
    return "\n".join(out)


def section(title: str) -> str:
    return f"\n{'═' * 78}\n  {title}\n{'═' * 78}"


def comparison_frame(metrics: dict) -> pd.DataFrame:
    rows = []
    for m in sorted(metrics["models"], key=lambda r: r["cv_roc_auc"], reverse=True):
        t = m["test"]
        rows.append({
            "Rank": len(rows) + 1,
            "Model": m["name"] + (" ★" if m["name"] == metrics["best_model"] else ""),
            "CV ROC-AUC": m["cv_roc_auc"],
            "Test ROC-AUC": t["roc_auc"],
            "Test PR-AUC": t["pr_auc"],
            "F1": t["f1"],
            "Precision": t["precision"],
            "Recall": t["recall"],
            "Accuracy": t["accuracy"],
            "Train time (s)": m["train_seconds"],
        })
    return pd.DataFrame(rows)


def print_summary(metrics: dict, gains: list[dict]) -> None:
    df = comparison_frame(metrics)
    print(section("MODEL COMPARISON (test set, threshold 0.5, ranked by CV ROC-AUC)"))
    print(format_table(list(df.columns),
                       [[f"{v:.3f}" if isinstance(v, float) and c != "Train time (s)" else v
                         for c, v in row.items()] for row in df.to_dict("records")],
                       align="rl" + "r" * (len(df.columns) - 2)))

    print(section("BEST HYPER-PARAMETERS (3-fold stratified grid search)"))
    print(format_table(["Model", "Parameters"],
                       [[m["name"], ", ".join(f"{k}={v}" for k, v in m["best_params"].items()) or "defaults"]
                        for m in metrics["models"]], align="ll"))

    t = metrics["best_model_tuned_test"]
    cm = t["confusion_matrix"]
    print(section(f"SELECTED MODEL: {metrics['best_model']}  (decision threshold {t['threshold']:.2f})"))
    print(format_table(["Metric", "Value", "Meaning"], [
        ["ROC-AUC", f"{t['roc_auc']:.3f}", "Ranking quality (0.5 = random, 1.0 = perfect)"],
        ["PR-AUC", f"{t['pr_auc']:.3f}", f"Precision-recall area (random = {(cm['tp'] + cm['fn']) / sum(cm.values()):.3f})"],
        ["Precision", f"{t['precision']:.1%}", "Of clients flagged 'yes', share who subscribed"],
        ["Recall", f"{t['recall']:.1%}", "Of actual subscribers, share the model found"],
        ["F1", f"{t['f1']:.3f}", "Balance of precision and recall"],
        ["Accuracy", f"{t['accuracy']:.1%}", "Share of all predictions correct"],
    ], align="lrl"))

    print("\n  Confusion matrix (test set)")
    print(format_table(["", "Predicted NO", "Predicted YES"], [
        ["Actual NO", f"{cm['tn']:,}  (correct)", f"{cm['fp']:,}  (wasted call)"],
        ["Actual YES", f"{cm['fn']:,}  (missed)", f"{cm['tp']:,}  (correct)"],
    ], align="lrr"))

    print(section("FEATURE IMPORTANCE (permutation: drop in ROC-AUC when shuffled)"))
    top = metrics["feature_importance"]
    peak = max(f["importance"] for f in top) or 1
    print(format_table(["#", "Feature", "Importance", ""], [
        [i + 1, f["feature"], f"{f['importance']:.4f}", "█" * max(0, round(30 * f["importance"] / peak))]
        for i, f in enumerate(top)
    ], align="rlrl"))

    print(section("CUMULATIVE GAINS (call clients in order of model score)"))
    print(format_table(["Top % of clients called", "Subscribers captured", "Lift vs random"],
                       [[f"{g['pct_called']}%", f"{g['pct_captured']:.1f}%", f"{g['lift']:.2f}x"]
                        for g in gains if g["pct_called"] in (5, 10, 20, 30, 40, 50)], align="rrr"))


# ----------------------------------------------------------------- charts ----

def _save(fig, name: str) -> str:
    path = REPORTS_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return name


def chart_model_comparison(metrics: dict) -> str:
    models = sorted(metrics["models"], key=lambda r: r["cv_roc_auc"], reverse=True)
    keys = ["roc_auc", "pr_auc", "f1", "precision", "recall"]
    x = np.arange(len(models))
    width = 0.16
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for i, k in enumerate(keys):
        vals = [m["test"][k] for m in models]
        bars = ax.bar(x + (i - 2) * width, vals, width, label=METRIC_LABELS[k], color=COLORS[i])
        if k == "roc_auc":
            ax.bar_label(bars, fmt="%.3f", fontsize=7, padding=2)
    ax.set_xticks(x, [m["name"] + (" ★" if m["name"] == metrics["best_model"] else "") for m in models])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("Model comparison on the test set (threshold 0.5)")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False)
    return _save(fig, "model_comparison.png")


def chart_cv_vs_test(metrics: dict) -> str:
    models = sorted(metrics["models"], key=lambda r: r["cv_roc_auc"])
    y = np.arange(len(models))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(y - 0.2, [m["cv_roc_auc"] for m in models], 0.4, label="Cross-validation", color=COLORS[0])
    ax.barh(y + 0.2, [m["test"]["roc_auc"] for m in models], 0.4, label="Held-out test", color=COLORS[1])
    ax.set_yticks(y, [m["name"] for m in models])
    lo = min(min(m["cv_roc_auc"], m["test"]["roc_auc"]) for m in models)
    ax.set_xlim(max(0.5, lo - 0.05), 1)
    ax.set_xlabel("ROC-AUC")
    ax.set_title("Cross-validation vs test ROC-AUC (similar values mean no over-fitting)")
    ax.legend(loc="lower right")
    return _save(fig, "cv_vs_test_auc.png")


def chart_roc(y_test, probas: dict, best: str) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for i, (name, p) in enumerate(probas.items()):
        fpr, tpr, _ = roc_curve(y_test, p)
        ax.plot(fpr, tpr, color=COLORS[i % len(COLORS)], lw=3 if name == best else 1.4,
                label=f"{name} (AUC {roc_auc_score(y_test, p):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1, label="Random guess (0.500)")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate (recall)")
    ax.set_title("ROC curves")
    ax.legend(loc="lower right", fontsize=8)
    return _save(fig, "roc_curves.png")


def chart_pr(y_test, probas: dict, best: str) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for i, (name, p) in enumerate(probas.items()):
        prec, rec, _ = precision_recall_curve(y_test, p)
        ax.plot(rec, prec, color=COLORS[i % len(COLORS)], lw=3 if name == best else 1.4,
                label=f"{name} (AP {average_precision_score(y_test, p):.3f})")
    base = float(np.mean(y_test))
    ax.axhline(base, ls="--", color="grey", lw=1, label=f"Random guess ({base:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_ylim(0, 1)
    ax.set_title("Precision-recall curves")
    ax.legend(loc="upper right", fontsize=8)
    return _save(fig, "pr_curves.png")


def chart_confusion(y_test, proba, threshold: float, best: str) -> str:
    y = np.asarray(y_test)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, thr, title in [(axes[0], 0.5, "Default threshold 0.50"),
                           (axes[1], threshold, f"Tuned threshold {threshold:.2f}")]:
        pred = (proba >= thr).astype(int)
        cm = np.array([[((y == a) & (pred == b)).sum() for b in (0, 1)] for a in (0, 1)])
        ax.imshow(cm, cmap="Blues")
        labels = [["True negative", "False positive"], ["False negative", "True positive"]]
        for i in range(2):
            for j in range(2):
                pct = cm[i, j] / cm[i].sum()
                ax.text(j, i, f"{cm[i, j]:,}\n{labels[i][j]}\n({pct:.0%} of row)", ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=9)
        ax.set_xticks([0, 1], ["Predicted NO", "Predicted YES"])
        ax.set_yticks([0, 1], ["Actual NO", "Actual YES"])
        ax.grid(False)
        ax.set_title(title)
    fig.suptitle(f"Confusion matrices: {best} (test set)")
    return _save(fig, "confusion_matrix.png")


def chart_threshold(y_test, proba, threshold: float) -> str:
    thresholds = np.linspace(0.05, 0.95, 91)
    prec = [precision_score(y_test, proba >= t, zero_division=0) for t in thresholds]
    rec = [recall_score(y_test, proba >= t) for t in thresholds]
    f1 = [f1_score(y_test, proba >= t) for t in thresholds]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(thresholds, prec, label="Precision", color=COLORS[0])
    ax.plot(thresholds, rec, label="Recall", color=COLORS[1])
    ax.plot(thresholds, f1, label="F1", color=COLORS[4], lw=2.5)
    ax.axvline(threshold, ls="--", color="black", lw=1)
    ax.text(threshold + 0.01, 0.95, f"chosen {threshold:.2f}", fontsize=9)
    ax.axvline(0.5, ls=":", color="grey", lw=1)
    ax.set_xlabel("Decision threshold (score above this = predict YES)")
    ax.set_ylabel("Score on test set")
    ax.set_ylim(0, 1)
    ax.set_title("Precision / recall trade-off by threshold")
    ax.legend(loc="center right")
    return _save(fig, "threshold_tradeoff.png")


def chart_importance(metrics: dict) -> str:
    imp = list(reversed(metrics["feature_importance"]))
    fig, ax = plt.subplots(figsize=(8, 5.5))
    vals = [f["importance"] for f in imp]
    ax.barh([f["feature"] for f in imp], vals, xerr=[f["std"] for f in imp],
            color=[COLORS[0] if v > 0 else "#94a3b8" for v in vals], capsize=3)
    ax.set_xlabel("Drop in ROC-AUC when the feature is shuffled")
    ax.set_title(f"Permutation feature importance: {metrics['best_model']}")
    return _save(fig, "feature_importance.png")


def cumulative_gains(y_test, proba) -> list[dict]:
    order = np.argsort(-proba)
    y_sorted = np.asarray(y_test)[order]
    total_pos = y_sorted.sum()
    out = []
    for pct in range(5, 101, 5):
        n = int(round(len(y_sorted) * pct / 100))
        captured = y_sorted[:n].sum() / total_pos * 100
        out.append({"pct_called": pct, "pct_captured": float(captured), "lift": float(captured / pct)})
    return out


def chart_gains(gains: list[dict], best: str) -> str:
    x = [0] + [g["pct_called"] for g in gains]
    y = [0] + [g["pct_captured"] for g in gains]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.plot(x, y, marker="o", ms=4, color=COLORS[0], lw=2, label=best)
    ax.plot([0, 100], [0, 100], "--", color="grey", label="Random calling")
    for g in gains:
        if g["pct_called"] in (10, 20, 30):
            ax.annotate(f"{g['pct_captured']:.0f}%", (g["pct_called"], g["pct_captured"]),
                        textcoords="offset points", xytext=(-10, 8), fontsize=9)
    ax.set_xlabel("% of clients called (highest score first)")
    ax.set_ylabel("% of all subscribers reached")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_title("Cumulative gains: how many subscribers each call budget reaches")
    ax.legend(loc="lower right")
    return _save(fig, "cumulative_gains.png")


# ------------------------------------------------------------------- html ----

def _img(name: str) -> str:
    data = base64.b64encode((REPORTS_DIR / name).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="{name}">'


def _float_format(column: str) -> str:
    if "time" in column.lower():
        return ".1f"
    if column in ("Importance", "Std"):
        return ".4f"
    return ".3f"


def _html_table(df: pd.DataFrame, highlight_col: str | None = None, highlight_val: str | None = None) -> str:
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    body = []
    for row in df.to_dict("records"):
        cls = ' class="hl"' if highlight_col and highlight_val and highlight_val in str(row[highlight_col]) else ""
        tds = "".join(
            f"<td>{v:{_float_format(c)}}</td>" if isinstance(v, float) else f"<td>{html.escape(str(v))}</td>"
            for c, v in row.items())
        body.append(f"<tr{cls}>{tds}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def write_html(metrics: dict, charts: dict, gains: list[dict]) -> None:
    t = metrics["best_model_tuned_test"]
    cm = t["confusion_matrix"]
    best = metrics["best_model"]
    comp = comparison_frame(metrics)
    params = pd.DataFrame([{"Model": m["name"],
                            "Best parameters": ", ".join(f"{k}={v}" for k, v in m["best_params"].items()) or "defaults"}
                           for m in metrics["models"]])
    imp = pd.DataFrame([{"Rank": i + 1, "Feature": f["feature"], "Importance": f["importance"], "Std": f["std"]}
                        for i, f in enumerate(metrics["feature_importance"])])
    gains_df = pd.DataFrame([{"Top % called": f"{g['pct_called']}%", "Subscribers reached": f"{g['pct_captured']:.1f}%",
                              "Lift": f"{g['lift']:.2f}x"} for g in gains if g["pct_called"] <= 50])
    g10 = next(g for g in gains if g["pct_called"] == 10)
    g20 = next(g for g in gains if g["pct_called"] == 20)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Bank Marketing – Training Report</title>
<style>
 body{{font-family:Segoe UI,system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#0f172a;background:#f8fafc}}
 h1{{margin-bottom:.2rem}} h2{{margin-top:2.2rem;border-bottom:2px solid #2563eb;padding-bottom:.3rem}}
 .muted{{color:#64748b}} .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.2rem 0}}
 .kpi{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:.9rem}}
 .kpi span{{color:#64748b;font-size:.85rem}} .kpi b{{display:block;font-size:1.5rem;margin-top:.2rem}}
 table{{border-collapse:collapse;width:100%;background:#fff;font-size:.9rem;margin:.8rem 0}}
 th,td{{border:1px solid #e2e8f0;padding:.45rem .6rem;text-align:left}} th{{background:#f1f5f9}}
 tr.hl td{{background:#eff6ff;font-weight:600}}
 img{{max-width:100%;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:.5rem;margin:.6rem 0}}
 .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
 .note{{background:#fff;border-left:4px solid #2563eb;padding:.7rem 1rem;margin:.8rem 0}}
</style></head><body>
<h1>Term Deposit Subscription – Model Training Report</h1>
<p class="muted">UCI Bank Marketing (bank-full.csv) · generated {datetime.now():%Y-%m-%d %H:%M} ·
train {metrics['train_size']:,} rows / test {metrics['test_size']:,} rows (stratified 80/20)</p>

<div class="kpis">
 <div class="kpi"><span>Selected model</span><b>{html.escape(best)}</b></div>
 <div class="kpi"><span>Test ROC-AUC</span><b>{t['roc_auc']:.3f}</b></div>
 <div class="kpi"><span>F1 @ threshold {t['threshold']:.2f}</span><b>{t['f1']:.3f}</b></div>
 <div class="kpi"><span>Recall / Precision</span><b>{t['recall']:.0%} / {t['precision']:.0%}</b></div>
</div>
<div class="note">Calling the top 10% of clients ranked by the model reaches <b>{g10['pct_captured']:.0f}%</b> of all
subscribers ({g10['lift']:.1f}× better than random); the top 20% reaches <b>{g20['pct_captured']:.0f}%</b>.</div>

<h2>1. Model comparison</h2>
<p>Six classifiers were tuned with 3-fold stratified cross-validation. The model with the highest
cross-validated ROC-AUC was selected (★). Test metrics below use the default 0.5 threshold.</p>
{_html_table(comp, "Model", "★")}
{_img(charts['comparison'])}
{_img(charts['cv_test'])}

<h2>2. Best hyper-parameters</h2>
{_html_table(params)}

<h2>3. ROC and precision-recall curves</h2>
<p>ROC-AUC measures how well a model ranks subscribers above non-subscribers. With only ~12% positives,
the precision-recall curve is the stricter view; the dashed line is what random guessing achieves.</p>
<div class="grid2">{_img(charts['roc'])}{_img(charts['pr'])}</div>

<h2>4. Decision threshold and confusion matrix ({html.escape(best)})</h2>
<p>The threshold was tuned to maximise F1 on out-of-fold <i>training</i> predictions (the test set was
not used), giving <b>{t['threshold']:.2f}</b>. On the test set this finds {cm['tp']:,} of {cm['tp'] + cm['fn']:,}
subscribers ({t['recall']:.0%}) while {t['precision']:.0%} of flagged clients actually subscribe.</p>
{_img(charts['confusion'])}
{_img(charts['threshold'])}

<h2>5. Feature importance</h2>
<p>Permutation importance: how much test ROC-AUC drops when a feature's values are shuffled.
Grey bars (≤ 0) are features the model barely relies on.</p>
<div class="grid2">{_img(charts['importance'])}<div>{_html_table(imp)}</div></div>

<h2>6. Business view: cumulative gains</h2>
<p>If the bank calls clients in order of model score, this shows the share of all subscribers reached for a given call budget.</p>
<div class="grid2">{_img(charts['gains'])}<div>{_html_table(gains_df)}</div></div>
</body></html>"""
    (REPORTS_DIR / "training_report.html").write_text(page, encoding="utf-8")


# ------------------------------------------------------------- entrypoint ----

def generate(metrics: dict, y_test, probas: dict, threshold: float) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    best = metrics["best_model"]
    best_proba = probas[best]
    gains = cumulative_gains(y_test, best_proba)

    print_summary(metrics, gains)

    charts = {
        "comparison": chart_model_comparison(metrics),
        "cv_test": chart_cv_vs_test(metrics),
        "roc": chart_roc(y_test, probas, best),
        "pr": chart_pr(y_test, probas, best),
        "confusion": chart_confusion(y_test, best_proba, threshold, best),
        "threshold": chart_threshold(y_test, best_proba, threshold),
        "importance": chart_importance(metrics),
        "gains": chart_gains(gains, best),
    }
    comparison_frame(metrics).to_csv(REPORTS_DIR / "model_comparison.csv", index=False)
    write_html(metrics, charts, gains)

    print(section("REPORT FILES"))
    print(f"  Open in a browser : {REPORTS_DIR / 'training_report.html'}")
    print(f"  Charts (PNG)      : {', '.join(charts.values())}")
    print(f"  Table (CSV)       : {REPORTS_DIR / 'model_comparison.csv'}")
