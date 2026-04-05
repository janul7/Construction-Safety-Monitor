"""Streamlit interface for the Construction Safety Monitor."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

from src.monitor import SafetyMonitor
from src.reports import (
    build_worker_dataframe,
    image_report_markdown,
    status_badge,
)
from src.schemas import FrameReport

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "webp"}
VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "m4v"}


@st.cache_resource
def load_monitor(model_path: str, rules_path: str) -> SafetyMonitor:
    """Load the model once and cache it across Streamlit reruns."""
    return SafetyMonitor(model_path=model_path, rules_path=rules_path)


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Construction Safety Monitor",
    page_icon="\U0001f3d7\ufe0f",
    layout="wide",
)

st.title("\U0001f3d7\ufe0f Construction Safety Monitor")
st.caption("Real-time PPE compliance analysis for construction sites")

# ── Config (defaults) ────────────────────────────────────────────────────────

model_path = "model/best.pt"
rules_path = "configs/rules.yaml"

# ── Upload ───────────────────────────────────────────────────────────────────

uploaded = st.file_uploader(
    "Upload an image or video",
    type=sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS),
)

if uploaded is None:
    st.info("Upload a construction site image or video to begin analysis.")
    st.stop()

suffix = Path(uploaded.name).suffix.lstrip(".").lower()
is_image = suffix in IMAGE_EXTENSIONS
is_video = suffix in VIDEO_EXTENSIONS

if not (is_image or is_video):
    st.error(f"Unsupported file type: .{suffix}")
    st.stop()

try:
    monitor = load_monitor(model_path, rules_path)
except Exception as e:
    st.error(f"Could not load model or rules: {e}")
    st.stop()

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ── Image analysis ───────────────────────────────────────────────────────────

if is_image:
    with tempfile.NamedTemporaryFile(suffix=f".{suffix}", delete=False) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    with st.spinner("Analysing image..."):
        frame = cv2.imread(tmp_path)
        if frame is None:
            st.error("Could not read the uploaded image.")
            st.stop()
        workers, scene_status, summary = monitor.analyze_frame(frame)
        annotated = monitor.annotate_frame(frame, workers, scene_status)

    st.subheader(f"Scene Status: {status_badge(scene_status)}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Workers", summary["total_workers"])
    c2.metric("Compliant", summary["compliant_workers"])
    c3.metric("Violations", summary["violating_workers"])
    c4.metric("Uncertain", summary["uncertain_workers"])

    left, right = st.columns(2)
    with left:
        st.image(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
            caption="Original",
            use_container_width=True,
        )
    with right:
        st.image(
            cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
            caption="Annotated",
            use_container_width=True,
        )

    if workers:
        st.subheader("Per-Worker Violation Table")
        st.dataframe(build_worker_dataframe(workers), use_container_width=True, hide_index=True)
    else:
        st.info("No workers detected in this scene.")

    st.subheader("Download Report")
    report = FrameReport(
        frame_index=0,
        scene_status=scene_status,
        worker_reports=workers,
        summary=summary,
    )
    json_str = json.dumps(report.to_dict(), indent=2)
    md_str = image_report_markdown(uploaded.name, scene_status, summary, workers, timestamp)

    d1, d2 = st.columns(2)
    d1.download_button(
        "JSON Report",
        json_str,
        file_name=f"report_{Path(uploaded.name).stem}.json",
        mime="application/json",
    )
    d2.download_button(
        "Markdown Report",
        md_str,
        file_name=f"report_{Path(uploaded.name).stem}.md",
        mime="text/markdown",
    )

# ── Video analysis ───────────────────────────────────────────────────────────

elif is_video:
    with tempfile.NamedTemporaryFile(suffix=f".{suffix}", delete=False) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        st.error("Could not open the uploaded video.")
        st.stop()

    total_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    duration_sec = total_frame_count / fps if fps > 0 else 0

    # Decide how many frames to sample based on video duration
    analysis_fps = monitor.rules.get("video", {}).get("analysis_fps", 2)
    num_samples = max(1, int(duration_sec * analysis_fps))
    # Cap at a reasonable maximum for very long videos
    num_samples = min(num_samples, 100)

    # Evenly space sample positions across the video
    sample_indices = [
        int(i * total_frame_count / num_samples)
        for i in range(num_samples)
    ]

    progress = st.progress(0, text="Analysing video...")
    annotated_frames = []
    all_frame_workers = []

    for count, frame_idx in enumerate(sample_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            continue

        workers, scene_status, summary = monitor.analyze_frame(frame)
        annotated = monitor.annotate_frame(frame, workers, scene_status)

        annotated_frames.append({
            "frame_idx": frame_idx,
            "time_sec": round(frame_idx / fps, 1),
            "annotated": annotated,
            "scene_status": scene_status,
            "summary": summary,
            "workers": workers,
        })

        for w in workers:
            all_frame_workers.append({
                "frame_idx": frame_idx,
                "time_sec": round(frame_idx / fps, 1),
                "worker_index": w.worker_index,
                "status": w.status,
                "helmet": w.helmet_detected,
                "vest": w.vest_detected,
                "violations": w.violations,
                "notes": w.notes,
            })

        progress.progress(
            min((count + 1) / num_samples, 1.0),
            text=f"Analysing frame {count + 1}/{num_samples}",
        )

    cap.release()
    progress.empty()

    # ── Aggregate summary ────────────────────────────────────────────────
    total_workers_seen = len(all_frame_workers)
    total_compliant = sum(1 for w in all_frame_workers if w["status"] == "COMPLIANT")
    total_violating = sum(1 for w in all_frame_workers if w["status"] == "VIOLATION")
    total_uncertain = sum(1 for w in all_frame_workers if w["status"] == "UNCERTAIN")

    unsafe_frames = [f for f in annotated_frames if f["scene_status"] == "UNSAFE"]
    review_frames = [f for f in annotated_frames if f["scene_status"] == "REVIEW"]
    safe_frames = [f for f in annotated_frames if f["scene_status"] == "SAFE"]

    if unsafe_frames:
        overall = "UNSAFE"
    elif review_frames:
        overall = "REVIEW"
    else:
        overall = "SAFE"

    # Count violation types across all frames
    violation_counts: dict = {}
    for w in all_frame_workers:
        for v in w["violations"]:
            violation_counts[v] = violation_counts.get(v, 0) + 1

    # ── Display ──────────────────────────────────────────────────────────
    st.subheader(f"Overall Video Status: {status_badge(overall)}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Frames Sampled", len(annotated_frames))
    c2.metric("Video Duration", f"{duration_sec:.1f}s")
    c3.metric("Unsafe Frames", len(unsafe_frames))
    c4.metric("Safe Frames", len(safe_frames))

    st.divider()
    st.subheader("Worker Summary Across Video")

    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Total Worker Detections", total_workers_seen)
    w2.metric("Compliant", total_compliant)
    w3.metric("Violations", total_violating)
    w4.metric("Uncertain", total_uncertain)

    if violation_counts:
        st.markdown("**Violation Breakdown:**")
        viol_rows = [{"Violation Type": k, "Count": v} for k, v in sorted(violation_counts.items(), key=lambda x: -x[1])]
        st.dataframe(pd.DataFrame(viol_rows), hide_index=True, use_container_width=True)

    # ── Sample frame gallery ─────────────────────────────────────────────
    st.divider()
    st.subheader("Sample Frames")

    # Show unsafe frames first, then review, then a few safe ones
    display_frames = unsafe_frames + review_frames
    if not display_frames:
        display_frames = safe_frames[:4]
    else:
        display_frames = display_frames[:8]

    cols_per_row = min(len(display_frames), 3)
    for row_start in range(0, len(display_frames), cols_per_row):
        row_frames = display_frames[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_frames))
        for col, fdata in zip(cols, row_frames):
            with col:
                st.image(
                    cv2.cvtColor(fdata["annotated"], cv2.COLOR_BGR2RGB),
                    caption=f"t={fdata['time_sec']}s — {fdata['scene_status']}",
                    use_container_width=True,
                )

    # ── Downloads ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Download Report")

    full_report = {
        "source": uploaded.name,
        "duration_sec": round(duration_sec, 1),
        "frames_sampled": len(annotated_frames),
        "overall_status": overall,
        "summary": {
            "total_worker_detections": total_workers_seen,
            "compliant": total_compliant,
            "violating": total_violating,
            "uncertain": total_uncertain,
            "violation_breakdown": violation_counts,
        },
        "unsafe_frames": len(unsafe_frames),
        "review_frames": len(review_frames),
        "safe_frames": len(safe_frames),
    }
    json_str = json.dumps(full_report, indent=2)

    md_lines = [
        f"# Video Analysis Report",
        f"",
        f"**Source:** {uploaded.name}",
        f"**Date:** {timestamp}",
        f"**Duration:** {duration_sec:.1f}s | **Frames sampled:** {len(annotated_frames)}",
        f"**Overall status:** {overall}",
        f"",
        f"## Worker Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total worker detections | {total_workers_seen} |",
        f"| Compliant | {total_compliant} |",
        f"| Violations | {total_violating} |",
        f"| Uncertain | {total_uncertain} |",
        f"",
    ]
    if violation_counts:
        md_lines.append("## Violation Breakdown\n")
        md_lines.append("| Type | Count |")
        md_lines.append("|------|-------|")
        for vtype, vcount in sorted(violation_counts.items(), key=lambda x: -x[1]):
            md_lines.append(f"| {vtype} | {vcount} |")
        md_lines.append("")

    md_lines.append(f"## Frame Status\n")
    md_lines.append(f"| Status | Frames |")
    md_lines.append(f"|--------|--------|")
    md_lines.append(f"| UNSAFE | {len(unsafe_frames)} |")
    md_lines.append(f"| REVIEW | {len(review_frames)} |")
    md_lines.append(f"| SAFE | {len(safe_frames)} |")

    md_str = "\n".join(md_lines)

    d1, d2 = st.columns(2)
    d1.download_button(
        "JSON Report",
        json_str,
        file_name=f"report_{Path(uploaded.name).stem}.json",
        mime="application/json",
    )
    d2.download_button(
        "Markdown Report",
        md_str,
        file_name=f"report_{Path(uploaded.name).stem}.md",
        mime="text/markdown",
    )
