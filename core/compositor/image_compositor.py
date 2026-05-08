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
        image_percent = self._clamp_percent(settings.image_height_percent, 20, 60)
        image_h = self._even_pixels(video_height * image_percent / 100)
        overlap_percent = min(max(settings.overlap_percent, 0), min(20, image_percent))
        overlap_h = 0 if overlap_percent <= 0 else min(self._even_pixels(video_height * overlap_percent / 100), image_h)
        visible_video_total = video_height - (image_h - overlap_h)
        offset_y = -(video_height - visible_video_total)
        image_top = video_height - image_h
        fade_start = image_top
        source_y = max(0, min(video_height - overlap_h, fade_start - offset_y))
        canvas_size = f"{video_width}x{video_height}"
        focus = {"top": "0", "center": "(ih-oh)/2", "bottom": "ih-oh"}[settings.crop_focus]
        prefix = (
            f"[{image_label}]scale=w=iw*max({video_width}/iw\\,{image_h}/ih):h=ih*max({video_width}/iw\\,{image_h}/ih),"
            f"crop=w={video_width}:h={image_h}:x=(iw-{video_width})/2:y={focus}[bg];"
        )
        if overlap_h <= 0:
            return (
                prefix
                + f"color=c=black@0:s={canvas_size}:d=1[canvas];"
                + f"[{video_label}]setpts=PTS-STARTPTS[mainv];"
                + f"[canvas][bg]overlay=x=0:y={image_top}[base];"
                + f"[base][mainv]overlay=x=0:y={offset_y}[{out}]"
            ), out

        # The source video remains one continuous shifted layer. The fade strip is sampled from
        # the viewport overlap region mapped back to source coordinates, then composited above the image.
        chain = (
            prefix
            + f"[{video_label}]setpts=PTS-STARTPTS,split=2[mainv][fade_src];"
            + f"[fade_src]crop=w={video_width}:h={overlap_h}:x=0:y={source_y},"
            + f"format=yuva420p,geq=lum='p(X,Y)':a='255*(1-(Y/{overlap_h}))'[fade];"
            + f"color=c=black@0:s={canvas_size}:d=1[canvas];"
            + f"[canvas][bg]overlay=x=0:y={image_top}[base];"
            + f"[base][mainv]overlay=x=0:y={offset_y}[shifted];"
            + f"[shifted][fade]overlay=x=0:y={fade_start}[{out}]"
        )
        return chain, out

    @staticmethod
    def _even_pixels(value: float) -> int:
        return max(2, int(value) // 2 * 2)

    @staticmethod
    def _clamp_percent(value: float, minimum: float, maximum: float) -> float:
        return min(max(float(value), minimum), maximum)
