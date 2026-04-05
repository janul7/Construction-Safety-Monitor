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
    video_report_markdown,
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
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Adaptive frame sampling: only run inference every N frames
    analysis_fps = monitor.rules.get("video", {}).get("analysis_fps", 2)
    frame_skip = max(1, round(fps / analysis_fps))
    frames_to_analyze = max(1, total_frame_count // frame_skip) if total_frame_count > 0 else 0

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_tmp:
        out_video_path = out_tmp.name

    writer = cv2.VideoWriter(
        out_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h),
    )
    monitor.reset_tracking()

    all_reports: list = []
    progress = st.progress(0, text="Processing video...")
    idx = 0
    analyzed_count = 0
    last_workers: list = []
    last_scene_status = "SAFE"
    last_summary: dict = {"total_workers": 0, "compliant_workers": 0, "violating_workers": 0, "uncertain_workers": 0}

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if idx % frame_skip == 0:
            workers, scene_status, summary = monitor.analyze_frame(
                frame, use_tracking=monitor.use_tracking,
            )
            last_workers, last_scene_status, last_summary = workers, scene_status, summary
            analyzed_count += 1

            fr = FrameReport(
                frame_index=idx,
                scene_status=scene_status,
                worker_reports=workers,
                summary=summary,
            )
            all_reports.append(fr.to_dict())
        else:
            workers, scene_status, summary = last_workers, last_scene_status, last_summary

        annotated = monitor.annotate_frame(frame, workers, scene_status)
        writer.write(annotated)

        idx += 1
        if total_frame_count > 0:
            progress.progress(
                min(idx / total_frame_count, 1.0),
                text=f"Frame {idx}/{total_frame_count} (analysed {analyzed_count}/{frames_to_analyze})",
            )

    cap.release()
    writer.release()
    progress.empty()

    # Aggregate stats
    unsafe_reports = [r for r in all_reports if r["scene_status"] == "UNSAFE"]
    total_violations = sum(r["summary"]["violating_workers"] for r in all_reports)
    overall = "UNSAFE" if unsafe_reports else "SAFE"

    st.subheader(f"Overall Status: {status_badge(overall)}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Frames Analysed", analyzed_count)
    c2.metric("Unsafe Frames", len(unsafe_reports))
    c3.metric("Violation Rate", f"{len(unsafe_reports) / max(analyzed_count, 1):.1%}")
    c4.metric("Violation Instances", total_violations)

    # Annotated video playback
    st.subheader("Annotated Video")
    with open(out_video_path, "rb") as vf:
        video_bytes = vf.read()
    st.video(video_bytes)

    # Safety timeline
    st.subheader("Safety Timeline")
    if all_reports:
        timeline_df = pd.DataFrame({
            "Frame": [r["frame_index"] for r in all_reports],
            "Violations": [r["summary"]["violating_workers"] for r in all_reports],
        })
        st.area_chart(
            timeline_df.set_index("Frame")[["Violations"]],
            color=["#ff4b4b"],
        )

    # Frame-level violation details
    if unsafe_reports:
        st.subheader("Frame-Level Violation Details")
        max_display = 50
        for i, r in enumerate(unsafe_reports):
            if i >= max_display:
                st.caption(
                    f"Showing first {max_display} unsafe frames. "
                    "Download the full report for complete details."
                )
                break
            with st.expander(
                f"Frame {r['frame_index']} — "
                f"{r['summary']['violating_workers']} violation(s)"
            ):
                rows = []
                for wr in r["worker_reports"]:
                    if wr["status"] == "VIOLATION":
                        tid = wr.get("track_id")
                        label = f"ID:{tid}" if tid is not None else f"W{wr['worker_index']}"
                        rows.append({
                            "Worker": label,
                            "Helmet": "Yes" if wr["helmet_detected"] else "No",
                            "Vest": "Yes" if wr["vest_detected"] else "No",
                            "Violations": ", ".join(wr["violations"]),
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows), hide_index=True)

    # Downloads
    st.subheader("Download Report")
    full_report = {
        "source": uploaded.name,
        "total_frames": idx,
        "fps": fps,
        "frames": all_reports,
    }
    json_str = json.dumps(full_report, indent=2)
    md_str = video_report_markdown(uploaded.name, idx, all_reports, timestamp)

    d1, d2, d3 = st.columns(3)
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
    d3.download_button(
        "Annotated Video",
        video_bytes,
        file_name=f"{Path(uploaded.name).stem}_annotated.mp4",
        mime="video/mp4",
    )
