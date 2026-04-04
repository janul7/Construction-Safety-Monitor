# Dataset Documentation - Construction Safety Monitor

## 1. Overview

This project uses a custom construction-safety dataset built for a PPE compliance monitoring system.

The main goal of the dataset is to support a system that can answer the practical safety question:

> **Is this situation safe or unsafe?**

The final object classes used in training are:

- `0: person`
- `1: helmet`
- `2: vest`

This dataset was prepared to support:

1. worker detection,
2. PPE detection,
3. worker-level compliance reasoning,
4. scene-level safety classification.

---

## 2. Dataset Sources

This submission follows the assignment requirement of using a **custom dataset** by extending a public baseline dataset with my own manually collected images and video frames.

### Dataset links

- **Final merged training dataset:** `[ADD_GOOGLE_DRIVE_LINK_FINAL_DATASET]`
- **Baseline dataset used as starting point:** `[ADD_GOOGLE_DRIVE_LINK_BASELINE_DATASET]`
- **Manually collected images:** `[ADD_GOOGLE_DRIVE_LINK_MANUAL_IMAGES]`
- **Manually collected videos:** `[ADD_GOOGLE_DRIVE_LINK_MANUAL_VIDEOS]`

<!-- FILL_THIS: Add the exact public dataset name and source link below. If you used CHV-PPE, write that exact name here. -->

- **Base dataset name:** `[FILL_THIS_WITH_EXACT_DATASET_NAME]`
- **Base dataset source:** `[FILL_THIS_WITH_SOURCE_LINK]`

### Why this approach was used

I did not rely only on a public benchmark. Instead, I extended the baseline dataset with additional manually collected data so the final dataset better reflects the assignment requirement for:

- varied environments,
- varied lighting conditions,
- safe and unsafe scenes,
- and more realistic PPE monitoring scenarios.

---

## 3. Manual Data Collection

I collected additional data in two forms:

- manually selected still images,
- manually selected videos, later converted into representative frames.

### Image collection process

To collect additional images, I searched reusable public sources for construction-related scenes and selected examples that improved diversity.

Typical search keywords included:

- `construction worker helmet vest`
- `construction site workers`
- `warehouse safety vest`
- `industrial worker hard hat`
- `construction team outdoor site`
- `indoor construction worker PPE`

I reviewed candidate images one by one and selected examples that helped cover:

- compliant workers,
- missing helmet cases,
- missing vest cases,
- multiple workers in one scene,
- indoor and outdoor settings,
- different camera angles,
- difficult lighting,
- and partial occlusion.

<!-- FILL_THIS: Replace the example source names below with the exact sources you actually used. -->

Example reusable sources reviewed:

- `Pexels`
- `Wikimedia Commons`
- `[ADD_ANY_OTHER_SOURCE_YOU_USED]`

### Video collection process

I also collected public videos containing construction-style scenes and converted them into frames for annotation.

The main purpose of video collection was to capture:

- natural worker motion,
- varied poses,
- realistic camera perspectives,
- multi-worker scenes,
- and more diverse PPE visibility patterns.

For each video, frame extraction was done using a simple sampling strategy rather than exporting every frame.

Example strategy:

- use **1 frame every 3 seconds** for slower scenes,
- use **1 frame every 1 second** when worker movement or camera change is faster.

This helped reduce near-duplicate frames while still preserving useful variation.

<!-- FILL_THIS: Add your exact frame sampling strategy if it changed by video. -->

---

## 4. Annotation Process

All manually collected data was annotated in **Roboflow** using a unified 3-class schema:

- `person`
- `helmet`
- `vest`

### Image annotation workflow

1. Create the project with the final three classes.
2. Upload the collected images to Roboflow.
3. Draw bounding boxes around each visible target object.
4. Annotate every image using the same label definitions.
5. Export the dataset in **YOLOv8 format**.

### Video annotation workflow

1. Upload each video to Roboflow.
2. Decide a frame extraction strategy based on scene motion.
3. Generate representative frames from the video.
4. Annotate the exported frames using the same three classes.
5. Export the labeled result in **YOLOv8 format**.

### Annotation rules used

- annotate visible workers as `person`,
- annotate helmets being worn as `helmet`,
- annotate visible high-visibility vests being worn as `vest`,
- do not annotate loose helmets lying in the scene,
- do not create negative classes such as `no-helmet` or `no-vest`,
- do not guess hidden PPE that is not visible.

This annotation design keeps the detector simple and moves the final compliance logic into the rule engine.

---

## 5. Final Dataset Assembly

After annotation, I used Google Colab to prepare the final dataset used for training.

The training dataset was built by combining three labeled sources:

- the annotated baseline dataset,
- manually collected annotated images,
- annotated frames extracted from manually collected videos.

The final preparation pipeline included:

- importing all labeled subsets,
- checking label consistency,
- basic preprocessing and cleanup,
- merging all subsets into one final dataset,
- creating train / validation / test splits,
- and preparing the final structure for YOLOv8 training.

This produced a single merged dataset used to train the final PPE detector.

---

## 6. Final Class Definition

The final label schema is:

- `0: person`
- `1: helmet`
- `2: vest`

This class design was chosen intentionally.

Instead of creating separate negative classes such as `no-helmet` or `no-vest`, the system detects workers and visible PPE first, then determines violations through rule-based reasoning.

That makes the system:

- easier to explain,
- easier to debug,
- and better aligned with the final safe/unsafe decision task.

---

## 7. Dataset Summary

<!-- FILL_THIS: Replace all placeholders below with exact counts from your final dataset. -->

- **Total images / frames:** `[FILL_THIS]`
- **Baseline dataset images used:** `[FILL_THIS]`
- **Manually collected images added:** `[FILL_THIS]`
- **Video frames added:** `[FILL_THIS]`

### Final split

- **Train:** `[FILL_THIS]`
- **Validation:** `[FILL_THIS]`
- **Test:** `[FILL_THIS]`

### Class distribution

- **Person instances:** `[FILL_THIS]`
- **Helmet instances:** `[FILL_THIS]`
- **Vest instances:** `[FILL_THIS]`

### Scene diversity summary

- **Outdoor scenes:** `[FILL_THIS]`
- **Indoor / warehouse / enclosed scenes:** `[FILL_THIS]`
- **Daylight scenes:** `[FILL_THIS]`
- **Artificial-light scenes:** `[FILL_THIS]`
- **Primarily safe scenes:** `[FILL_THIS]`
- **Primarily unsafe scenes:** `[FILL_THIS]`

<!-- FILL_THIS: Keep only the counts you can support with your final validation output. -->

---

## 8. Notes and Limitations

This dataset is designed specifically for visible PPE compliance using:

- worker presence,
- helmet presence,
- vest presence.

It does **not** currently label:

- helmet fastening state,
- vest closure state,
- fall-protection harnesses,
- unsafe posture,
- or other non-PPE hazards.

These limitations are intentional and keep the dataset aligned with the current project scope.
