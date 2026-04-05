# Construction Safety Monitor

A computer vision system that detects workers on construction sites, checks whether they are wearing the required PPE (helmet and vest), and flags safety violations — all through an interactive Streamlit web app.

---

## Project Structure

```
Construction-Safety-Monitor/
├── app.py                   # Streamlit web app
├── configs/
│   └── rules.yaml           # Thresholds, association params, zone config
├── docs/
│   ├── dataset_documentation.md
│   └── safety_rules.md
├── examples/                # Sample test images
│   ├── safe_example.jpg
│   ├── unsafe_missing_helmet.jpg
│   └── unsafe_missing_vest.jpg
├── model/                   # Place best.pt here
├── notebooks/               # Training notebooks
├── src/
│   ├── main.py              # CLI entry point
│   ├── monitor.py           # SafetyMonitor (detection + annotation)
│   ├── rules.py             # Rule engine & evaluation logic
│   ├── schemas.py           # Detection, WorkerAssessment, FrameReport
│   ├── smoother.py          # Temporal smoothing for video
│   └── reports.py           # Report generation helpers
├── requirements.txt
└── README.md
```

---

## Prerequisites

| Requirement   | Version                          |
| ------------- | -------------------------------- |
| Python        | 3.9 or higher                    |
| Trained model | `best.pt` placed inside `model/` |

---

## Training Notebook

The training notebook is available in the `notebooks/` folder as a `.ipynb` file.

To view or reproduce the training process:

1. Open the notebook in **Google Colab**.
2. Enable a **GPU runtime** in Colab if needed.
3. Run the notebook **cell by cell** from top to bottom.
4. The notebook shows the training steps, model setup, and evaluation results.

## Run the Streamlit App

### 1. Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it:

- **Windows (PowerShell)**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (CMD)**
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS / Linux**
  ```bash
  source venv/bin/activate
  ```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Launch the Streamlit app

```bash
streamlit run app.py
```

This opens the app in your browser (usually at `http://localhost:8501`).

From the app you can:

- Upload an **image** or **video** from the `examples/` folder or your own files.
- View the annotated output with bounding boxes and status labels.
- See a scene summary (total workers, compliant, violations, uncertain) and a per-worker table.
- Download the analysis as a **JSON** or **Markdown** report.
- For video: view a safety timeline chart and expandable frame-level violation details.

---

## Documentation and Notebooks

### Project Documentation

| File                                                             | Description                                                                                                                     |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| [`docs/dataset_documentation.md`](docs/dataset_documentation.md) | Explains the dataset sources, manual data collection process, annotation workflow, final class schema, and dataset composition. |
| [`docs/safety_rules.md`](docs/safety_rules.md)                   | Defines the PPE compliance rules, worker-level and scene-level decision logic, uncertainty handling, and violation examples.    |

### Notebooks

| Notebook                                                           | Description                                                                                               |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| [`notebooks/Model_Training.ipynb`](notebooks/Model_Training.ipynb) | Contains the model training pipeline, evaluation steps, and training results for the YOLOv8 PPE detector. |

---

## Problem Framing & Why YOLOv8

This project is framed as a **construction-site PPE monitoring** problem. The system first detects three visual classes in each frame — **person, helmet, and vest** — and then uses the application layer to determine whether each worker is compliant and whether the overall scene is safe or unsafe. This separation keeps the model focused on reliable object detection while allowing the safety logic to remain transparent, configurable, and easy to improve. This framing matches the assignment’s core requirements: worker detection, PPE recognition, compliance checking, and violation flagging.

**Why YOLOv8**

- YOLOv8 was chosen because this task needs **object detection**, not simple image classification.
- It is a strong fit for construction monitoring because it balances **accuracy and practical inference speed** for frame-by-frame analysis.
- Using **pretrained YOLOv8 weights** also makes sense for a custom PPE dataset, because transfer learning helps adapt the detector to the target classes more efficiently.

## Evaluation with Results

The model was evaluated using standard object detection metrics: **precision, recall, mAP50, and mAP50-95**. Precision shows how many predicted detections are correct, recall shows how many real objects are found, and mAP summarizes detection performance across classes and overlap thresholds.

**Overall results**

- Validation: **Precision 0.9125**, **Recall 0.9054**, **mAP50 0.9441**, **mAP50-95 0.5712**

**Interpretation**

- The model performs well overall, with **strong precision and recall**, meaning most detections are correct and most real objects are found.
- The high **mAP50** shows that the model can detect the target objects reliably at a practical overlap threshold.
- The model performs especially well at **recognizing objects correctly**.
- It struggles more with **precise bounding box localization** under stricter IoU thresholds, as shown by the lower **mAP50-95** compared with **mAP50**.
- Overall, the model is good at identifying **what** is present, but still has room to improve in drawing **more accurate box boundaries**.

## Known Limitations and Failure Cases

This model is a strong baseline, but it still has important limitations. The detector performs best when workers are clearly visible, PPE is not heavily occluded, and the scene has reasonable lighting. It is likely to struggle more with **small or distant workers**, **partial occlusion**, **shadow-heavy or low-light scenes**, and **cluttered backgrounds**. These are common failure patterns in object detection, especially when objects are small or only partly visible.

**Observed limitations**

- **Small / distant workers:** helmets and vests become harder to detect accurately when workers occupy a small part of the frame. The system flags these cases as uncertain (`person_too_small_for_reliable_ppe_check`).
- **Occlusion:** PPE can be missed when it is partially hidden by body pose, tools, machinery, or other workers. Partial occlusion detection is not yet implemented.
- **Vest detection is harder:** the lower vest recall suggests missed vest detections are one of the main sources of downstream compliance errors.
- **Bounding box precision:** the gap between mAP50 and mAP50-95 suggests the detector is often correct at a coarse level, but bounding boxes are less precise under stricter evaluation.
- **Marginal confidence detections:** when the model's confidence is only slightly above the threshold, the system flags these as uncertain (`low_person_detection_confidence`, `low_helmet_confidence`, `low_vest_confidence`) to avoid overconfident compliance decisions.

**Important scope limitation**

- The trained model detects only **person, helmet, and vest**.
- Final compliance checking and scene-level safety decisions are handled in the application layer after detection.

## License

See [LICENSE](LICENSE) for details.
