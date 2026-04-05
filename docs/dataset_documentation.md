# Dataset Documentation - Construction Safety Monitor

## 1. Overview

This project uses a custom construction-safety dataset created for a PPE compliance monitoring system.

The main purpose of the dataset is to support a system that can answer the practical safety question:

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

The final dataset was created by combining:

1. a reviewed public baseline dataset, and
2. a small amount of manually collected supplementary data.

### Baseline dataset

The baseline dataset used as the starting point was:

- **Dataset name:** `CHV-PPE (Color Helmet and Vest PPE Dataset)`
- **Source platform:** `Roboflow Universe`
- **Initial public dataset size:** `1330 images`
- **Dataset link:** `https://universe.roboflow.com/ppechvdataset/chv-ppe`
- **Downloaded version link:** `https://drive.google.com/file/d/187sYErM0Gi4WMznoUHNTtfjHWJDsvDQN/view?usp=drive_link`

Before downloading the baseline dataset, I reviewed the images and annotations in Roboflow to check whether they were suitable for the target construction safety scenario. During this review:

- images that did not match the project requirements were removed,
- existing annotations were checked for quality,
- and bounding boxes were adjusted where necessary.

### Supplementary data

To improve variation and make the dataset more relevant to the project scenario, I collected a small amount of additional public data:

- **Manually collected images:** 30 images
- **Manually collected videos:** 6 videos

These were gathered from reusable public sources such as:

- `Pexels`
- `Wikimedia Commons`

Project file links:

- **Final merged training dataset:** [Final merged training dataset](https://drive.google.com/file/d/1n9XJKficD09KdzImArLuiFKXn5o9zyvr/view?usp=drive_link)
- **Manually collected images:** [Manually collected images](https://drive.google.com/file/d/1S6VaZ-RQcwOuK7ob6QOcEFjaO9LkEHpO/view?usp=drive_link)
- **Manually collected videos:** [Manually collected videos](https://drive.google.com/file/d/1-Rv069J6mbFnd_si4EmchbsJx6KcCEqa/view?usp=drive_link)
- **Sample of video frames:** [Sample of video frames](https://drive.google.com/file/d/14YvOzRdIh_7Q0-8GcUobQlXG7KnMucLu/view?usp=drive_link)

---

## 3. Additional Data Collection

The manually collected supplementary data was added to introduce useful variation beyond the baseline dataset. The purpose of this step was not to build a large separate dataset, but to include scenes that better matched the target safety-monitoring task. Videos were especially useful because they added more realistic scene variation, including motion, different viewpoints, and partial occlusions.

Preference was given to images and videos showing:

- workers wearing helmets and high-visibility vests,
- workers with missing PPE,
- indoor and outdoor construction-related settings,
- multiple workers in a single scene,
- different viewpoints,
- varied lighting and environmental conditions.

### Video frame extraction

For public videos, frames were not extracted from every frame. Instead, a simple sampling strategy was used to reduce near-duplicate images while preserving useful variation:

- for slower scenes, approximately **one frame every 3 seconds**,
- for faster scenes or moving-camera scenes, approximately **one frame every 1 second**.

The extracted frames were then annotated and added to the final dataset.

---

## 4. Annotation Process

The public baseline dataset originally contained six classes:

- `vest`
- `person`
- `blue-safety-helmet`
- `red-safety-helmet`
- `white-safety-helmet`
- `yellow-safety-helmet`

After reviewing and refining the baseline annotations, the original class structure was mapped into the final three classes used in this project:

- `person`
- `helmet`
- `vest`

### Class mapping

The mapping was performed as follows:

- `person` → `person`
- `vest` → `vest`
- `blue-safety-helmet` → `helmet`
- `red-safety-helmet` → `helmet`
- `white-safety-helmet` → `helmet`
- `yellow-safety-helmet` → `helmet`

This means that all helmet-color categories from the public dataset were merged into a single `helmet` class.

For the manually collected images and video frames, annotation was performed directly from the beginning using the same final three-class schema:

- `person`
- `helmet`
- `vest`

This ensured consistency across all data sources before merging them into the final training dataset.

### Annotation rules used

The following annotation rules were applied consistently:

- annotate every visible worker as `person`,
- annotate visible helmets being worn as `helmet`,
- annotate visible high-visibility vests being worn as `vest`,
- do not assume or label PPE that is fully hidden or not visually observable.

The final labeled dataset was exported in **YOLOv8 format** for training.

---

## 5. Final Class Definition

The final label schema is:

- `0: person`
- `1: helmet`
- `2: vest`

This class design was chosen intentionally.

Instead of defining separate negative classes such as `no-helmet` or `no-vest`, the system first detects workers and visible PPE items, and then determines safety violations through rule-based reasoning.

This makes the system:

- easier to interpret,
- easier to debug,
- and better aligned with the final safe/unsafe decision-making task.

---

## 6. Dataset Summary

- **Total images / frames:** `1372`

### Final split

- **Train:** `1093`
- **Validation:** `141`
- **Test:** `138`

### Class distribution

- **Person instances:** `4009`
- **Helmet instances:** `3632`
- **Vest instances:** `1872`

---

## 7. Notes and Limitations

This dataset is designed specifically for visible PPE compliance based on:

- worker presence,
- helmet presence,
- vest presence.

It does **not** currently label:

- helmet fastening state,
- vest closure state,
- fall-protection harnesses,
- unsafe posture,
- other non-PPE hazards.

These limitations are intentional and keep the dataset aligned with the current project scope.
