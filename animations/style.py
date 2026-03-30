"""
Shared style constants and helpers for tqdb blog animations.

Design: dark background, clean minimal aesthetic.
Color language:
  - ACCENT (warm gold)  : highlights, key results, "the answer"
  - PRIMARY (blue)      : query vectors, input data, first-stage
  - SECONDARY (teal)    : transformations, rotations, intermediate
  - TERTIARY (red)      : stored data, compressed, hot-path
  - MUTED (grey)        : labels, axes, secondary text
"""

from manim import *

# ── Background ──────────────────────────────────────────────────
BG = "#0D0D0D"

# ── Palette ─────────────────────────────────────────────────────
ACCENT       = "#E8A838"   # warm gold — highlights, key numbers
ACCENT_DIM   = "#A67A2E"   # muted gold — secondary highlights
PRIMARY      = "#5B9BD5"   # blue — queries, input
PRIMARY_DIM  = "#2D5F8A"   # dark blue — fills, outlines
SECONDARY    = "#5ECDA0"   # teal — rotation, transforms
SECONDARY_DIM= "#2E7A5A"   # dark teal
TERTIARY     = "#E8605D"   # red — stored vectors, compressed
TERTIARY_DIM = "#8A3532"   # dark red
MUTED        = "#888888"   # grey — labels, axes
MUTED_LIGHT  = "#BBBBBB"   # light grey
MUTED_DARK   = "#444444"   # dark grey
TEXT_COLOR   = "#E0E0E0"   # off-white for body text

# ── Typography ──────────────────────────────────────────────────
TITLE_SIZE   = 40
HEADING_SIZE = 28
BODY_SIZE    = 22
LABEL_SIZE   = 18
SMALL_SIZE   = 14

# ── Stroke / geometry ──────────────────────────────────────────
AXIS_COLOR   = MUTED_DARK
AXIS_WIDTH   = 1.0
THIN_STROKE  = 1.0
MED_STROKE   = 2.0
THICK_STROKE = 3.0


def setup_scene(scene):
    """Standard scene initialization."""
    scene.camera.background_color = BG


def styled_axes(x_range, y_range, x_length=10, y_length=4, **kwargs):
    """Create axes matching our visual style."""
    return Axes(
        x_range=x_range,
        y_range=y_range,
        x_length=x_length,
        y_length=y_length,
        tips=False,
        axis_config={
            "color": AXIS_COLOR,
            "stroke_width": AXIS_WIDTH,
            "include_ticks": False,
        },
        **kwargs,
    )


def title_text(text, **kwargs):
    return Text(text, font_size=TITLE_SIZE, color=TEXT_COLOR, **kwargs)


def heading_text(text, color=TEXT_COLOR, **kwargs):
    return Text(text, font_size=HEADING_SIZE, color=color, **kwargs)


def body_text(text, color=MUTED_LIGHT, **kwargs):
    return Text(text, font_size=BODY_SIZE, color=color, **kwargs)


def label_text(text, color=MUTED, **kwargs):
    return Text(text, font_size=LABEL_SIZE, color=color, **kwargs)


def small_text(text, color=MUTED, **kwargs):
    return Text(text, font_size=SMALL_SIZE, color=color, **kwargs)


def value_to_color(value, min_val=0.0, max_val=1.0):
    """Map a signed value to blue (positive) or red (negative)."""
    alpha = min(abs(value) / max(abs(max_val), 1e-15), 1.0)
    if value >= 0:
        return interpolate_color(
            ManimColor(PRIMARY_DIM), ManimColor(PRIMARY), alpha
        )
    else:
        return interpolate_color(
            ManimColor(TERTIARY_DIM), ManimColor(TERTIARY), alpha
        )
