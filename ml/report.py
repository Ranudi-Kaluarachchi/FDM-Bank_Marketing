"""Human-readable training outputs: console tables, PNG charts and an HTML report.

Everything is written to reports/ so results can be reviewed without the web app:
  reports/training_report.html                 single self-contained page (open in any browser)
  reports/*.png                                individual charts
  reports/confusion_matrices/*.png             one confusion-matrix chart per model
  reports/confusion_matrices_all_models.png    all models' confusion matrices side by side
  reports/model_comparison.csv                 comparison table for Excel / Sheets
"""
import base64
import html
import re
import sys
from datetime import datetime

import matplotlib

# "Agg" renders charts straight to image files without opening a window, so the
# report works on machines/servers with no display. It must be set before pyplot is imported.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score, f1_score, precision_recall_curve, precision_score,
    recall_score, roc_auc_score, roc_curve,
)

from ml.config import ROOT  # noqa: E402

# Output folders for the report files.
REPORTS_DIR = ROOT / "reports"
CM_DIR_NAME = "confusion_matrices"

# One colour per model / metric so charts stay visually consistent.
COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]

# Friendly display names for the metric keys stored in metrics.json.
METRIC_LABELS = {
    "roc_auc": "ROC-AUC", "pr_auc": "PR-AUC", "f1": "F1",
    "precision": "Precision", "recall": "Recall", "accuracy": "Accuracy",
}

# Global matplotlib styling: light grid, no top/right borders, readable font size.
plt.rcParams.update({
    "figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "font.size": 10,
})


# ---------------------------------------------------------------- helpers ----

