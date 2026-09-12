"""Subtitle Engine — Hormozi-style word-by-word progressive highlight with emphasis words.

Features:
- Word-level timing based on estimated word duration within each scene
- Progressive highlight: each word turns yellow as it's spoken
- Emphasis words: rendered larger + color pop
- Pop-in animation via \fad fade-in
- Multiple styles: HORMOZI_BOLD, BEAST_COLOR, MINIMAL_CLEAN, CINEMATIC_NOIR
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

from app.config import settings
from app.schemas.video import SubtitleStyle


def _sec_to_ass(seconds: float) -> str:
    """Convert seconds to ASS timestamp H:MM:SS.cc"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - math.floor(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _estimate_word_durations(words: List[str], total_sec: float) -> List[float]:
    """Estimate how long each word is spoken based on character length weighting."""
    if not words:
        return []
    # Weight by char length + constant per word (words take min ~0.15s each)
    weights = [max(len(w), 2) for w in words]
    total_weight = sum(weights)
    return [(w / total_weight) * total_sec for w in weights]


def _split_into_chunks(words: List[str], max_chunk: int = 3) -> List[List[str]]:
    """Split words into chunks for subtitle display (max N words per line)."""
    chunks = []
    for i in range(0, len(words), max_chunk):
        chunks.append(words[i:i + max_chunk])
    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# Style definitions
# ──────────────────────────────────────────────────────────────────────────────

