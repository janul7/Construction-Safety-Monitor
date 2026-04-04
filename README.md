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

## How to Run (Step by Step)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/Construction-Safety-Monitor.git
cd Construction-Safety-Monitor
```

### 2. Create a virtual environment (recommended)

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add the trained model

Copy your trained YOLOv8 weights file into the `model/` folder:

```
model/best.pt
```

### 5. Launch the Streamlit app

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

## CLI Usage (Optional)

```bash
# Analyse an image
python -m src.main --model model/best.pt --rules configs/rules.yaml --source examples/safe_example.jpg

# Analyse a video
python -m src.main --model model/best.pt --rules configs/rules.yaml --source path/to/video.mp4

# Custom output directory
python -m src.main --model model/best.pt --rules configs/rules.yaml --source examples/unsafe_missing_helmet.jpg --output results/
```

Results are saved to `runs/output/` by default.

---

## Documentation

| Document                                                         | Description                                                |
| ---------------------------------------------------------------- | ---------------------------------------------------------- |
| [`docs/dataset_documentation.md`](docs/dataset_documentation.md) | Dataset details, class distribution, annotation format     |
| [`docs/safety_rules.md`](docs/safety_rules.md)                   | Rule engine logic, spatial association, zone configuration |

---

## License

See [LICENSE](LICENSE) for details.