def slugify(name: str) -> str:
    """Turn a model name into a safe file name, e.g. 'K-Nearest Neighbours' -> 'k_nearest_neighbours'."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def confusion_counts(y_true, proba, threshold: float) -> np.ndarray:
    """Return the 2x2 confusion matrix [[TN, FP], [FN, TP]] for a given decision threshold."""
    y = np.asarray(y_true)
    pred = (np.asarray(proba) >= threshold).astype(int)  # score above threshold -> predict "yes"
    return np.array([[((y == actual) & (pred == predicted)).sum() for predicted in (0, 1)]
                     for actual in (0, 1)])


def ranked_models(metrics: dict) -> list[dict]:
    """Models sorted best-first by cross-validated ROC-AUC (the selection metric)."""
    return sorted(metrics["models"], key=lambda r: r["cv_roc_auc"], reverse=True)


# ---------------------------------------------------------------- console ----

def format_table(headers: list[str], rows: list[list], align: str | None = None) -> str:
    """Render a plain-text table with box-drawing borders.

    `align` is one character per column: 'l' = left-aligned, 'r' = right-aligned.
    By default the first column is left-aligned and the rest right-aligned (numbers).
    """
    cells = [[str(c) for c in r] for r in rows]
    # Each column is as wide as its longest value (header included).
    widths = [max(len(str(h)), *(len(r[i]) for r in cells)) for i, h in enumerate(headers)]
    align = align or "l" + "r" * (len(headers) - 1)

    def line(left, mid, right):
        """Horizontal border line, e.g. ┌────┬────┐."""
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def fmt(row):
        """One table row with padded cells, e.g. │ a  │  1 │."""
        parts = [(c.ljust(w) if a == "l" else c.rjust(w)) for c, w, a in zip(row, widths, align)]
        return "│ " + " │ ".join(parts) + " │"

    out = [line("┌", "┬", "┐"), fmt([str(h) for h in headers]), line("├", "┼", "┤")]
    out += [fmt(r) for r in cells]
    out.append(line("└", "┴", "┘"))
    return "\n".join(out)


def section(title: str) -> str:
    """A bold banner used to separate the console report into sections."""
    return f"\n{'═' * 78}\n  {title}\n{'═' * 78}"


def comparison_frame(metrics: dict) -> pd.DataFrame:
    """Build the model comparison table (one row per model, ranked by CV ROC-AUC)."""
    rows = []
    for m in ranked_models(metrics):
        t = m["test"]  # test-set metrics at the default 0.5 threshold
        rows.append({
            "Rank": len(rows) + 1,
            "Model": m["name"] + (" ★" if m["name"] == metrics["best_model"] else ""),  # ★ = selected model
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


def confusion_frame(metrics: dict) -> pd.DataFrame:
    """Confusion-matrix counts for every model at the default 0.5 threshold."""
    rows = []
    for m in ranked_models(metrics):
        cm = m["test"]["confusion_matrix"]
        positives = cm["tp"] + cm["fn"]  # actual subscribers in the test set
        flagged = cm["tp"] + cm["fp"]    # clients the model said "yes" to
        rows.append({
            "Model": m["name"] + (" ★" if m["name"] == metrics["best_model"] else ""),
            "TN (correct no)": f"{cm['tn']:,}",
            "FP (wasted call)": f"{cm['fp']:,}",
            "FN (missed)": f"{cm['fn']:,}",
            "TP (correct yes)": f"{cm['tp']:,}",
            "Subscribers found": f"{cm['tp'] / positives:.1%}" if positives else "-",
            "Flagged that subscribed": f"{cm['tp'] / flagged:.1%}" if flagged else "-",
        })
    return pd.DataFrame(rows)


def print_summary(metrics: dict, gains: list[dict]) -> None:
    """Print every results table to the console."""
    # 1. Model comparison: floats shown with 3 decimals, except training time.
    df = comparison_frame(metrics)
    print(section("MODEL COMPARISON (test set, threshold 0.5, ranked by CV ROC-AUC)"))
    print(format_table(list(df.columns),
                       [[f"{v:.3f}" if isinstance(v, float) and c != "Train time (s)" else v
                         for c, v in row.items()] for row in df.to_dict("records")],
                       align="rl" + "r" * (len(df.columns) - 2)))

    # 2. Winning hyper-parameters found by the grid search for each model.
    print(section("BEST HYPER-PARAMETERS (3-fold stratified grid search)"))
    print(format_table(["Model", "Parameters"],
                       [[m["name"], ", ".join(f"{k}={v}" for k, v in m["best_params"].items()) or "defaults"]
                        for m in metrics["models"]], align="ll"))

    # 3. Confusion matrices for all models side by side.
    cmf = confusion_frame(metrics)
    print(section("CONFUSION MATRICES - ALL MODELS (test set, threshold 0.5)"))
    print(format_table(list(cmf.columns), cmf.values.tolist()))

    # 4. Selected model at its tuned threshold, with a plain-English meaning per metric.
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

    # 5. Feature importance with a text bar chart scaled to the strongest feature.
    print(section("FEATURE IMPORTANCE (permutation: drop in ROC-AUC when shuffled)"))
    top = metrics["feature_importance"]
    peak = max(f["importance"] for f in top) or 1
    print(format_table(["#", "Feature", "Importance", ""], [
        [i + 1, f["feature"], f"{f['importance']:.4f}", "█" * max(0, round(30 * f["importance"] / peak))]
        for i, f in enumerate(top)
    ], align="rlrl"))

    # 6. Cumulative gains: the business view of how useful the ranking is.
    print(section("CUMULATIVE GAINS (call clients in order of model score)"))
    print(format_table(["Top % of clients called", "Subscribers captured", "Lift vs random"],
                       [[f"{g['pct_called']}%", f"{g['pct_captured']:.1f}%", f"{g['lift']:.2f}x"]
                        for g in gains if g["pct_called"] in (5, 10, 20, 30, 40, 50)], align="rrr"))


# ----------------------------------------------------------------- charts ----

def _save(fig, name: str) -> str:
    """Save a figure under reports/ and return its relative file name."""
    path = REPORTS_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)  # free memory; many charts are generated in one run
    return name


def chart_model_comparison(metrics: dict) -> str:
    """Grouped bar chart of the main test metrics for every model."""
    models = ranked_models(metrics)
    keys = ["roc_auc", "pr_auc", "f1", "precision", "recall"]
    x = np.arange(len(models))
    width = 0.16  # width of one bar; 5 bars per model group
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for i, k in enumerate(keys):
        vals = [m["test"][k] for m in models]
        # Offset each metric's bars so the five bars sit side by side around the tick.
        bars = ax.bar(x + (i - 2) * width, vals, width, label=METRIC_LABELS[k], color=COLORS[i])
        if k == "roc_auc":
            ax.bar_label(bars, fmt="%.3f", fontsize=7, padding=2)  # print ROC-AUC values on top
    ax.set_xticks(x, [m["name"] + (" ★" if m["name"] == metrics["best_model"] else "") for m in models])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("Model comparison on the test set (threshold 0.5)")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False)
    return _save(fig, "model_comparison.png")


def chart_cv_vs_test(metrics: dict) -> str:
    """Compare cross-validation and test ROC-AUC; a big gap would indicate over-fitting."""
    models = sorted(metrics["models"], key=lambda r: r["cv_roc_auc"])
    y = np.arange(len(models))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(y - 0.2, [m["cv_roc_auc"] for m in models], 0.4, label="Cross-validation", color=COLORS[0])
    ax.barh(y + 0.2, [m["test"]["roc_auc"] for m in models], 0.4, label="Held-out test", color=COLORS[1])
    ax.set_yticks(y, [m["name"] for m in models])
    # Zoom the x-axis in on the range the scores actually occupy.
    lo = min(min(m["cv_roc_auc"], m["test"]["roc_auc"]) for m in models)
    ax.set_xlim(max(0.5, lo - 0.05), 1)
    ax.set_xlabel("ROC-AUC")
    ax.set_title("Cross-validation vs test ROC-AUC (similar values mean no over-fitting)")
    ax.legend(loc="lower right")
    return _save(fig, "cv_vs_test_auc.png")


def chart_roc(y_test, probas: dict, best: str) -> str:
    """ROC curve for every model; the selected model is drawn thicker."""
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for i, (name, p) in enumerate(probas.items()):
        fpr, tpr, _ = roc_curve(y_test, p)
        ax.plot(fpr, tpr, color=COLORS[i % len(COLORS)], lw=3 if name == best else 1.4,
                label=f"{name} (AUC {roc_auc_score(y_test, p):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1, label="Random guess (0.500)")  # diagonal = no skill
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate (recall)")
    ax.set_title("ROC curves")
    ax.legend(loc="lower right", fontsize=8)
    return _save(fig, "roc_curves.png")


def chart_pr(y_test, probas: dict, best: str) -> str:
    """Precision-recall curve for every model (more informative than ROC for rare positives)."""
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for i, (name, p) in enumerate(probas.items()):
        prec, rec, _ = precision_recall_curve(y_test, p)
        ax.plot(rec, prec, color=COLORS[i % len(COLORS)], lw=3 if name == best else 1.4,
                label=f"{name} (AP {average_precision_score(y_test, p):.3f})")
    # A random model's precision equals the share of positives in the data.
    base = float(np.mean(y_test))
    ax.axhline(base, ls="--", color="grey", lw=1, label=f"Random guess ({base:.3f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_ylim(0, 1)
    ax.set_title("Precision-recall curves")
    ax.legend(loc="upper right", fontsize=8)
    return _save(fig, "pr_curves.png")


def _draw_confusion(ax, cm: np.ndarray, title: str, fontsize: int = 9) -> None:
    """Draw one labelled confusion matrix heat-map onto a matplotlib axis."""
    ax.imshow(cm, cmap="Blues")
    labels = [["True negative", "False positive"], ["False negative", "True positive"]]
    for i in range(2):          # rows: actual class
        for j in range(2):      # columns: predicted class
            row_total = cm[i].sum()
            pct = cm[i, j] / row_total if row_total else 0
            # White text on dark cells, black text on light cells, for readability.
            ax.text(j, i, f"{cm[i, j]:,}\n{labels[i][j]}\n({pct:.0%} of row)", ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=fontsize)
    ax.set_xticks([0, 1], ["Predicted NO", "Predicted YES"])
    ax.set_yticks([0, 1], ["Actual NO", "Actual YES"])
    ax.grid(False)
    ax.set_title(title)


def _cm_summary(cm: np.ndarray) -> str:
    """One-line accuracy / precision / recall / F1 summary computed from a confusion matrix."""
    tn, fp, fn, tp = cm.ravel()
    acc = (tp + tn) / cm.sum()
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    return f"Accuracy {acc:.1%}  ·  Precision {prec:.1%}  ·  Recall {rec:.1%}  ·  F1 {f1:.3f}"


def chart_confusion(y_test, proba, threshold: float, best: str) -> str:
    """Selected model: confusion matrix at the default 0.5 threshold vs the tuned threshold."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, thr, title in [(axes[0], 0.5, "Default threshold 0.50"),
                           (axes[1], threshold, f"Tuned threshold {threshold:.2f}")]:
        _draw_confusion(ax, confusion_counts(y_test, proba, thr), title)
    fig.suptitle(f"Confusion matrices: {best} (test set)")
    return _save(fig, "confusion_matrix.png")


