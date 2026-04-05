# Safety Rules - Construction Safety Monitor

## 1. Scope

This system evaluates visible workers in construction-style scenes and determines whether the scene is **safe** or **unsafe** based on visible PPE compliance.

For this version of the project, the safety check is limited to:

- helmet use,
- high-visibility vest use.

The system focuses only on what is visually detectable from the image or video frame.

---

## 2. Detector Inputs

The object detector predicts the following classes:

- `person`
- `helmet`
- `vest`

The detector output is then passed to a rule engine, which converts detections into worker-level and scene-level safety decisions.

---

## 3. Required PPE

Each detected worker is expected to wear:

- a helmet,
- a high-visibility vest.

A worker is considered compliant only when both required PPE items are detected and correctly associated with that worker.

---

## 4. Worker-Level Safety Rules

### Rule 1 - Missing Helmet

If a worker is detected but no helmet is associated with that worker, the worker is marked as violating the helmet rule.

- **Violation label:** `missing_helmet`

### Rule 2 - Missing Vest

If a worker is detected but no high-visibility vest is associated with that worker, the worker is marked as violating the vest rule.

- **Violation label:** `missing_vest`

### Rule 3 - Full PPE Compliance

A worker is considered compliant only if:

- a helmet is detected for that worker,
- and a vest is detected for that worker.

If either one is missing, the worker is treated as non-compliant.

---

## 5. Association Logic

The system does not only count objects in the scene.

Instead, it checks PPE at the **worker level** by associating:

- `helmet` detections with a worker’s upper region,
- `vest` detections with a worker’s torso region.

This makes the final decision more meaningful because the system evaluates whether **each worker** appears properly equipped, not just whether helmets or vests exist somewhere in the frame.

---

## 6. Scene-Level Decision

The final scene result is based on all detected workers.

- **SAFE**: all detected workers are compliant
- **UNSAFE**: one or more detected workers violate the PPE rules

If no worker is detected, the scene is treated as:

- **SAFE**
- with note: `no_workers_detected`

This means no worker requiring PPE was detected within the current scope.

---

## 7. Uncertainty Handling

To avoid overconfident decisions, the system can also attach a review note when visibility is poor.

The system currently handles the following uncertainty scenarios:

- **Worker is very small in the frame** — the person bounding box occupies less than 0.8% of the frame area, making PPE detection unreliable.
- **Worker is heavily truncated** — the person bounding box touches the edge of the image, meaning part of the worker (and their PPE) may be cut off.
- **Detection confidence is weak** — the person, helmet, or vest detection confidence is only marginally above the minimum threshold, indicating the model is not highly certain about its prediction.

In such cases, the system adds notes such as:

- `person_too_small_for_reliable_ppe_check`
- `person_truncated_at_frame_edge`
- `low_person_detection_confidence`
- `low_helmet_confidence`
- `low_vest_confidence`

If a worker has uncertainty notes but no clear PPE violation, their status is set to **UNCERTAIN**, and the scene status becomes **REVIEW**.

If a worker has both a violation and uncertainty notes, the **VIOLATION** status takes priority.

---

## 8. Examples of Violations

### Example 1 - Missing helmet

Detected:

- person
- vest
- no associated helmet

Result:

- worker status: non-compliant
- violation: `missing_helmet`
- scene status: `UNSAFE`

### Example 2 - Missing vest

Detected:

- person
- helmet
- no associated vest

Result:

- worker status: non-compliant
- violation: `missing_vest`
- scene status: `UNSAFE`

### Example 3 - Missing both

Detected:

- person only

Result:

- worker status: non-compliant
- violations:
  - `missing_helmet`
  - `missing_vest`
- scene status: `UNSAFE`

### Example 4 - Fully compliant

Detected:

- person
- helmet
- vest

Result:

- worker status: compliant
- scene status: `SAFE` if all workers in the scene are also compliant

---

## 9. Human-Readable Alert Output

The system does not return only a binary flag.

For each unsafe case, it should produce a short human-readable explanation such as:

- `Worker 2: helmet not detected`
- `Worker 1: high-visibility vest not detected`
- `Scene unsafe: 2 workers have PPE violations`
- `Review recommended: one worker is too small for reliable PPE verification`

This makes the result easier to understand and better aligned with real safety monitoring use.

---

## 10. Out of Scope

The following are not enforced in the current version:

- helmet fastening verification,
- vest closure correctness,
- harness detection,
- fall-protection checking,
- unsafe posture detection,
- advanced zone-based PPE policies,
- partial occlusion detection (e.g., worker hidden behind machinery or another worker),
- PPE visibility analysis based on lighting, blur, or shadow conditions.

These are valid future extensions, but they are outside the current detector labels and current project scope.
