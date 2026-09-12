"""Dynamic viral subtitle generator (Alex Hormozi / MrBeast style) generating ASS files."""

import math
from pathlib import Path
from typing import List, Dict, Any
from app.config import settings
from app.schemas.video import SubtitleStyle


def _sec_to_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        secs += 1
        cs = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


class SubtitleEngine:
    def __init__(self):
        self.output_dir = settings.TEMP_DIR / "subtitles"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_ass_subtitles(
        self,
        scenes_data: List[Dict[str, Any]],
        style: SubtitleStyle = SubtitleStyle.HORMOZI_BOLD,
        aspect_ratio: str = "9:16",
        output_filename: str = "subtitles.ass"
    ) -> Path:
        """Create an ASS subtitle file with viral styling and word-chunk timing."""
        output_path = self.output_dir / output_filename

        play_res_x = 1080 if aspect_ratio == "9:16" else 1920
        play_res_y = 1920 if aspect_ratio == "9:16" else 1080
        font_size = 56 if aspect_ratio == "9:16" else 42
        margin_v = 380 if aspect_ratio == "9:16" else 140

        # Primary style colors in ASS BGR format
        # White text, bold yellow accent, black border
        if style == SubtitleStyle.HORMOZI_BOLD:
            primary_colour = "&H00FFFFFF"  # White
            outline_colour = "&H00000000"  # Solid Black
            back_colour = "&H80000000"     # Semi-transparent shadow
            font_name = "Arial Black"
        elif style == SubtitleStyle.BEAST_COLOR:
            primary_colour = "&H0000FFFF"  # Vibrant Yellow
            outline_colour = "&H00000000"
            back_colour = "&H80000000"
            font_name = "Impact"
        else:
            primary_colour = "&H00FFFFFF"
            outline_colour = "&H00222222"
            back_colour = "&H80000000"
            font_name = "Arial"

        header = f"""[Script Info]
Title: CineShorts Dynamic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralMain,{font_name},{font_size},{primary_colour},&H000000FF,{outline_colour},{back_colour},-1,0,0,0,100,100,1,0,1,5,3,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        dialogue_lines = []
        
        for sc in scenes_data:
            start_sec = sc.get("start_time_sec", 0.0)
            end_sec = sc.get("end_time_sec", start_sec + sc.get("duration_sec", 4.0))
            text = sc.get("voiceover_text", "")
            
            # Split scene voiceover into punchy 2-4 word rhythmic chunks
            words = text.split()
            if not words:
                continue

            chunk_size = 3
            num_chunks = math.ceil(len(words) / chunk_size)
            total_dur = end_sec - start_sec
            chunk_dur = total_dur / num_chunks

            for i in range(num_chunks):
                c_start = start_sec + (i * chunk_dur)
                c_end = min(end_sec, c_start + chunk_dur)
                chunk_words = words[i * chunk_size : (i + 1) * chunk_size]
                chunk_str = " ".join(chunk_words).upper()

                # Highlight the first word or emphasis word in vibrant yellow (&H0000FFFF)
                if len(chunk_words) > 1:
                    first_word = chunk_words[0].upper()
                    rest_words = " ".join(chunk_words[1:]).upper()
                    styled_text = f"{{\\c&H0000FFFF&}}{first_word}{{\\c{primary_colour}&}} {rest_words}"
                else:
                    styled_text = f"{{\\c&H0000FFFF&}}{chunk_str}"

                start_str = _sec_to_ass_time(c_start)
                end_str = _sec_to_ass_time(c_end)
                dialogue_lines.append(
                    f"Dialogue: 0,{start_str},{end_str},ViralMain,,0,0,0,,{styled_text}"
                )

        full_ass_content = header + "\n".join(dialogue_lines) + "\n"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_ass_content)

        return output_path

subtitle_engine = SubtitleEngine()