def chart_confusion_per_model(y_test, probas: dict, metrics: dict, threshold: float) -> list[str]:
    """Save one confusion-matrix PNG per model into reports/confusion_matrices/.

    Every model is shown at the default 0.5 threshold so they can be compared fairly.
    The selected model's file gets a second panel with its tuned threshold.
    Files are prefixed with the model's rank (01_ = best) so they sort in order.
    """
    files = []
    for rank, m in enumerate(ranked_models(metrics), start=1):
        name = m["name"]
        is_best = name == metrics["best_model"]
        panels = [(0.5, "Threshold 0.50")]
        if is_best:
            panels.append((threshold, f"Tuned threshold {threshold:.2f}"))

        fig, axes = plt.subplots(1, len(panels), figsize=(5.2 * len(panels), 4.8), squeeze=False)
        for ax, (thr, title) in zip(axes[0], panels):
            cm = confusion_counts(y_test, probas[name], thr)
            _draw_confusion(ax, cm, title)
            ax.set_xlabel(_cm_summary(cm), fontsize=8, labelpad=10)  # metrics under each matrix
        fig.suptitle(f"#{rank} {name}{' ★ (selected)' if is_best else ''}  -  test set, "
                     f"ROC-AUC {m['test']['roc_auc']:.3f}", fontsize=11)
        files.append(_save(fig, f"{CM_DIR_NAME}/{rank:02d}_{slugify(name)}.png"))
    return files


