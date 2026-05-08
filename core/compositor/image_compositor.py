"""FFmpeg image compositor builder."""
from __future__ import annotations

from pathlib import Path
from random import Random

from models.project_state import ImageCompositeSettings


class ImageCompositor:
    def __init__(self) -> None:
        self.random = Random()

    @staticmethod
    def pick_image(pool: list[Path], salt: str) -> Path:
        if not pool:
            raise ValueError("image pool is empty")
        return sorted(pool, key=lambda p: p.as_posix())[hash(salt) % len(pool)]

    def build_filter(
        self,
        video_label: str,
        image_label: str,
        settings: ImageCompositeSettings,
        video_width: int,
        video_height: int,
    ) -> tuple[str, str]:
        out = "composited_v"
        image_h = self._even_pixels(video_height * settings.image_height_percent / 100)
        overlap_h = min(self._even_pixels(video_height * settings.overlap_percent / 100), image_h)
        canvas_size = f"{video_width}x{video_height}"
        focus = {"top": "0", "center": "(ih-oh)/2", "bottom": "ih-oh"}[settings.crop_focus]
        # The source video is shifted up first. The fade is generated from the visible video overlap,
        # then overlaid on top of the full-width image region at the bottom of the frame.
        chain = (
            f"[{image_label}]scale=w=iw*max({video_width}/iw\\,{image_h}/ih):h=ih*max({video_width}/iw\\,{image_h}/ih),"
            f"crop=w={video_width}:h={image_h}:x=(iw-{video_width})/2:y={focus}[bg];"
            f"[{video_label}]setpts=PTS-STARTPTS,split=2[mainv][fade_src];"
            f"[fade_src]crop=w=iw:h={overlap_h}:x=0:y=ih-{image_h}-{overlap_h},"
            f"format=yuva420p,geq=lum='p(X,Y)':a='255*(1-(Y/{overlap_h}))'[fade];"
            f"color=c=black@0:s={canvas_size}:d=1[canvas];"
            f"[canvas][bg]overlay=x=0:y=H-{image_h}[base];"
            f"[base][mainv]overlay=x=0:y=-{image_h}+{overlap_h}[shifted];"
            f"[shifted][fade]overlay=x=0:y=H-{image_h}-{overlap_h}[{out}]"
        )
        return chain, out

    @staticmethod
    def _even_pixels(value: float) -> int:
        return max(2, int(value) // 2 * 2)
