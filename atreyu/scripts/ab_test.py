#!/usr/bin/env python3
"""
A/B Testing Framework for Computer Vision Campaign
===================================================

Generates preview frames and comparison reports for campaign variants.

Usage:
  python ab_test.py preview --variant-a neon-genesis --variant-b neon-genesis-variant-b
  python ab_test.py compare --variant-a neon-genesis --variant-b neon-genesis-variant-b
  python ab_test.py report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
STORYBOARDS_DIR = ROOT / "storyboards"
EPISODES_DIR = ROOT / "episodes"


@dataclass
class CampaignVariant:
    """Represents a campaign variant for A/B testing."""
    name: str
    title: str
    filepath: Path
    
    @classmethod
    def load(cls, name: str) -> Optional[CampaignVariant]:
        """Load a variant storyboard."""
        filepath = STORYBOARDS_DIR / f"{name}.json"
        if not filepath.exists():
            print(f"Error: Storyboard not found: {filepath}", file=sys.stderr)
            return None
        
        try:
            with open(filepath) as f:
                data = json.load(f)
            return cls(
                name=name,
                title=data.get("title", name),
                filepath=filepath
            )
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {filepath}", file=sys.stderr)
            return None
    
    def get_scenes(self) -> list:
        """Get scenes from this variant."""
        with open(self.filepath) as f:
            data = json.load(f)
        return data.get("scenes", [])
    
    def get_metadata(self) -> dict:
        """Get metadata about this variant."""
        with open(self.filepath) as f:
            data = json.load(f)
        return {
            "title": data.get("title", ""),
            "episode": data.get("episode", ""),
            "scene_count": data.get("scene_count", 0),
            "duration": data.get("duration", 0),
        }


def cmd_preview(args):
    """Generate preview information for A/B variants."""
    variant_a = CampaignVariant.load(args.variant_a)
    variant_b = CampaignVariant.load(args.variant_b)
    
    if not variant_a or not variant_b:
        return 1
    
    print(f"\n{'='*70}")
    print(f"A/B TEST PREVIEW: {args.variant_a} vs {args.variant_b}")
    print(f"{'='*70}\n")
    
    meta_a = variant_a.get_metadata()
    meta_b = variant_b.get_metadata()
    
    print(f"VARIANT A: {variant_a.title}")
    print(f"  Episodes: {meta_a['episode']}")
    print(f"  Duration: {meta_a['duration']}s")
    print(f"  Scenes: {meta_a['scene_count']}\n")
    
    print(f"VARIANT B: {variant_b.title}")
    print(f"  Episodes: {meta_b['episode']}")
    print(f"  Duration: {meta_b['duration']}s")
    print(f"  Scenes: {meta_b['scene_count']}\n")
    
    # Show first 3 scenes from each variant for comparison
    scenes_a = variant_a.get_scenes()[:3]
    scenes_b = variant_b.get_scenes()[:3]
    
    print(f"{'='*70}")
    print("SAMPLE SCENE COMPARISON (First 3 Scenes)")
    print(f"{'='*70}\n")
    
    for i, (scene_a, scene_b) in enumerate(zip(scenes_a, scenes_b), 1):
        print(f"--- SCENE {i} ---\n")
        
        print(f"Variant A Prompt:\n  {scene_a.get('prompt', 'N/A')}\n")
        print(f"Variant B Prompt:\n  {scene_b.get('prompt', 'N/A')}\n")
        
        print(f"Variant A Narration:\n  {scene_a.get('narration', 'N/A')}\n")
        print(f"Variant B Narration:\n  {scene_b.get('narration', 'N/A')}\n")
        
        print()
    
    print(f"✓ Preview generated. Ready to launch full render with 'render' command.")
    return 0


def cmd_compare(args):
    """Generate detailed comparison report."""
    variant_a = CampaignVariant.load(args.variant_a)
    variant_b = CampaignVariant.load(args.variant_b)
    
    if not variant_a or not variant_b:
        return 1
    
    print(f"\n{'='*70}")
    print(f"A/B COMPARISON REPORT: {args.variant_a} vs {args.variant_b}")
    print(f"{'='*70}\n")
    
    scenes_a = variant_a.get_scenes()
    scenes_b = variant_b.get_scenes()
    
    # Analyze visual differences
    print("VISUAL CHARACTERISTICS:\n")
    
    # Extract color palette hints from prompts
    def analyze_aesthetics(scenes):
        prompts = [s.get('prompt', '') for s in scenes]
        all_text = ' '.join(prompts).lower()
        
        characteristics = {
            'neon': 'neon' in all_text,
            'dark': 'dark' in all_text,
            'industrial': 'industrial' in all_text,
            'dystopian': 'dystopian' in all_text,
            'cyberpunk': 'cyberpunk' in all_text,
            'high_contrast': 'contrast' in all_text or 'stark' in all_text,
            'warm': 'warm' in all_text or 'red' in all_text or 'orange' in all_text,
            'cool': 'cool' in all_text or 'blue' in all_text or 'cyan' in all_text,
        }
        return characteristics
    
    char_a = analyze_aesthetics(scenes_a)
    char_b = analyze_aesthetics(scenes_b)
    
    print("Variant A Aesthetic Tags:")
    tags_a = [k.replace('_', ' ') for k, v in char_a.items() if v]
    print(f"  {', '.join(tags_a) if tags_a else 'Standard aesthetic'}\n")
    
    print("Variant B Aesthetic Tags:")
    tags_b = [k.replace('_', ' ') for k, v in char_b.items() if v]
    print(f"  {', '.join(tags_b) if tags_b else 'Standard aesthetic'}\n")
    
    # Calculate motion characteristics
    print("MOTION CHARACTERISTICS:\n")
    zoom_a = [float(s.get('zoom_end', 1.0)) for s in scenes_a]
    zoom_b = [float(s.get('zoom_end', 1.0)) for s in scenes_b]
    
    print(f"Variant A avg zoom end: {sum(zoom_a)/len(zoom_a):.2f}x")
    print(f"Variant B avg zoom end: {sum(zoom_b)/len(zoom_b):.2f}x\n")
    
    print(f"{'='*70}")
    print("RECOMMENDATIONS:\n")
    
    # Make recommendations based on characteristics
    if char_a['neon'] and not char_b['neon']:
        print("• Variant A emphasizes neon/bright aesthetics - better for trendy platforms")
        print("• Variant B emphasizes dark/industrial - better for serious/dramatic platforms\n")
    
    if char_a['cyberpunk'] and char_b['dystopian']:
        print("• Variant A feels more optimistic/future-forward (cyberpunk)")
        print("• Variant B feels darker/more ominous (dystopian)\n")
    
    if max(zoom_b) > max(zoom_a):
        print(f"• Variant B has more dramatic zoom effects ({max(zoom_b):.2f}x vs {max(zoom_a):.2f}x)")
        print("• More engaging for dynamic viewing experience\n")
    
    print(f"{'='*70}")
    return 0


def cmd_report(args):
    """Generate overall A/B test report."""
    print(f"\n{'='*70}")
    print("A/B TEST REPORT")
    print(f"{'='*70}\n")
    
    # List available variants
    storyboards = sorted(STORYBOARDS_DIR.glob("*.json"))
    variants = [s.stem for s in storyboards]
    
    print(f"Available campaign variants ({len(variants)}):\n")
    for variant in variants:
        filepath = STORYBOARDS_DIR / f"{variant}.json"
        with open(filepath) as f:
            data = json.load(f)
        title = data.get("title", variant)
        print(f"  • {variant:30s} -> {title}")
    
    print(f"\nTo run A/B tests:")
    print(f"  python ab_test.py preview --variant-a {variants[0]} --variant-b {variants[-1]}")
    print(f"  python ab_test.py compare --variant-a {variants[0]} --variant-b {variants[-1]}\n")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="A/B Testing Framework for Computer Vision Campaign",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ab_test.py preview --variant-a neon-genesis --variant-b neon-genesis-variant-b
  python ab_test.py compare --variant-a neon-genesis --variant-b neon-genesis-variant-b
  python ab_test.py report
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Generate A/B test preview")
    preview_parser.add_argument("--variant-a", required=True, help="Variant A storyboard name")
    preview_parser.add_argument("--variant-b", required=True, help="Variant B storyboard name")
    preview_parser.set_defaults(func=cmd_preview)
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Generate detailed comparison")
    compare_parser.add_argument("--variant-a", required=True, help="Variant A storyboard name")
    compare_parser.add_argument("--variant-b", required=True, help="Variant B storyboard name")
    compare_parser.set_defaults(func=cmd_compare)
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate A/B test report")
    report_parser.set_defaults(func=cmd_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
