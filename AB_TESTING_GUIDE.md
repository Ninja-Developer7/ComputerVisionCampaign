# A/B Testing Guide - Computer Vision Campaign

## Overview
This campaign includes A/B testing infrastructure to compare visual variants before launch.

### Current Test Setup

**Variant A (Control):** Neon Genesis - Cyberpunk Theme
- Visual Style: Bright, neon-focused cyberpunk aesthetic
- Narration: "In scene X, the story unfolds against neon rain and chrome reflections."
- Zoom Effect: 1.15x average
- Best For: Trendy platforms, optimistic/future-forward positioning

**Variant B (Treatment):** Neon Genesis - Dystopian-Tech Theme
- Visual Style: High-contrast, industrial, dark dystopian aesthetic
- Narration: "In the depths of scene X, forgotten technology tells forgotten stories."
- Zoom Effect: 1.20x average (more dramatic)
- Best For: Serious/dramatic positioning, high-engagement audiences

---

## Quick Start

### 1. Preview A/B Variants
See visual descriptions and narration differences:
```bash
cd atreyu
python3 scripts/ab_test.py preview \
  --variant-a neon-genesis \
  --variant-b neon-genesis-variant-b
```

### 2. Get Detailed Comparison Report
Analysis of aesthetics, motion characteristics, and recommendations:
```bash
cd atreyu
python3 scripts/ab_test.py compare \
  --variant-a neon-genesis \
  --variant-b neon-genesis-variant-b
```

### 3. List All Available Variants
```bash
cd atreyu
python3 scripts/ab_test.py report
```

---

## Full Render (Generate Videos)

### Render Variant A (Cyberpunk)
Generate complete 60-second video with images, narration, and soundtrack:
```bash
cd atreyu
python3 scripts/pipeline.py full --episode neon-genesis --duration 60
```

**Outputs:**
- `episodes/neon-genesis/scene_*.png` - 12 scene images
- `episodes/neon-genesis/episode.mp4` - Final 60-second video

### Render Variant B (Dystopian)
First, create the episode metadata:
```bash
cd atreyu
python3 scripts/init-episode --title "Neon Genesis - Variant B" --episode neon-genesis-variant-b
```

Then render:
```bash
python3 scripts/pipeline.py full --episode neon-genesis-variant-b --duration 60
```

**Note:** The pipeline steps can also be run individually:
```bash
python3 scripts/pipeline.py storyboard --episode neon-genesis-variant-b
python3 scripts/pipeline.py images --episode neon-genesis-variant-b --count 12
python3 scripts/pipeline.py narration --episode neon-genesis-variant-b
python3 scripts/pipeline.py soundtrack --episode neon-genesis-variant-b
python3 scripts/pipeline.py render --episode neon-genesis-variant-b --duration 60
```

---

## Key Metrics Comparison

| Metric | Variant A (Cyberpunk) | Variant B (Dystopian) |
|--------|----------------------|----------------------|
| **Visual Style** | Bright, neon | Dark, industrial |
| **Color Palette** | Blues, cyans, bright colors | Reds, grays, stark shadows |
| **Aesthetic Feel** | Optimistic, futuristic | Ominous, serious |
| **Avg Zoom Effect** | 1.15x | 1.20x |
| **Pan Pattern** | Center | Varied (L-R, center, R-L) |
| **Narrative Tone** | Hopeful | Mysterious |

---

## Testing Workflow

1. **Preview Phase** ✓
   - Review visual descriptions
   - Compare narrative tone
   - Check motion characteristics

2. **Render Phase**
   - Generate full video for each variant
   - Create comparable assets

3. **Evaluation Phase**
   - Test with sample audience
   - Measure engagement metrics
   - Collect feedback

4. **Launch Decision**
   - Choose winner or hybrid approach
   - Document results
   - Archive test data

---

## Creating New Variants

To create your own variant, copy and modify a storyboard:

```python
import json
import copy

# Load base
with open("storyboards/neon-genesis.json") as f:
    base = json.load(f)

# Create variant
my_variant = copy.deepcopy(base)
my_variant["title"] = "Neon Genesis - My Variant"

# Modify scenes
for scene in my_variant["scenes"]:
    scene["prompt"] = "Your custom prompt here"
    scene["narration"] = "Your custom narration"

# Save
with open("storyboards/neon-genesis-my-variant.json", "w") as f:
    json.dump(my_variant, f, indent=2)
```

---

## Output Locations

- **Storyboards:** `atreyu/storyboards/`
- **Episodes:** `atreyu/episodes/<episode-name>/`
- **Scene Images:** `atreyu/episodes/<episode-name>/scene_*.png`
- **Narration Audio:** `atreyu/voices/<episode>_narration.wav`
- **Soundtracks:** `atreyu/assets/<episode>_soundtrack.wav`
- **Final Videos:** `atreyu/episodes/<episode-name>/episode.mp4`

---

## Notes

- A/B testing framework is in `atreyu/scripts/ab_test.py`
- Full pipeline orchestration is in `atreyu/scripts/pipeline.py`
- Current placeholder implementation - image/audio generation uses fallbacks
- Ready for integration with actual image generation and TTS services

---

## Next Steps

1. ✓ Run preview to see variant descriptions
2. ✓ Review comparison report
3. → Render full videos for both variants
4. → Evaluate engagement metrics
5. → Make launch decision
