#!/usr/bin/env python3
"""
NINJISTICS LIBRARIAN - Episode 1: The Relic's Echo
Cyberpunk Episode Builder - Storyboard & Renderer
Generates a 60-second episode video from 12 scene images with:
- Ken Burns camera motion
- Voice narration
- Cyberpunk soundtrack
- FFmpeg assembly (via MoviePy)
"""

import os
import json
from pathlib import Path

WORKDIR = Path("/Users/ronin/episode_builder")
SCENES_DIR = WORKDIR / "scenes"
AUDIO_DIR = WORKDIR / "audio"
SCRIPTS_DIR = WORKDIR / "scripts"

SCENES_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
SCRIPTS_DIR.mkdir(exist_ok=True)

SCENE_PROMPTS = [
    "cinematic wide shot, cyberpunk city skyline at midnight, towering megastructures with glowing neon signs in kanji and english, heavy rain falling, crisscrossing electric wires and holographic advertisements, moody teal and magenta color palette, ultra-realistic digital art, NEO-TOKYO",
    "extreme close-up cybernetic portrait, a glowing blue bionic eye, intricate mechanical iris with rotating aperture, reflection of neon city lights on cornea, sci-fi horror style, shallow depth of field, purple and cyan lighting, KURO",
    "cinematic narrow alley in a cyberpunk city, rain-soaked asphalt reflecting neon, steam rising from ground vents, flickering holographic storefront signs, moisture and lens fog, Japanese back alley aesthetic, 4k detail, SHADOW CLAN",
    "medium shot street samurai standing in heavy rain, dark trench coat billowing, katana sheathed at side, blue hair with neon highlights, face partially shadowed, wet street reflecting neon pink and blue signs, dramatic backlighting, KURO",
    "wide cyberpunk night market scene, crowded street with stalls selling glowing cybernetic augmentations and tech, cyborg patrons with visible modifications, street food lanterns, flying drones overhead, dense urban atmosphere, blade runner inspired, THE LIBRARY",
    "interior shot of a corporate tower penthouse, glass walls showing sprawling city view at night, translucent holographic data streams and financial charts floating around, minimalist brutalist furniture, view of neon grid below, corporate dystopia, AI VAULT",
    "hacker in a dimly lit basement computer den, surrounded by CRT monitors displaying scrolling code and live city surveillance feeds with face recognition overlays, tangled wires, glow of screens illuminating face wearing VR goggles, hacking scene, ALLIES",
    "dynamic action shot cyberpunk highway chase, flying cars with neon trails weaving between skyscrapers, motion blur and light streaks, rain, low angle ground view showing neon road markings, high speed, futuristic transportation, SHADOW CLAN CHASE",
    "cinematic rooftop duel at night, two futuristic warriors with ornate energy blades locked in a standoff, electric neon sparks, stormy sky with lightning, rain-soaked rooftop, dramatic cinematic lighting, anime scene composition, tension and motion, SHADOW CLAN",
    "surreal neural interface chamber, person reclining in medical chair with dozens of bioluminescent data cables connecting to the back of their skull, virtual cityscape projection shimmering around the room, blue and green light, silence and connection, KURO LINKING",
    "melancholic monologue scene, lone figure sitting on a high ledge overlooking the city at night, half-empty whiskey bottle, rain falling, city lights blur in bokeh, figure in silhouette, reflective and somber, noir atmosphere, MENTOR'S WISDOM",
    "resolving wide shot, city skyline at dawn, rain stopped, first golden sunlight mixing with fading neon signs, silhouetted figure walking away from camera toward the light, wet streets reflecting transition from night to morning, hopeful ending, AI VAULT APPROACH"
]

NARRATION_SCRIPT = [
    (0.0, "In Neo-Tokyo, the shadows remember what the light forgets."),
    (5.5, "Kuro carries the Relic—a living interface to the AI Council."),
    (11.0, "The Shadow Clan hunts the sacred code through acid rain streets."),
    (16.5, "The Library holds the answers, if you dare read them."),
    (22.0, "Above the city, the AI Vault waits in silence and light."),
    (27.5, "Allies emerge from the underground, wired and ready."),
    (33.0, "The highway becomes a river of neon and pursuit."),
    (38.5, "Konfrontation. Betrayal. The blade speaks truth."),
    (44.0, "Kuro links to the network. Secrets flood the cortex."),
    (49.5, "Mentor's voice echoes: the past is data."),
    (55.0, "A new dawn approaches the AI Vault..."),
    (59.0, ""),
]

TITLE = "NINJISTICS LIBRARIAN - Episode 1: The Relic's Echo"
CHARACTERS = ["Kuro", "Mentor", "Villain"]
LOCATIONS = ["Neo-Tokyo", "Library", "AI Vault"]

def save_storyboard():
    data = {
        "title": TITLE,
        "series": "NINJISTICS LIBRARIAN",
        "episode": 1,
        "duration_seconds": 60,
        "scenes": len(SCENE_PROMPTS),
        "characters": CHARACTERS,
        "locations": LOCATIONS,
        "scene_prompts": SCENE_PROMPTS,
        "narration": NARRATION_SCRIPT,
    }
    with open(WORKDIR / "storyboard.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Storyboard saved.")

if __name__ == "__main__":
    save_storyboard()
