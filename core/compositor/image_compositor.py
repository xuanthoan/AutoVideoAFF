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

    def build_filter(self, video_label: str, image_label: str, settings: ImageCompositeSettings) -> tuple[str, str]:
        out = "composited_v"
        image_h = f"trunc(ih*{settings.image_height_percent / 100:.4f}/2)*2"
        overlap = f"trunc(ih*{settings.overlap_percent / 100:.4f}/2)*2"
        focus = {"top": "0", "center": "(ih-oh)/2", "bottom": "ih-oh"}[settings.crop_focus]
        # The source video is shifted up first. The fade is generated from the visible video overlap,
        # then overlaid on top of the full-width image region at the bottom of the frame.
        chain = (
            f"[{image_label}]scale=w=iw*max(W/iw\\,{image_h}/ih):h=ih*max(W/iw\\,{image_h}/ih),"
            f"crop=w=W:h={image_h}:x=(iw-W)/2:y={focus}[bg];"
            f"[{video_label}]setpts=PTS-STARTPTS,split=2[mainv][fade_src];"
            f"[fade_src]crop=w=iw:h={overlap}:x=0:y=ih-{image_h}-{overlap},"
            f"format=yuva420p,geq=lum='p(X,Y)':a='255*(1-Y/{overlap})'[fade];"
            f"color=c=black@0:s=WxH:d=1[canvas];"
            f"[canvas][bg]overlay=x=0:y=H-{image_h}[base];"
            f"[base][mainv]overlay=x=0:y=-{image_h}+{overlap}[shifted];"
            f"[shifted][fade]overlay=x=0:y=H-{image_h}-{overlap}[{out}]"
        )
        return chain, out