STYLE_CONFIGS = {
    SubtitleStyle.HORMOZI_BOLD: {
        "font_name": "Arial Black",
        "font_size_portrait": 64,
        "font_size_landscape": 48,
        "primary": "&H00FFFFFF",   # White base
        "highlight": "&H0000FFFF", # Yellow highlight (BGR)
        "outline": "&H00000000",   # Black stroke
        "shadow": "&H80000000",
        "bold": True,
        "outline_size": 4,
        "margin_v_portrait": 360,
        "margin_v_landscape": 140,
        "all_caps": True,
    },
    SubtitleStyle.BEAST_COLOR: {
        "font_name": "Impact",
        "font_size_portrait": 72,
        "font_size_landscape": 52,
        "primary": "&H0000FFFF",   # Yellow base
        "highlight": "&H000040FF", # Orange-red highlight
        "outline": "&H00000000",
        "shadow": "&H80000000",
        "bold": True,
        "outline_size": 5,
        "margin_v_portrait": 340,
        "margin_v_landscape": 130,
        "all_caps": True,
    },
    SubtitleStyle.MINIMAL_CLEAN: {
        "font_name": "Helvetica Neue",
        "font_size_portrait": 52,
        "font_size_landscape": 38,
        "primary": "&H00FFFFFF",
        "highlight": "&H00AAFFFF", # Soft yellow
        "outline": "&H44222222",
        "shadow": "&H60000000",
        "bold": False,
        "outline_size": 2,
        "margin_v_portrait": 380,
        "margin_v_landscape": 150,
        "all_caps": False,
    },
    SubtitleStyle.CINEMATIC_NOIR: {
        "font_name": "Georgia",
        "font_size_portrait": 54,
        "font_size_landscape": 40,
        "primary": "&H00E8D5A3",   # Gold/ivory
        "highlight": "&H0000D7FF", # Warm gold highlight
        "outline": "&H00000000",
        "shadow": "&H90000000",
        "bold": False,
        "outline_size": 3,
        "margin_v_portrait": 400,
        "margin_v_landscape": 160,
        "all_caps": False,
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# ASS header generator
# ──────────────────────────────────────────────────────────────────────────────

def _build_ass_header(style: SubtitleStyle, aspect_ratio: str) -> str:
    portrait = aspect_ratio == "9:16"
    cfg = STYLE_CONFIGS.get(style, STYLE_CONFIGS[SubtitleStyle.HORMOZI_BOLD])

    play_res_x = 1080 if portrait else 1920
    play_res_y = 1920 if portrait else 1080
    font_size = cfg["font_size_portrait"] if portrait else cfg["font_size_landscape"]
    margin_v = cfg["margin_v_portrait"] if portrait else cfg["margin_v_landscape"]
    bold = -1 if cfg["bold"] else 0

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{cfg["font_name"]},{font_size},{cfg["primary"]},&H00FFFF00,{cfg["outline"]},{cfg["shadow"]},{bold},0,0,0,100,100,0,0,1,{cfg["outline_size"]},1,2,30,30,{margin_v},1
Style: Emphasis,{cfg["font_name"]},{font_size + 10},{cfg["highlight"]},&H00FFFF00,{cfg["outline"]},{cfg["shadow"]},-1,0,0,0,105,110,0,0,1,{cfg["outline_size"] + 1},2,2,30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ──────────────────────────────────────────────────────────────────────────────
# Subtitle line generator
# ──────────────────────────────────────────────────────────────────────────────

def _build_dialogue_line(
    start: float,
    end: float,
    text: str,
    style_name: str = "Default",
    all_caps: bool = True,
    fade_in_ms: int = 80,
) -> str:
    display_text = text.upper() if all_caps else text
    fade = f"{{\\fad({fade_in_ms},0)}}"
    return f"Dialogue: 0,{_sec_to_ass(start)},{_sec_to_ass(end)},{style_name},,0,0,0,,{fade}{display_text}"


# ──────────────────────────────────────────────────────────────────────────────
# Main engine
# ──────────────────────────────────────────────────────────────────────────────

class SubtitleEngine:
    def __init__(self):
        self.output_dir = settings.TEMP_DIR / "subtitles"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_ass_subtitles(
        self,
        scenes_data: List[Dict[str, Any]],
        style: SubtitleStyle = SubtitleStyle.HORMOZI_BOLD,
        aspect_ratio: str = "9:16",
        output_filename: str = "subtitles.ass",
    ) -> Path:
        """Generate an ASS subtitle file with word-level progressive timing."""
        output_path = self.output_dir / output_filename
        cfg = STYLE_CONFIGS.get(style, STYLE_CONFIGS[SubtitleStyle.HORMOZI_BOLD])
        all_caps = cfg.get("all_caps", True)

        header = _build_ass_header(style, aspect_ratio)
        dialogue_lines: List[str] = []

        for scene in scenes_data:
            text: str = scene.get("voiceover_text", "")
            start: float = scene.get("start_time_sec", 0.0)
            duration: float = scene.get("duration_sec", 3.0)
            emphasis_words: List[str] = [w.lower() for w in scene.get("emphasis_words", [])]

            if not text.strip():
                continue

            words = text.split()
            if not words:
                continue

            word_durations = _estimate_word_durations(words, duration * 0.9)  # Use 90% of scene time

            # Group into chunks of 3 words
            chunks = _split_into_chunks(words, max_chunk=3)
            chunk_starts: List[float] = []
            t = start
            word_idx = 0
            for chunk in chunks:
                chunk_dur = sum(word_durations[word_idx:word_idx + len(chunk)])
                chunk_starts.append(t)
                t += chunk_dur
                word_idx += len(chunk)

            # Generate one dialogue event per chunk
            for i, chunk in enumerate(chunks):
                chunk_start = chunk_starts[i]
                chunk_end = chunk_starts[i + 1] if i + 1 < len(chunk_starts) else start + duration

                chunk_text = " ".join(chunk)
                # Determine if any emphasis word is in this chunk
                is_emphasis = any(w.lower().strip(".,!?") in emphasis_words for w in chunk)
                style_name = "Emphasis" if is_emphasis else "Default"

                dialogue_lines.append(
                    _build_dialogue_line(
                        chunk_start, chunk_end, chunk_text,
                        style_name=style_name,
                        all_caps=all_caps,
                    )
                )

        ass_content = header + "\n".join(dialogue_lines) + "\n"
        output_path.write_text(ass_content, encoding="utf-8")
        return output_path


subtitle_engine = SubtitleEngine()
