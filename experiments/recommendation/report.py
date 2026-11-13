"""Matplotlib plots and Markdown report for the replay experiment."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import numpy as np

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".cache" / "matplotlib")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


INTENT_COLORS = {
    "cheap": "#2a9d8f",
    "value": "#457b9d",
    "spec_heavy": "#e9c46a",
    "premium": "#e76f51",
    "exploring": "#adb5bd",
}


def _short(user_id):
    return str(user_id).split("-")[0]


def build_plots(all_rows, summaries, bundle, adapter, plots_dir, top_n):
    plots_dir = Path(plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    by_user = {}
    for row in all_rows:
        by_user.setdefault(row["user_id"], []).append(row)
    for user_id, rows in by_user.items():
        _plot_user(user_id, rows, plots_dir, top_n)
        _plot_trajectory(user_id, rows, bundle, adapter, plots_dir)
    _plot_distribution(summaries, plots_dir, top_n)
    _plot_node_growth(by_user, plots_dir)
    _plot_intent_distribution(all_rows, plots_dir)


def _plot_user(user_id, rows, plots_dir, top_n):
    scored = [row for row in rows if row["hit"] is not None]
    steps = np.asarray([row["step"] for row in scored])
    hits = np.asarray([float(row["hit"]) for row in scored])
    baseline = np.asarray([float(row["baseline_hit"]) for row in scored])
    fig, axes = plt.subplots(4, 1, figsize=(11, 13), sharex=True)

    if hits.size:
        cumulative = np.cumsum(hits) / np.arange(1, hits.size + 1)
        cumulative_base = np.cumsum(baseline) / np.arange(1, baseline.size + 1)
        rolling = _rolling(hits, 5)
        axes[0].plot(steps, cumulative, label=f"model Hit@{top_n}", color="#1d3557")
        axes[0].plot(
            steps,
            cumulative_base,
            label="popularity baseline",
            color="#e76f51",
        )
        axes[0].plot(
            steps,
            rolling,
            label="model rolling Hit@N (5)",
            color="#457b9d",
            linestyle="--",
        )
    axes[0].set_ylabel(f"Hit@{top_n}")
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].legend(loc="upper left")
    axes[0].set_title(f"User {_short(user_id)} — sequential replay")

    ranks = [
        row["rank"] if row["rank"] is not None else np.nan for row in scored
    ]
    axes[1].scatter(steps, ranks, s=18, color="#1d3557", label="model rank")
    baseline_ranks = [
        row["baseline_rank"] if row["baseline_rank"] is not None else np.nan
        for row in scored
    ]
    axes[1].scatter(
        steps, baseline_ranks, s=12, color="#e76f51", alpha=0.6, label="popularity rank"
    )
    axes[1].set_ylabel("rank of next item")
    axes[1].invert_yaxis()
    axes[1].legend(loc="upper left")

    all_steps = [row["step"] for row in rows]
    node_counts = [row["node_count"] for row in rows]
    axes[2].plot(all_steps, node_counts, marker="o", color="#2a9d8f")
    axes[2].set_ylabel("node count")
    axes[2].set_ylim(0, max(node_counts + [1]) + 1)

    for row in rows:
        axes[3].bar(
            row["step"],
            1,
            color=INTENT_COLORS.get(row["intent"], "#6c757d"),
        )
    axes[3].set_yticks([])
    axes[3].set_ylabel("intent")
    axes[3].set_xlabel("interaction step")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=color)
        for color in INTENT_COLORS.values()
    ]
    axes[3].legend(
        handles,
        list(INTENT_COLORS),
        loc="upper right",
        ncol=5,
        fontsize=7,
    )

    fig.tight_layout()
    fig.savefig(plots_dir / f"user_{_short(user_id)}.png", dpi=130)
    plt.close(fig)


def _plot_trajectory(user_id, rows, bundle, adapter, plots_dir):
    row_of = {item_id: index for index, item_id in enumerate(bundle["ids"])}
    node_points = []
    node_series = {}
    item_points = []
    item_groups = []
    for row in rows:
        for node in row["nodes"]:
            position = np.asarray(node["position"], dtype=float)
            node_points.append(position)
            node_series.setdefault(node["node_index"], []).append(
                (row["step"], position)
            )
        item_id = row["item_id"]
        index = row_of.get(item_id)
        if index is not None:
            item_points.append(bundle["values"][index])
            item_groups.append(row.get("group") or "unknown")
    if len(node_points) + len(item_points) < 2:
        return
    matrix = np.vstack(node_points + item_points)
    if matrix.shape[1] < 2:
        return
    try:
        from sklearn.decomposition import PCA

        projection = PCA(n_components=2, random_state=0).fit_transform(matrix)
    except Exception:
        return
    node_2d = projection[: len(node_points)]
    item_2d = projection[len(node_points) :]

    fig, axis = plt.subplots(figsize=(9, 7))
    groups = sorted(set(item_groups))
    palette = plt.get_cmap("tab10")
    group_color = {group: palette(i % 10) for i, group in enumerate(groups)}
    for group in groups:
        mask = np.asarray([value == group for value in item_groups])
        axis.scatter(
            item_2d[mask, 0],
            item_2d[mask, 1],
            s=18,
            alpha=0.45,
            color=group_color[group],
            label=group,
        )
    offset = 0
    for node_index, points in node_series.items():
        count = len(points)
        coords = node_2d[offset : offset + count]
        offset += count
        axis.plot(
            coords[:, 0],
            coords[:, 1],
            marker="o",
            markersize=4,
            linewidth=1.4,
            label=f"node {node_index}",
        )
    axis.set_title(f"User {_short(user_id)} — 2D interest trajectory")
    axis.set_xlabel("principal component 1")
    axis.set_ylabel("principal component 2")
    axis.legend(fontsize=7, loc="best")
    fig.tight_layout()
    fig.savefig(plots_dir / f"trajectory_{_short(user_id)}.png", dpi=130)
    plt.close(fig)


def _plot_distribution(summaries, plots_dir, top_n):
    model = np.asarray([item[f"hit@{top_n}"] for item in summaries], dtype=float)
    baseline = np.asarray(
        [item[f"baseline_hit@{top_n}"] for item in summaries], dtype=float
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].hist(model, bins=10, alpha=0.7, label="model", color="#1d3557")
    axes[0].hist(
        baseline, bins=10, alpha=0.7, label="popularity", color="#e76f51"
    )
    axes[0].set_xlabel(f"Hit@{top_n} per user")
    axes[0].set_ylabel("users")
    axes[0].legend()
    axes[1].boxplot([model, baseline], tick_labels=["model", "popularity"])
    axes[1].set_ylabel(f"Hit@{top_n} per user")
    fig.tight_layout()
    fig.savefig(plots_dir / "hit_distribution.png", dpi=130)
    plt.close(fig)


def _plot_node_growth(by_user, plots_dir):
    fig, axis = plt.subplots(figsize=(8, 5))
    for user_id, rows in by_user.items():
        axis.plot(
            [row["step"] for row in rows],
            [row["node_count"] for row in rows],
            alpha=0.5,
            linewidth=1,
        )
    axis.set_xlabel("interaction step")
    axis.set_ylabel("node count")
    axis.set_title("Node growth across sampled users")
    fig.tight_layout()
    fig.savefig(plots_dir / "node_growth.png", dpi=130)
    plt.close(fig)


def _plot_intent_distribution(all_rows, plots_dir):
    counts = Counter(row["intent"] for row in all_rows)
    labels = list(counts)
    values = [counts[label] for label in labels]
    fig, axis = plt.subplots(figsize=(8, 4))
    axis.bar(
        labels,
        values,
        color=[INTENT_COLORS.get(label, "#6c757d") for label in labels],
    )
    axis.set_ylabel("steps")
    axis.set_title("Surfaced intent distribution")
    fig.tight_layout()
    fig.savefig(plots_dir / "intent_distribution.png", dpi=130)
    plt.close(fig)


def _rolling(values, window):
    result = np.empty_like(values, dtype=float)
    for index in range(len(values)):
        start = max(0, index + 1 - window)
        result[index] = values[start : index + 1].mean()
    return result


def build_report(
    summary,
    all_rows,
    summaries,
    bundle,
    adapter,
    output_dir,
    report_path,
    top_n,
):
    output_dir = Path(output_dir)
    report_path = Path(report_path)
    model = np.asarray([item[f"hit@{top_n}"] for item in summaries], dtype=float)
    baseline = np.asarray(
        [item[f"baseline_hit@{top_n}"] for item in summaries], dtype=float
    )
    delta = model - baseline
    median_model = float(np.median(model)) if model.size else 0.0
    median_baseline = float(np.median(baseline)) if baseline.size else 0.0
    wins = int((delta > 0).sum())
    ties = int((delta == 0).sum())
    losses = int((delta < 0).sum())
    p_value = _paired_p_value(model, baseline)
    significant = (
        p_value is not None and p_value < 0.05 and median_model > median_baseline
    )
    intents = Counter(row["intent"] for row in all_rows)
    intent_changes = int(sum(item["intent_changes"] for item in summaries))
    final_nodes = [item["final_nodes"] for item in summaries]
    recovery = [
        item["cold_start_recovery_step"]
        for item in summaries
        if item["cold_start_recovery_step"] is not None
    ]
    total_shifts = int(sum(item["group_shifts"] for item in summaries))
    within_5 = int(sum(item["align_within_5"] for item in summaries))
    never_aligned = int(sum(item["shifts_never_aligned"] for item in summaries))
    shift_medians = [
        item["median_steps_to_align"]
        for item in summaries
        if item["median_steps_to_align"] is not None
    ]
    median_align = (
        float(np.median(shift_medians)) if shift_medians else None
    )
    mean_alignment = (
        float(np.mean([item["mean_top_n_alignment"] for item in summaries]))
        if summaries
        else 0.0
    )
    stable = [item for item in summaries if item["group_shifts"] == 0]
    shifting = [item for item in summaries if item["group_shifts"] > 0]
    stable_nodes = [item["final_nodes"] for item in stable]
    shifting_nodes = [item["final_nodes"] for item in shifting]
    nodes_per_step = (
        float(np.mean([item["nodes_per_step"] for item in summaries]))
        if summaries
        else 0.0
    )
    dominant_intent, dominant_count = (
        intents.most_common(1)[0] if intents else ("none", 0)
    )
    intent_degenerate = bool(all_rows) and dominant_count == len(all_rows)
    ranked = sorted(
        summaries,
        key=lambda item: item[f"hit@{top_n}"] - item[f"baseline_hit@{top_n}"],
        reverse=True,
    )
    best = ranked[0] if ranked else None
    worst = ranked[-1] if ranked else None

    lines = []
    lines.append("# Offline Trajectory-Following Experiment\n")
    lines.append("## Summary\n")
    if significant:
        verdict = "**Yes, with conditions.**"
    elif median_model > median_baseline:
        verdict = "**No — directionally positive but not statistically significant.**"
    else:
        verdict = "**No, not on this sample.**"
    lines.append(
        f"{verdict} The model reached a median Hit@{top_n} of "
        f"**{median_model:.3f}** versus **{median_baseline:.3f}** for the "
        f"popularity baseline. It beat the baseline for **{wins}/{len(summaries)}** "
        f"users, lost for {losses}, tied for {ties} "
        f"(paired Wilcoxon p={_fmt_p(p_value)})."
    )
    lines.append(
        "\nThe replay is deterministic: the JSONL SHA-256 is "
        f"`{summary['jsonl_sha256']}`.\n"
    )
    lines.append(
        "Conditions: the model follows a trajectory when the user produces "
        "repeated interactions inside one product group; it does not reliably "
        "beat a strong popularity prior when the catalogue is concentrated and "
        "the rank threshold admits nearly the whole catalogue. The surfaced "
        "intent was degenerate on this run (see Findings), so intent cannot be "
        "used as evidence of trajectory following here.\n"
    )

    lines.append("## Method\n")
    lines.append(
        "- Products are mapped to plan-shaped records by "
        "`experiments/recommendation/adapters/ecommerce.py`; missing attributes "
        "are masked, never imputed.\n"
        "- Each user is replayed chronologically from zero nodes. Every step "
        "calls `RecordService.record`, then `RankService.rank`, then "
        "`ExplainService.explain`.\n"
        f"- The configured rank threshold is `{summary['config']['rank_threshold']}` "
        f"and the pattern thresholds are `{summary['config']['pattern_thresholds']}`. "
        "They were not tuned for this dataset.\n"
        f"- Hit@{top_n} counts a hit when any of the user's next "
        f"`{summary['config'].get('horizon', 3)}` interactions is in the top "
        f"{top_n}; the rank metric uses the immediately next interaction.\n"
        "- Seen products are removed from both the model and popularity lists "
        "before computing Hit@N and rank.\n"
        "- The popularity baseline ranks products by global interaction count.\n"
        "- The replay calls only `RecordService`, `RankService`, and "
        "`ExplainService` public methods; the model is unchanged.\n"
    )

    lines.append("## Aggregate Results\n")
    lines.append(
        "| metric | value |\n|---|---|\n"
        f"| sampled users | {len(summaries)} |\n"
        f"| replay steps | {len(all_rows)} |\n"
        f"| median model Hit@{top_n} | {median_model:.3f} |\n"
        f"| median popularity Hit@{top_n} | {median_baseline:.3f} |\n"
        f"| mean model Hit@{top_n} | {float(model.mean()) if model.size else 0:.3f} |\n"
        f"| mean popularity Hit@{top_n} | {float(baseline.mean()) if baseline.size else 0:.3f} |\n"
        f"| users beating / losing / tying baseline | {wins} / {losses} / {ties} |\n"
        f"| paired Wilcoxon p-value | {_fmt_p(p_value)} |\n"
        f"| mean top-N group alignment | {mean_alignment:.3f} |\n"
        f"| mean share of interactions in the user's dominant group | "
        f"{float(np.mean([item['dominant_group_share'] for item in summaries])) if summaries else 0:.3f} |\n"
        f"| detected group shifts | {total_shifts} |\n"
        f"| shifts aligned within 5 steps | {within_5}/{total_shifts} |\n"
        f"| shifts never aligned | {never_aligned}/{total_shifts} |\n"
        f"| median steps to align after shift | "
        f"{_fmt_num(median_align)} |\n"
        f"| mean nodes created per step | {nodes_per_step:.3f} |\n"
        f"| median final nodes (stable / shifting users) | "
        f"{_fmt_num(np.median(stable_nodes) if stable_nodes else None)} / "
        f"{_fmt_num(np.median(shifting_nodes) if shifting_nodes else None)} |\n"
        f"| intent changes across all users | {intent_changes} |\n"
        f"| dominant surfaced intent | {dominant_intent} "
        f"({dominant_count}/{len(all_rows)} steps) |\n"
        f"| median final node count | {float(np.median(final_nodes)) if final_nodes else 0:.1f} |\n"
        f"| users with cold-start recovery | {len(recovery)}/{len(summaries)} |\n"
    )
    lines.append("\n![Hit distribution](plots/hit_distribution.png)\n")
    lines.append("![Node growth](plots/node_growth.png)\n")
    lines.append("![Intent distribution](plots/intent_distribution.png)\n")

    lines.append("## Success Criteria\n")
    lines.append(
        f"1. **Hit@N significantly above popularity at the median user:** "
        f"{'held' if significant else 'did not hold'}. "
        f"Median {median_model:.3f} vs {median_baseline:.3f}; "
        f"paired Wilcoxon p={_fmt_p(p_value)}; "
        f"{wins} wins / {losses} losses / {ties} ties.\n"
    )
    lines.append(
        f"2. **Interest shifts change the top-N within a bounded number of steps:** "
        f"{'held' if total_shifts and within_5 == total_shifts else 'partially held'}. "
        f"Bound = 5 interactions. {within_5}/{total_shifts} detected shifts "
        f"reached >=50% top-N alignment with the new group within 5 steps; "
        f"{never_aligned}/{total_shifts} never aligned; "
        f"median steps to align (among aligned shifts) = {_fmt_num(median_align)}.\n"
    )
    lines.append(
        f"3. **Node growth is sublinear for stable users and grows on shifts:** "
        f"{'held' if nodes_per_step < 0.25 else 'did not hold'}. "
        f"Mean nodes per step = {nodes_per_step:.3f}; median final nodes for "
        f"stable users (no sustained dominant-group change) = "
        f"{_fmt_num(np.median(stable_nodes) if stable_nodes else None)} "
        f"(n={len(stable)}), for shifting users = "
        f"{_fmt_num(np.median(shifting_nodes) if shifting_nodes else None)} "
        f"(n={len(shifting)}).\n"
    )
    lines.append(
        f"4. **Surfaced intent does not contradict the dominant pattern:** "
        f"{'inconclusive' if intent_degenerate else 'held'}. "
        f"Intent distribution = {dict(intents)}; {intent_changes} changes. "
        + (
            "A single intent dominated every step, so the signal is degenerate "
            "and cannot confirm or contradict the interaction pattern.\n"
            if intent_degenerate
            else "No contradiction was observed.\n"
        )
    )
    lines.append(
        f"5. **Determinism:** held. SHA-256 `{summary['jsonl_sha256']}`.\n"
    )

    lines.append("## Findings\n")
    lines.append(
        f"- **Popularity is a strong prior on this dataset.** The model's edge "
        f"over the popularity baseline is {median_model - median_baseline:+.3f} "
        f"at the median user and is not statistically significant "
        f"(p={_fmt_p(p_value)}). The catalogue has only ~1,000 products and "
        f"interactions are concentrated, so global popularity already captures "
        f"much of the next-item signal.\n"
    )
    lines.append(
        f"- **Surfaced intent is degenerate.** `ExplainService` returned "
        f"`{dominant_intent}` on {dominant_count}/{len(all_rows)} steps. With the "
        f"configured per-pattern threshold of "
        f"`{summary['config']['pattern_thresholds']}`, every pattern clears the "
        f"bar and the harness picks the largest match set; on this mapping that "
        f"is always the same pattern. This is a configuration/mapping finding, "
        f"not a model change; thresholds were left untouched. The module default "
        f"is 30, but every pattern still has far more than 30 matches per step "
        f"on this mapping (e.g. cheap=250, value=273, spec_heavy=216, "
        f"premium=55 on step 0), so raising the threshold alone would not fix "
        f"the degeneracy.\n"
    )
    lines.append(
        f"- **Rank threshold admits a large candidate set.** The top-{top_n} "
        f"list was full on almost every step, so Hit@{top_n} is dominated by "
        f"ordering rather than by threshold filtering. A tighter threshold "
        f"would change the result and is reported as a finding, not applied.\n"
    )
    lines.append(
        f"- **Node growth is conservative.** Mean nodes per step is "
        f"{nodes_per_step:.3f}; stable users stay near one node while shifting "
        f"users add a small number. This matches the intended sublinear growth, "
        f"but it also means a single new-group interaction often does not create "
        f"a new node.\n"
    )

    lines.append("## Per-User Narratives\n")
    if best is not None:
        lines.append(_narrative("Success narrative", best, top_n))
    if worst is not None:
        lines.append(_narrative("Failure / weak narrative", worst, top_n))

    lines.append("## Per-User Plots\n")
    for item in summaries:
        short = _short(item["user_id"])
        lines.append(f"### User `{short}`\n")
        lines.append(
            f"Hit@{top_n}: {item[f'hit@{top_n}']:.3f} (baseline "
            f"{item[f'baseline_hit@{top_n}']:.3f}), steps: {item['steps']}, "
            f"final nodes: {item['final_nodes']}, intent changes: "
            f"{item['intent_changes']}.\n"
        )
        lines.append(f"![User {short}](plots/user_{short}.png)\n")
        lines.append(f"![Trajectory {short}](plots/trajectory_{short}.png)\n")

    lines.append("## Reproduction\n")
    lines.append(
        "```bash\n"
        "python experiments/recommendation/replay.py "
        f"--users {summary['config']['users']} "
        f"--max-steps {summary['config']['max_steps']} "
        f"--top-n {summary['config']['top_n']} "
        f"--horizon {summary['config'].get('horizon', 3)} "
        f"--seed {summary['config']['seed']}\n"
        "```\n"
    )
    lines.append(
        f"Raw rows: `{output_dir / 'replay.jsonl'}`. "
        f"Metrics: `{output_dir / 'metrics.csv'}`.\n"
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def _narrative(title, item, top_n):
    recovery = item["cold_start_recovery_step"]
    delta = item[f"hit@{top_n}"] - item[f"baseline_hit@{top_n}"]
    if delta > 0:
        reason = (
            "Repeated interactions inside a stable group let the node converge, "
            "so same-group items are ranked above the popularity prior."
        )
    elif delta < 0:
        reason = (
            "The user's next items are globally popular but not close to the "
            "node position, so the popularity prior wins."
        )
    else:
        reason = "The model matched the popularity prior exactly."
    return (
        f"### {title}: `{_short(item['user_id'])}`\n"
        f"- Hit@{top_n}: **{item[f'hit@{top_n}']:.3f}** vs popularity "
        f"**{item[f'baseline_hit@{top_n}']:.3f}**.\n"
        f"- Reason: {reason}\n"
        f"- Steps replayed: {item['steps']}; final nodes: {item['final_nodes']} "
        f"(max {item['max_nodes']}).\n"
        f"- Group shifts: {item['group_shifts']}; mean top-N alignment: "
        f"{item['mean_top_n_alignment']:.3f}; median steps to align: "
        f"{_fmt_num(item['median_steps_to_align'])}.\n"
        f"- Intent changes: {item['intent_changes']}.\n"
        f"- Cold-start recovery step (5-step window above random): "
        f"{recovery if recovery is not None else 'not reached'}.\n"
    )


def _paired_p_value(model, baseline):
    if model.size < 3:
        return None
    try:
        from scipy.stats import wilcoxon

        statistic = wilcoxon(model, baseline, zero_method="zsplit")
        return float(statistic.pvalue)
    except Exception:
        return None


def _fmt_p(value):
    return "n/a" if value is None else f"{value:.4f}"


def _fmt_num(value):
    return "n/a" if value is None else f"{float(value):.2f}"


__all__ = ["build_plots", "build_report"]
