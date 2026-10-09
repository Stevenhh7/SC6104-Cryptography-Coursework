"""B: figures use measured CSV values; timeout values never enter medians."""

from pathlib import Path
from collections import defaultdict
from statistics import median
import csv
import math


def setup_plotting():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 120, "savefig.dpi": 180})
    return plt


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def benchmark_plots(csv_path, output):
    plt = setup_plotting()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = read_csv(csv_path)
    groups = defaultdict(list)
    for row in rows:
        groups[(int(row["unique_moduli"]), row["algorithm"])].append(row)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for algorithm, color in (("pairwise", "#c86c2d"), ("batch", "#137e87")):
        x, y, lower, upper = [], [], [], []
        for size in sorted({key[0] for key in groups}):
            values = [float(r["total_seconds"]) for r in groups[(size, algorithm)] if r["status"] == "ok"]
            if values:
                mid = median(values)
                x.append(size); y.append(mid); lower.append(mid - min(values)); upper.append(max(values) - mid)
        if x:
            ax.errorbar(x, y, yerr=[lower, upper], marker="o", linewidth=2, capsize=4, label=algorithm, color=color)
    timeouts = [(size, algo) for (size, algo), group in groups.items() if any(r["status"] == "timeout" for r in group)]
    if timeouts:
        ax.text(0.03, 0.96, "Timeouts excluded: " + ", ".join(f"{a}@{n}" for n, a in timeouts),
                transform=ax.transAxes, va="top", fontsize=9)
    ax.set(xlabel="Distinct RSA moduli (2048 bits)", ylabel="Complete scan time (seconds)",
           title="Measured scan time: median with observed min/max")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(output / "scan_times.png"); plt.close(fig)

    stages = ("preprocess", "conversion", "product_tree", "remainder_tree", "final_gcd", "fallback", "assemble")
    sizes = sorted(n for n, a in groups if a == "batch" and any(r["status"] == "ok" for r in groups[(n, a)]))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bottom = [0.] * len(sizes)
    colors = ("#a8b5be", "#af8eb6", "#3484a8", "#167c80", "#d5a53c", "#be6463", "#c4cacf")
    for stage, color in zip(stages, colors):
        values = [median(float(r[stage + "_seconds"]) for r in groups[(n, "batch")] if r["status"] == "ok") for n in sizes]
        ax.bar([str(n) for n in sizes], values, bottom=bottom, label=stage.replace("_", " "), color=color)
        bottom = [a + b for a, b in zip(bottom, values)]
    ax.set(xlabel="Distinct RSA moduli", ylabel="Seconds", title="Batch scan stages (component-wise medians)")
    ax.legend(ncol=3, fontsize=9); ax.grid(axis="y", alpha=.2)
    fig.tight_layout(); fig.savefig(output / "batch_stages.png"); plt.close(fig)
    presentation_plots(rows, output)
    return [str(output / name) for name in ("scan_times.png", "batch_stages.png", "scan_times_presentation.png")]


def presentation_plots(rows, output):
    """A larger-font scientific chart for projection, with explicit sample sizes."""
    plt = setup_plotting()
    groups = defaultdict(list)
    for row in rows:
        if row["status"] == "ok":
            groups[(int(row["unique_moduli"]), row["algorithm"])].append(float(row["total_seconds"]))
    fig, ax = plt.subplots(figsize=(8.4, 5))
    for algorithm, label, color in (("pairwise", "Pairwise GCD", "#c86c2d"), ("batch", "Batch GCD", "#087d83")):
        points = sorted((size, values) for (size, name), values in groups.items() if name == algorithm)
        centers = [median(values) for _, values in points]
        errors = [[center - min(values) for center, (_, values) in zip(centers, points)],
                  [max(values) - center for center, (_, values) in zip(centers, points)]]
        ax.errorbar([size for size, _ in points], centers, yerr=errors, marker="o", markersize=7,
                    linewidth=2.4, capsize=5, label=label, color=color)
    sizes = sorted({int(row["unique_moduli"]) for row in rows})
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(sizes, [f"{size:,}" for size in sizes])
    ax.set_xlabel("Distinct 2048-bit RSA moduli", fontsize=14, labelpad=12)
    ax.set_ylabel("Scan time in seconds (log scale)", fontsize=14, labelpad=8)
    ax.tick_params(axis="both", which="major", labelsize=13)
    ax.grid(alpha=.18, which="major")
    ax.legend(fontsize=13, loc="upper left", frameon=False)
    fig.tight_layout(pad=1.5)
    for suffix in ("png", "svg"):
        fig.savefig(Path(output) / f"scan_times_presentation.{suffix}")
    plt.close(fig)


def pool_plot(csv_path, output):
    plt = setup_plotting()
    groups = defaultdict(list)
    for row in read_csv(csv_path):
        groups[int(row["pool_size"])].append(float(row["vulnerable_fraction"]))
    sizes = sorted(groups)
    values = [median(groups[s]) for s in sizes]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.errorbar(sizes, values, yerr=[[values[i] - min(groups[s]) for i, s in enumerate(sizes)],
                                    [max(groups[s]) - values[i] for i, s in enumerate(sizes)]],
                marker="o", color="#137e87", capsize=4)
    ax.set(xlabel="Prime pool size", ylabel="Recoverable fraction", ylim=(0, 1.05),
           title="Controlled weak-prime pool: median and observed min/max")
    ax.set_xscale("log", base=2); ax.grid(alpha=.2)
    fig.tight_layout()
    path = Path(output) / "weak_pool.png"; path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path); plt.close(fig)
    return str(path)


def relation_plot(keys, output):
    """Small public-input graph; duplicates appear once, no ground truth used."""
    plt = setup_plotting()
    unique = {k.n: k for k in keys}
    if len(unique) > 300:
        raise ValueError("关系图限制为 300 个不同模数，以便清晰展示")
    numbers = list(unique)
    edges = []
    from math import gcd
    for i, n in enumerate(numbers):
        for j in range(i + 1, len(numbers)):
            g = gcd(n, numbers[j])
            if 1 < g < min(n, numbers[j]):
                edges.append((i, j))
    nodes = sorted({index for edge in edges for index in edge})
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if nodes:
        coords = {index: (math.cos(2 * math.pi * k / len(nodes)), math.sin(2 * math.pi * k / len(nodes))) for k, index in enumerate(nodes)}
        for a, b in edges:
            ax.plot([coords[a][0], coords[b][0]], [coords[a][1], coords[b][1]], color="#9aaab2", zorder=1)
        for index in nodes:
            x, y = coords[index]
            ax.scatter(x, y, s=650, color="#137e87", zorder=2)
            ax.text(x, y + .15, unique[numbers[index]].id, ha="center", fontsize=9)
    else:
        ax.text(.5, .5, "No shared factors found in this collection", ha="center", transform=ax.transAxes)
    ax.set_title(f"Shared-prime relationships: {len(nodes)} moduli, {len(edges)} edges")
    ax.set_aspect("equal"); ax.axis("off"); ax.margins(.3)
    fig.tight_layout()
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path); plt.close(fig)
    return str(path)
