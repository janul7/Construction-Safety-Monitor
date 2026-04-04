"""Pure-Python report helpers shared between app.py and tests."""

import pandas as pd

from src.schemas import WorkerAssessment


def build_worker_dataframe(workers) -> pd.DataFrame:
    rows = []
    for w in workers:
        label = f"ID:{w.track_id}" if w.track_id is not None else f"W{w.worker_index}"
        rows.append({
            "Worker": label,
            "Status": w.status,
            "Helmet": "Yes" if w.helmet_detected else "No",
            "Vest": "Yes" if w.vest_detected else "No",
            "Confidence": f"{w.person_confidence:.0%}",
            "Zone": w.zone_name,
            "Violations": ", ".join(w.violations) if w.violations else "None",
            "Notes": ", ".join(w.notes) if w.notes else "—",
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def status_badge(status: str) -> str:
    color = {"SAFE": "green", "UNSAFE": "red", "REVIEW": "orange"}.get(status, "gray")
    return f":{color}[**{status}**]"


def image_report_markdown(name, scene_status, summary, workers, timestamp):
    lines = [
        f"# Safety Report — {name}",
        f"**Generated:** {timestamp}  ",
        f"**Scene Status:** {scene_status}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total workers | {summary['total_workers']} |",
        f"| Compliant | {summary['compliant_workers']} |",
        f"| Violations | {summary['violating_workers']} |",
        f"| Uncertain | {summary['uncertain_workers']} |",
        "",
        "## Worker Details",
        "",
    ]
    for w in workers:
        wid = f"Worker {w.worker_index}" if w.track_id is None else f"Worker (Track {w.track_id})"
        lines.append(f"### {wid}")
        lines.append(f"- **Status:** {w.status}")
        lines.append(f"- **Helmet:** {'Detected' if w.helmet_detected else 'Not detected'}")
        if w.helmet_confidence is not None:
            lines.append(f"  - Confidence: {w.helmet_confidence:.2f}")
        lines.append(f"- **Vest:** {'Detected' if w.vest_detected else 'Not detected'}")
        if w.vest_confidence is not None:
            lines.append(f"  - Confidence: {w.vest_confidence:.2f}")
        lines.append(f"- **Person confidence:** {w.person_confidence:.2f}")
        lines.append(f"- **Zone:** {w.zone_name}")
        if w.violations:
            lines.append(f"- **Violations:** {', '.join(w.violations)}")
        if w.notes:
            lines.append(f"- **Notes:** {', '.join(w.notes)}")
        lines.append("")
    return "\n".join(lines)


def video_report_markdown(name, total_frames, reports, timestamp):
    unsafe_count = sum(1 for r in reports if r["scene_status"] == "UNSAFE")
    total_violations = sum(r["summary"]["violating_workers"] for r in reports)

    lines = [
        f"# Video Safety Report — {name}",
        f"**Generated:** {timestamp}  ",
        f"**Total frames:** {total_frames}  ",
        f"**Unsafe frames:** {unsafe_count} ({unsafe_count / max(total_frames, 1):.1%})",
        "",
        "## Aggregate Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total frames analysed | {total_frames} |",
        f"| Unsafe frames | {unsafe_count} |",
        f"| Total violation instances | {total_violations} |",
        "",
        "## Unsafe Frame Details",
        "",
    ]
    for r in reports:
        if r["scene_status"] != "UNSAFE":
            continue
        lines.append(f"### Frame {r['frame_index']}")
        for wr in r["worker_reports"]:
            if wr["status"] == "VIOLATION":
                tid = wr.get("track_id")
                label = f"ID:{tid}" if tid is not None else f"W{wr['worker_index']}"
                lines.append(f"- **{label}:** {', '.join(wr['violations'])}")
        lines.append("")
    if unsafe_count == 0:
        lines.append("No unsafe frames detected.")
    return "\n".join(lines)