def chart_confusion_grid(y_test, probas: dict, metrics: dict) -> str:
    """All models' confusion matrices (threshold 0.5) in one 2x3 grid image."""
    models = ranked_models(metrics)
    cols = 3
    rows = int(np.ceil(len(models) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4.6 * rows), squeeze=False)
    for ax, m in zip(axes.flat, models):
        cm = confusion_counts(y_test, probas[m["name"]], 0.5)
        star = " ★" if m["name"] == metrics["best_model"] else ""
        _draw_confusion(ax, cm, f"{m['name']}{star}", fontsize=8)
        ax.set_xlabel(_cm_summary(cm).replace("  ·  ", "\n", 1), fontsize=8, labelpad=8)
    for ax in list(axes.flat)[len(models):]:
        ax.axis("off")  # hide unused grid cells if the model count isn't a multiple of 3
    fig.suptitle("Confusion matrices for all models (test set, threshold 0.5)", fontsize=13)
    return _save(fig, "confusion_matrices_all_models.png")


def chart_threshold(y_test, proba, threshold: float) -> str:
    """How precision, recall and F1 change as the decision threshold moves."""
    thresholds = np.linspace(0.05, 0.95, 91)
    prec = [precision_score(y_test, proba >= t, zero_division=0) for t in thresholds]
    rec = [recall_score(y_test, proba >= t) for t in thresholds]
    f1 = [f1_score(y_test, proba >= t) for t in thresholds]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(thresholds, prec, label="Precision", color=COLORS[0])
    ax.plot(thresholds, rec, label="Recall", color=COLORS[1])
    ax.plot(thresholds, f1, label="F1", color=COLORS[4], lw=2.5)
    ax.axvline(threshold, ls="--", color="black", lw=1)  # chosen (tuned) threshold
    ax.text(threshold + 0.01, 0.95, f"chosen {threshold:.2f}", fontsize=9)
    ax.axvline(0.5, ls=":", color="grey", lw=1)          # default threshold for reference
    ax.set_xlabel("Decision threshold (score above this = predict YES)")
    ax.set_ylabel("Score on test set")
    ax.set_ylim(0, 1)
    ax.set_title("Precision / recall trade-off by threshold")
    ax.legend(loc="center right")
    return _save(fig, "threshold_tradeoff.png")


