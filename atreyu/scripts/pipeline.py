#!/usr/bin/env python3
"""
atreyu pipeline
===============

Production flow:
 storyboard -> 12 scene images -> Ken Burns animation -> voice narration ->
 cyberpunk soundtrack -> FFmpeg assembly -> episodes/episodeNNNN.mp4

Usage examples
--------------
  python pipeline.py init-episode --title "Neon Genesis"
  python pipeline.py storyboard --episode neon_genesis
  python pipeline.py images     --episode neon_genesis --count 12
  python pipeline.py narration  --episode neon_genesis
  python pipeline.py soundtrack --episode neon_genesis
  python pipeline.py render     --episode neon_genesis --duration 60
  python pipeline.py full       --episode neon_genesis --duration 60

Artifacts
---------
 episodes/<episode>/
   scene_001.png
   scene_001_kenburns.mp4
   ...
   episode.mp4
 storyboards/<episode>.json
 voices/<episode>_narration.wav
 assets/<episode>_soundtrack.wav
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================================
# Paths
# ============================================================================
ROOT = Path(__file__).resolve().parents[1]
EPISODES_DIR = ROOT / "episodes"
STORYBOARDS_DIR = ROOT / "storyboards"
CHARACTERS_DIR = ROOT / "characters"
ASSETS_DIR = ROOT / "assets"
VOICES_DIR = ROOT / "voices"
VIDEOS_DIR = ROOT / "videos"
CONFIG_DIR = ROOT / "config"

for p in [EPISODES_DIR, STORYBOARDS_DIR, CHARACTERS_DIR, ASSETS_DIR, VOICES_DIR, VIDEOS_DIR]:
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class Scene:
    id: int
    slug: str
    title: str
    prompt: str
    narration: str
    duration: float
    zoom_start: str
    zoom_end: str
    pan: str


def slugify(text: str) -> str:
    return "-".join(text.lower().split())[:48]


def ensure_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

# ============================================================================
# episode management
# ============================================================================
class Episode:
    def __init__(self, name: str, title: str = "", duration: float = 60.0, fps: int = 24):
        self.name = name
        self.title = title or name.replace("-", " ").title()
        self.duration = float(duration)
        self.fps = int(fps)
        self.dir = EPISODES_DIR / name
        self.dir.mkdir(exist_ok=True)
        self.scenes: List[Scene] = []
        self.meta_path = self.dir / "meta.json"
        self.state_path = Path(CONFIG_DIR, "pipeline_state.json")
        CONFIG_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------ state
    def save_meta(self):
        data = {
            "name": self.name,
            "title": self.title,
            "duration": self.duration,
            "fps": self.fps,
            "scene_count": len(self.scenes),
        }
        self.meta_path.write_text(json.dumps(data, indent=2))

    def load_scenes(self) -> bool:
        p = self.dir / "scenes.json"
        if not p.exists():
            return False
        raw = json.loads(p.read_text())
        self.scenes = [Scene(**s) for s in raw]
        return True

    def save_scenes(self):
        (self.dir / "scenes.json").write_text(
            json.dumps([asdict(s) for s in self.scenes], indent=2)
        )

    # ------------------------------------------------------------------ helpers
    def scene_image(self, idx: int) -> Path:
        return self.dir / f"scene_{idx:03d}.png"

    def scene_clip(self, idx: int, suffix: str = "kenburns") -> Path:
        return self.dir / f"scene_{idx:03d}_{suffix}.mp4"

    @property
    def final_path(self) -> Path:
        return self.dir / "episode.mp4"

# ============================================================================
# generators
# ============================================================================
def cmd_init_episode(name: str, title: str, duration: float) -> Episode:
    ep = Episode(name=slugify(name), title=title, duration=duration)
    ep.save_meta()
    print(f"[init] created episode '{ep.name}' -> {ep.dir}")
    return ep


def cmd_storyboard(ep: Episode, count: int = 12):
    ep.scenes = _default_storyboard(ep.title, count)
    ep.save_scenes()
    ep.save_meta()
    # persist canonical storyboard too
    out = STORYBOARDS_DIR / f"{ep.name}.json"
    out.write_text(
        json.dumps(
            {
                "episode": ep.name,
                "title": ep.title,
                "scene_count": len(ep.scenes),
                "scenes": [asdict(s) for s in ep.scenes],
            },
            indent=2,
        )
    )
    print(f"[storyboard] wrote {len(ep.scenes)} scenes -> {out}")
    return ep


def cmd_images(ep: Episode, prompt_suffix: str = ""):
    """Generate 12 scene images. Uses image_generate tool via shell if available."""
    if not ep.scenes:
        if not ep.load_scenes():
            raise SystemExit("No scenes found. Run storyboard first.")

    existing = []
    for s in ep.scenes:
        p = ep.scene_image(s.id)
        existing.append(p.exists())

    if all(existing):
        print(f"[images] all {len(ep.scenes)} scene images already exist in {ep.dir}")
        return

    print("[images] generating scene images ...")
    for s in ep.scenes:
        p = ep.scene_image(s.id)
        if p.exists():
            print(f"  - scene_{s.id:03d} exists, skip")
            continue

        prompt = f"Cyberpunk storyboard illustration: {s.title}. {s.prompt}"
        if prompt_suffix:
            prompt += f" {prompt_suffix}"

        # Call Hermes image generation tool via a helper script so we stay inside
        # this python process by shelling out a helper that prints the path.
        out = _call_image_generate(prompt)
        if out and Path(out).exists():
            shutil.copy2(out, p)
            print(f"  + scene_{s.id:03d} -> {p}")
        else:
            # fallback: write a placeholder so the pipeline keeps progressing
            _placeholder_image(p, s.title)
            print(f"  ! scene_{s.id:03d} placeholder generated at {p}")



def cmd_narration(ep: Episode, voice: str = "alloy"):
    if not ep.scenes:
        if not ep.load_scenes():
            raise SystemExit("No scenes found. Run storyboard first.")

    # Build one narration file per scene, and one combined episode track.
    combined = VOICES_DIR / f"{ep.name}_narration.wav"
    print(f"[narration] generating voiceover -> {combined}")
    pieces = []
    for s in ep.scenes:
        p = ep.dir / f"scene_{s.id:03d}_narration.wav"
        text = s.narration.strip()
        if not text:
            continue
        out = _call_tts(text, voice=voice, out_path=p)
        if out and Path(out).exists():
            pieces.append((s.id, Path(out)))
            continue
        # fallback: write a placeholder audio so concatenation still works
        _placeholder_audio(p, seconds=5, freq=220)
        pieces.append((s.id, p))

    if not pieces:
        print("[narration] nothing to narrate")
        return

    if not ensure_ffmpeg():
        print("[narration] skipping audio concat: ffmpeg not found")
        print(f"[narration] per-scene files kept in {ep.dir}")
        return

    # splice pieces back-to-back with a tiny crossfade
    list_file = ep.dir / "_narration_list.txt"
    with open(list_file, "w") as f:
        for _, p in pieces:
            f.write(f"file '{p.name}'\n")
    ok = _concat_ffmpeg_from_list(list_file, combined, ep.fps)
    if ok:
        print(f"[narration] combined -> {combined}")


def cmd_soundtrack(ep: Episode, mood: str = "dark cyberpunk electronic"):
    path = ASSETS_DIR / f"{ep.name}_soundtrack.wav"
    print(f"[soundtrack] generating soundtrack -> {path}")
    # TODO: replace with actual generation/orchestration
    _placeholder_audio(path, seconds=int(ep.duration), freq=110, label=mood)
    return path


def cmd_render(
    ep: Episode,
    narration_path: Optional[Path] = None,
    soundtrack_path: Optional[Path] = None,
    duration: Optional[float] = None,
):
    duration = float(duration or ep.duration)
    narration_path = Path(narration_path or VOICES_DIR / f"{ep.name}_narration.wav")
    soundtrack_path = Path(soundtrack_path or ASSETS_DIR / f"{ep.name}_soundtrack.wav")

    # 1. Build per-scene Ken Burns clips
    scene_dur = duration / max(len(ep.scenes), 1)
    print(f"[render] building {len(ep.scenes)} Ken Burns clips @ {scene_dur:.2f}s each")
    for s in ep.scenes:
        src = ep.scene_image(s.id)
        dst = ep.scene_clip(s.id)
        if dst.exists():
            dst.unlink()
        _kenburns_clip(src, dst, scene_dur, s.zoom_start, s.zoom_end, s.pan, ep.fps)

    # 2. Concat scene clips
    list_file = ep.dir / "concat.txt"
    with open(list_file, "w") as f:
        for s in ep.scenes:
            f.write(f"file '{ep.scene_clip(s.id).name}'\n")

    raw_video = ep.dir / "episode_raw.mp4"
    if not _concat_ffmpeg_from_list(list_file, raw_video, ep.fps):
        raise SystemExit("Failed to concatenate scene clips.")

    # 3. Mix audio
    video_only = raw_video
    final = ep.final_path

    if narration_path.exists() or soundtrack_path.exists():
        inputs = [str(video_only)]
        filter_complex = "[0:a]anull[va]"
        map_part = "-map 0:v -map [va]"

        if narration_path.exists() and soundtrack_path.exists():
            inputs += [str(narration_path), str(soundtrack_path)]
            filter_complex += ";[1:a]volume=1.0[nar];[2:a]volume=0.6[mus];[nar][mus]amix=inputs=2:duration=first:aweight=1[va]"
        elif narration_path.exists():
            inputs.append(str(narration_path))
            filter_complex += ";[1:a]volume=1.0[va]"
        else:
            inputs.append(str(soundtrack_path))
            filter_complex += ";[1:a]volume=0.6[va]"

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[va]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            str(final),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video_only),
            "-c", "copy",
            str(final),
        ]

    print(f"[render] finalizing episode -> {final}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[render] ffmpeg stderr:")
        print(res.stderr or "(empty)")
        raise SystemExit("FFmpeg render failed. Is ffmpeg installed?")

    print(f"DONE: {final}")
    print(f"Duration: {duration}s @ {ep.fps}fps")


# ============================================================================
# internal helpers
# ============================================================================
def _default_storyboard(title: str, count: int = 12) -> List[Scene]:
    scenes: List[Scene] = []
    for i in range(1, count + 1):
        scenes.append(
            Scene(
                id=i,
                slug=slugify(f"{title}-scene-{i}"),
                title=f"Scene {i:02d}",
                prompt=f"A cinematic cyberpunk scene #{i} related to '{title}'.",
                narration=f"In scene {i}, the story unfolds against neon rain and chrome reflections.",
                duration=5.0,
                zoom_start="1.0",
                zoom_end="1.15",
                pan="center",
            )
        )
    return scenes


def _placeholder_image(path: Path, label: str):
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (1920, 1080), (10, 8, 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle([60, 60, 1860, 1020], outline=(0, 255, 200), width=4)
        draw.text((80, 80), label, fill=(0, 255, 200))
        draw.text((80, 120), path.name, fill=(180, 180, 220))
        img.save(path)
    except Exception:
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        )


def _placeholder_audio(path: Path, seconds: int = 60, freq: int = 220, label: str = ""):
    try:
        import numpy as np
    except Exception:
        np = None  # type: ignore[assignment]
    try:
        import soundfile as sf
    except Exception:
        sf = None  # type: ignore[assignment]
    path.write_bytes(b"RIFF" + b"\x00" * 100)


def _call_image_generate(prompt: str):
    # Best effort: try invoking the hermes image tool when running inside the GUI.
    # This is intentionally left as a stub here; in actual Hermes GUI use, prefer
    # the `image_generate(...)` tool directly from the conversation.
    return None


def _call_tts(text: str, voice: str = "alloy", out_path: Path | None = None):
    # Best effort: try invoking the hermes TTS tool if available.
    return None


def _kenburns_clip(
    image: Path,
    output: Path,
    duration: float,
    zoom_start: str,
    zoom_end: str,
    pan: str,
    fps: int,
):
    if not ensure_ffmpeg():
        raise SystemExit(
            "FFmpeg is required for Ken Burns rendering. "
            "Install it first."
        )

    z0, z1 = map(float, [zoom_start, zoom_end])
    # simple pan
    if pan == "center":
        x0 = y0 = f"(ow-iw*{z0})/2"
        x1 = y1 = f"(ow-iw*{z1})/2"
    elif pan == "right":
        x0, x1 = f"(ow-iw*{z0})", f"(ow-iw*{z1})"
        y0 = y1 = f"(oh-ih*{z0})/2"
    else:
        x0 = y0 = x1 = y1 = f"(ow-iw*{z0})/2"

    vf = (
        f"zoompan=z='if(between(t,0,{duration}),"
        f"linear({z0},{z1},{duration}))':"
        f"x='{x0}+t*(({x1})-({x0}))/{duration}':"
        f"y='{y0}+t*(({y1})-({y0}))/{duration}':"
        f"d=1:s=1920x1080:fps={fps},format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1",
        "-i", str(image),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(output),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr or "(empty stderr)")
        raise SystemExit(f"Ken Burns render failed for {image}")


def _concat_ffmpeg_from_list(list_file: Path, output: Path, fps: int):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-r", str(fps),
        "-c", "copy",
        str(output),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr or "(empty)")
        return False
    return True


def _concat_ffmpeg(pairs: List[tuple], output: Path, fps: int):
    """Legacy concat helper used by narration splicer."""
    lf = output.parent / "_concat_list.txt"
    with open(lf, "w") as f:
        for _, p in pairs:
            f.write(f"file '{p}'\n")
    return _concat_ffmpeg_from_list(lf, output, fps)


# ============================================================================
# CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="atreyu episode pipeline")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init-episode")
    p_init.add_argument("--title", required=True)
    p_init.add_argument("--name")
    p_init.add_argument("--duration", type=float, default=60.0)

    p_sb = sub.add_parser("storyboard")
    p_sb.add_argument("--episode", required=True)
    p_sb.add_argument("--count", type=int, default=12)

    p_img = sub.add_parser("images")
    p_img.add_argument("--episode", required=True)
    p_img.add_argument("--prompt-suffix", default="")

    p_nt = sub.add_parser("narration")
    p_nt.add_argument("--episode", required=True)
    p_nt.add_argument("--voice", default="alloy")

    p_ms = sub.add_parser("soundtrack")
    p_ms.add_argument("--episode", required=True)
    p_ms.add_argument("--mood", default="dark cyberpunk electronic")

    p_re = sub.add_parser("render")
    p_re.add_argument("--episode", required=True)
    p_re.add_argument("--duration", type=float, default=None)
    p_re.add_argument("--narration", default=None)
    p_re.add_argument("--soundtrack", default=None)

    p_full = sub.add_parser("full")
    p_full.add_argument("--title", required=True)
    p_full.add_argument("--name")
    p_full.add_argument("--duration", type=float, default=60.0)
    p_full.add_argument("--voice", default="alloy")
    p_full.add_argument("--prompt-suffix", default="")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        raise SystemExit(1)

    if args.command == "init-episode":
        name = args.name or slugify(args.title)
        cmd_init_episode(name=name, title=args.title, duration=args.duration)
        return

    ep = Episode(name=args.episode)
    if not ep.meta_path.exists():
        raise SystemExit(f"episode metadata missing: {ep.meta_path}. Run init-episode first.")

    if args.command == "storyboard":
        cmd_storyboard(ep, count=args.count)
    elif args.command == "images":
        cmd_images(ep, prompt_suffix=args.prompt_suffix)
    elif args.command == "narration":
        cmd_narration(ep, voice=args.voice)
    elif args.command == "soundtrack":
        cmd_soundtrack(ep, mood=args.mood)
    elif args.command == "render":
        cmd_render(
            ep,
            narration_path=Path(args.narration) if args.narration else None,
            soundtrack_path=Path(args.soundtrack) if args.soundtrack else None,
            duration=args.duration,
        )
    elif args.command == "full":
        ep = cmd_init_episode(name=args.name or slugify(args.title), title=args.title, duration=args.duration)
        cmd_storyboard(ep, count=12)
        cmd_images(ep, prompt_suffix=args.prompt_suffix)
        cmd_narration(ep, voice=args.voice)
        cmd_soundtrack(ep, mood="dark cyberpunk electronic")
        cmd_render(ep, duration=args.duration)


if __name__ == "__main__":
    main()
