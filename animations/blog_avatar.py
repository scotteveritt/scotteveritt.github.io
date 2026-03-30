"""
Blog avatar for Hashnode / Dev.to profiles.
400x400. The polar vector motif from the hero image, condensed.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 400
config.pixel_height = 400
config.frame_width = 4
config.frame_height = 4


class BlogAvatar(Scene):
    def construct(self):
        self.camera.background_color = BG

        rng = np.random.default_rng(7)
        origin = ORIGIN

        # Subtle polar grid
        max_r = 1.6
        for r in np.linspace(0.4, max_r, 5):
            self.add(Arc(
                radius=r, start_angle=0, angle=TAU,
                arc_center=origin,
                color=MUTED_DARK, stroke_width=0.4, stroke_opacity=0.12,
            ))
        for a in np.linspace(0, TAU, 16, endpoint=False):
            self.add(Line(
                origin, origin + max_r * np.array([np.cos(a), np.sin(a), 0]),
                color=MUTED_DARK, stroke_width=0.3, stroke_opacity=0.08,
            ))

        # Vectors radiating out with dots at tips
        n = 24
        angles = np.linspace(0, TAU, n, endpoint=False) + rng.uniform(-0.1, 0.1, n)
        radii = rng.uniform(0.5, max_r * 0.9, n)
        colors = [PRIMARY, SECONDARY, ACCENT, "#7db8c9", "#c9a0dc"]

        for i, (a, r) in enumerate(zip(angles, radii)):
            color = colors[i % len(colors)]
            tip = origin + r * np.array([np.cos(a), np.sin(a), 0])

            # Direction line
            self.add(Line(
                origin, tip,
                color=color, stroke_width=0.5,
                stroke_opacity=rng.uniform(0.08, 0.2),
            ))

            # Glow + dot
            self.add(Dot(tip, radius=0.07, color=color, fill_opacity=0.08))
            self.add(Dot(tip, radius=0.03, color=color, fill_opacity=rng.uniform(0.5, 0.95)))

        # Center dot
        self.add(Dot(origin, radius=0.12, color=TEXT_COLOR, fill_opacity=0.06))
        self.add(Dot(origin, radius=0.035, color=TEXT_COLOR, fill_opacity=0.7))