def chart_importance(metrics: dict) -> str:
    """Horizontal bar chart of permutation importance with error bars (std over repeats)."""
    imp = list(reversed(metrics["feature_importance"]))  # reversed so the top feature is drawn at the top
    fig, ax = plt.subplots(figsize=(8, 5.5))
    vals = [f["importance"] for f in imp]
    ax.barh([f["feature"] for f in imp], vals, xerr=[f["std"] for f in imp],
            color=[COLORS[0] if v > 0 else "#94a3b8" for v in vals], capsize=3)  # grey = no real effect
    ax.set_xlabel("Drop in ROC-AUC when the feature is shuffled")
    ax.set_title(f"Permutation feature importance: {metrics['best_model']}")
    return _save(fig, "feature_importance.png")


def cumulative_gains(y_test, proba) -> list[dict]:
    """For each call budget (5%, 10%, ... of clients), the share of subscribers reached.

    Clients are sorted by model score, highest first; 'lift' is how many times better
    that is than calling the same number of clients at random.
    """
    order = np.argsort(-proba)               # indices from highest to lowest score
    y_sorted = np.asarray(y_test)[order]
    total_pos = y_sorted.sum()
    out = []
    for pct in range(5, 101, 5):
        n = int(round(len(y_sorted) * pct / 100))
        captured = y_sorted[:n].sum() / total_pos * 100
        out.append({"pct_called": pct, "pct_captured": float(captured), "lift": float(captured / pct)})
    return out


