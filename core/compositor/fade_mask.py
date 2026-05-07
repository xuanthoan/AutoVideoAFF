"""Fade mask expression for the video overlap region."""
from __future__ import annotations


def vertical_alpha_mask(overlap_h: str = "overlap_h") -> str:
    return "format=yuva420p,geq=lum='p(X,Y)':a='255*(1-Y/{})'".format(overlap_h)
