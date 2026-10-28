# EcoVision household-item classifier evaluation

- Model: `openai/clip-vit-base-patch32`
- Dataset: EcoVision real household items v1.0.0
- Evaluated: 2026-10-28T19:00:16.687424+00:00
- Images: 30 real, human-labeled household-item photographs

## Result

Top-1 accuracy was **70.0%** (21/30).

This is a small diagnostic baseline, not a production acceptance threshold. It covers every current candidate label at least once, but most labels have only one example. Beverage cans, food cans, plastic beverage bottles, and electronic devices have two examples each.

## Confused categories

| Known label | Predicted label | Count |
|---|---|---:|
| a clear plastic beverage bottle | a clear glass bottle or jar | 1 |
| a polystyrene foam container | a disposable paper cup or takeout container | 1 |
| aluminum foil or tray | a clear plastic beverage bottle | 1 |
| an aluminum beverage can | mixed-material packaging | 1 |
| an electronic device | a household battery | 1 |
| an opaque plastic jug or container | a disposable paper cup or takeout container | 1 |
| another type of household object | a clear glass bottle or jar | 1 |
| mixed-material packaging | a food or beverage carton | 1 |
| yard trimmings | a polystyrene foam container | 1 |

No exact known-label → predicted-label pair occurred more than once. The most common incorrect destination labels were a clear glass bottle or jar, a disposable paper cup or takeout container (2 errors each).

## Specific failures

| Image ID | Known label | Predicted label | Top-1 score | Known-label rank | Image characteristic |
|---|---|---|---:|---:|---|
| `aluminum_can_02` | an aluminum beverage can | mixed-material packaging | 0.228 | 6 | The can is heavily crushed, so its normal cylindrical silhouette is absent. |
| `plastic_bottle_01` | a clear plastic beverage bottle | a clear glass bottle or jar | 0.319 | 2 | The clear PET bottle has the transparency and outline of a glass bottle. |
| `plastic_jug_01` | an opaque plastic jug or container | a disposable paper cup or takeout container | 0.546 | 3 | The compact square jug resembles a lidded takeout container. |
| `foam_container_01` | a polystyrene foam container | a disposable paper cup or takeout container | 0.803 | 2 | The closed foam clamshell is also visually a generic takeout container. |
| `electronic_phone_01` | an electronic device | a household battery | 0.497 | 2 | The dark rectangular phone resembles a flat rechargeable battery. |
| `mixed_packaging_01` | mixed-material packaging | a food or beverage carton | 0.406 | 2 | The opened chip bag exposes food and reflective layers instead of a clean package silhouette. |
| `foil_tray_01` | aluminum foil or tray | a clear plastic beverage bottle | 0.181 | 7 | The image contains a pile of crushed tray fragments rather than one intact tray. |
| `yard_trimmings_01` | yard trimmings | a polystyrene foam container | 0.628 | 4 | The grass clippings sit inside a concrete drain whose rectangular shape dominates the frame. |
| `other_toothbrush_01` | another type of household object | a clear glass bottle or jar | 0.473 | 5 | The translucent, elongated toothbrush overlaps visually with bottles, straws, and medical sharps. |

## Per-label results

| Known label | Correct | Support | Accuracy |
|---|---:|---:|---:|
| an aluminum beverage can | 1 | 2 | 50.0% |
| a metal food can | 2 | 2 | 100.0% |
| a clear glass bottle or jar | 1 | 1 | 100.0% |
| a cardboard box | 1 | 1 | 100.0% |
| a sheet of paper | 1 | 1 | 100.0% |
| a clear plastic beverage bottle | 1 | 2 | 50.0% |
| an opaque plastic jug or container | 0 | 1 | 0.0% |
| a plastic bag or plastic film | 1 | 1 | 100.0% |
| a polystyrene foam container | 0 | 1 | 0.0% |
| food waste | 1 | 1 | 100.0% |
| a household battery | 1 | 1 | 100.0% |
| an electronic device | 1 | 2 | 50.0% |
| clothing or textile | 1 | 1 | 100.0% |
| mixed-material packaging | 0 | 1 | 0.0% |
| adhesive tape | 1 | 1 | 100.0% |
| aluminum foil or tray | 0 | 1 | 0.0% |
| a pizza box | 1 | 1 | 100.0% |
| a disposable paper cup or takeout container | 1 | 1 | 100.0% |
| a food or beverage carton | 1 | 1 | 100.0% |
| a ceramic dish or drinking glass | 1 | 1 | 100.0% |
| a plastic utensil or straw | 1 | 1 | 100.0% |
| yard trimmings | 0 | 1 | 0.0% |
| a CFL or fluorescent light bulb | 1 | 1 | 100.0% |
| a paint or solvent container | 1 | 1 | 100.0% |
| a needle or medical sharp | 1 | 1 | 100.0% |
| another type of household object | 0 | 1 | 0.0% |

## Reproduce

From `backend/`, with the existing virtual environment activated:

```bash
python -m evaluation.evaluate
```

The first run downloads the exact, checksummed Wikimedia Commons thumbnails listed in `evaluation/household_items.json`. Later runs reuse the ignored local cache. Use `--offline` to prohibit downloads or `--refresh` to download and verify every image again.

The JSON result beside this report contains each image's top five predictions, the known label's rank, and the raw confidence-like CLIP scores. These scores are useful for ranking but are not calibrated probabilities.
