"""
Open Graph preview image for social sharing.
1200x630 (standard OG image size).
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1200
config.pixel_height = 630
config.frame_width = 12
config.frame_height = 6.3


class OGImage(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a1a"

        # Subtle background dots (like compressed vectors)
        rng = np.random.default_rng(42)
        bg_dots = VGroup()
        for _ in range(80):
            x = rng.uniform(-5.5, 5.5)
            y = rng.uniform(-2.8, 2.8)
            dot = Dot(
                point=np.array([x, y, 0]),
                radius=0.04,
                color=SECONDARY,
                fill_opacity=rng.uniform(0.05, 0.15),
            )
            bg_dots.add(dot)
        self.add(bg_dots)

        # Title
        title = Text(
            "Building a Vector Database That\nNever Decompresses Your Vectors",
            font_size=38,
            color="#f0e8dc",
            line_spacing=1.3,
        )
        title.shift(UP * 0.6)

        # Subtitle
        sub = Text(
            "8x compression  ·  620x faster startup  ·  91.9% recall",
            font_size=20,
            color=ACCENT,
        )
        sub.next_to(title, DOWN, buff=0.5)

        # Author
        author = Text(
            "scotteveritt.github.io",
            font_size=16,
            color=MUTED,
        )
        author.to_edge(DOWN, buff=0.6)

        # Accent line
        line = Line(LEFT * 2, RIGHT * 2, color=ACCENT, stroke_width=2)
        line.next_to(sub, DOWN, buff=0.4)

        self.add(title, sub, author, line)