def chart_gains(gains: list[dict], best: str) -> str:
    """Cumulative gains curve versus random calling."""
    x = [0] + [g["pct_called"] for g in gains]
    y = [0] + [g["pct_captured"] for g in gains]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.plot(x, y, marker="o", ms=4, color=COLORS[0], lw=2, label=best)
    ax.plot([0, 100], [0, 100], "--", color="grey", label="Random calling")
    for g in gains:
        if g["pct_called"] in (10, 20, 30):  # annotate a few key budgets
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
    """Embed a PNG directly in the HTML (base64) so the report is a single portable file."""
    data = base64.b64encode((REPORTS_DIR / name).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="{name}">'


def _float_format(column: str) -> str:
    """Number format for a table column: times 1 dp, importances 4 dp, everything else 3 dp."""
    if "time" in column.lower():
        return ".1f"
    if column in ("Importance", "Std"):
        return ".4f"
    return ".3f"


def _html_table(df: pd.DataFrame, highlight_col: str | None = None, highlight_val: str | None = None) -> str:
    """Convert a DataFrame to an HTML table; rows whose `highlight_col` contains `highlight_val` are highlighted."""
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
    """Assemble all tables and charts into reports/training_report.html."""
    t = metrics["best_model_tuned_test"]
    cm = t["confusion_matrix"]
    best = metrics["best_model"]

    # Tables shown in the report.
    comp = comparison_frame(metrics)
    cm_table = confusion_frame(metrics)
    params = pd.DataFrame([{"Model": m["name"],
                            "Best parameters": ", ".join(f"{k}={v}" for k, v in m["best_params"].items()) or "defaults"}
                           for m in metrics["models"]])
    imp = pd.DataFrame([{"Rank": i + 1, "Feature": f["feature"], "Importance": f["importance"], "Std": f["std"]}
                        for i, f in enumerate(metrics["feature_importance"])])
    gains_df = pd.DataFrame([{"Top % called": f"{g['pct_called']}%", "Subscribers reached": f"{g['pct_captured']:.1f}%",
                              "Lift": f"{g['lift']:.2f}x"} for g in gains if g["pct_called"] <= 50])
    g10 = next(g for g in gains if g["pct_called"] == 10)
    g20 = next(g for g in gains if g["pct_called"] == 20)

    # Individual confusion-matrix images, two per row.
    per_model_imgs = "".join(_img(f) for f in charts["confusion_per_model"])

    # Note: CSS braces are doubled ({{ }}) because this is an f-string.
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

<h2>4. Confusion matrices for every model</h2>
<p>All models at the default 0.5 threshold on the same test set. <b>FP</b> = a call to a client who
does not subscribe (wasted effort); <b>FN</b> = a subscriber the model missed (lost sale).</p>
{_html_table(cm_table, "Model", "★")}
{_img(charts['confusion_grid'])}
<details><summary>Show each model's confusion matrix individually</summary>
<div class="grid2">{per_model_imgs}</div></details>

<h2>5. Decision threshold for the selected model ({html.escape(best)})</h2>
<p>The threshold was tuned to maximise F1 on out-of-fold <i>training</i> predictions (the test set was
not used), giving <b>{t['threshold']:.2f}</b>. On the test set this finds {cm['tp']:,} of {cm['tp'] + cm['fn']:,}
subscribers ({t['recall']:.0%}) while {t['precision']:.0%} of flagged clients actually subscribe.</p>
{_img(charts['confusion'])}
{_img(charts['threshold'])}

<h2>6. Feature importance</h2>
<p>Permutation importance: how much test ROC-AUC drops when a feature's values are shuffled.
Grey bars (≤ 0) are features the model barely relies on.</p>
<div class="grid2">{_img(charts['importance'])}<div>{_html_table(imp)}</div></div>

<h2>7. Business view: cumulative gains</h2>
<p>If the bank calls clients in order of model score, this shows the share of all subscribers reached for a given call budget.</p>
<div class="grid2">{_img(charts['gains'])}<div>{_html_table(gains_df)}</div></div>
</body></html>"""
    (REPORTS_DIR / "training_report.html").write_text(page, encoding="utf-8")


# ------------------------------------------------------------- entrypoint ----

def generate(metrics: dict, y_test, probas: dict, threshold: float) -> None:
    """Produce the full report.

    metrics   : the dict saved to artifacts/metrics.json by train.py
    y_test    : true labels of the held-out test set
    probas    : {model name: predicted subscription scores on the test set}
    threshold : tuned decision threshold of the selected model
    """
    # Windows consoles default to a legacy code page that cannot print the
    # box-drawing characters used in the tables; switch stdout to UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    best = metrics["best_model"]
    best_proba = probas[best]
    gains = cumulative_gains(y_test, best_proba)

    print_summary(metrics, gains)

    # Generate every chart; values are file names relative to reports/.
    charts = {
        "comparison": chart_model_comparison(metrics),
        "cv_test": chart_cv_vs_test(metrics),
        "roc": chart_roc(y_test, probas, best),
        "pr": chart_pr(y_test, probas, best),
        "confusion": chart_confusion(y_test, best_proba, threshold, best),
        "confusion_grid": chart_confusion_grid(y_test, probas, metrics),
        "confusion_per_model": chart_confusion_per_model(y_test, probas, metrics, threshold),
        "threshold": chart_threshold(y_test, best_proba, threshold),
        "importance": chart_importance(metrics),
        "gains": chart_gains(gains, best),
    }
    comparison_frame(metrics).to_csv(REPORTS_DIR / "model_comparison.csv", index=False)
    write_html(metrics, charts, gains)

    # Tell the user where everything was written.
    single_charts = [v for k, v in charts.items() if k != "confusion_per_model"]
    print(section("REPORT FILES"))
    print(f"  Open in a browser : {REPORTS_DIR / 'training_report.html'}")
    print(f"  Charts (PNG)      : {', '.join(single_charts)}")
    print(f"  Per-model confusion matrices ({REPORTS_DIR / CM_DIR_NAME}):")
    for f in charts["confusion_per_model"]:
        print(f"      - {f.split('/', 1)[1]}")
    print(f"  Table (CSV)       : {REPORTS_DIR / 'model_comparison.csv'}")
