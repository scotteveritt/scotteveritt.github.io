"""
Cover image for cross-platform use (Dev.to, Hashnode, OG cards).
1600x840 - fits Hashnode's cover ratio without stretching.
Same polar vector motif but composed for this aspect ratio.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1600
config.pixel_height = 840
config.frame_width = 12
config.frame_height = 6.3


class CoverImage(Scene):
    def construct(self):
        self.camera.background_color = BG

        rng = np.random.default_rng(7)
        origin = ORIGIN

        # Polar grid
        max_r = 2.6
        for r in np.linspace(0.5, max_r, 6):
            self.add(Arc(
                radius=r, start_angle=0, angle=TAU,
                arc_center=origin,
                color=MUTED_DARK, stroke_width=0.4, stroke_opacity=0.1,
            ))
        for a in np.linspace(0, TAU, 20, endpoint=False):
            self.add(Line(
                origin, origin + max_r * np.array([np.cos(a), np.sin(a), 0]),
                color=MUTED_DARK, stroke_width=0.3, stroke_opacity=0.06,
            ))

        # Clusters
        cluster_defs = [
            {"angle": 0.4,   "radius": 1.6, "color": PRIMARY,   "n": 20, "a_spread": 0.18, "r_spread": 0.28},
            {"angle": 1.1,   "radius": 1.0, "color": PRIMARY,   "n": 16, "a_spread": 0.15, "r_spread": 0.22},
            {"angle": 1.9,   "radius": 2.0, "color": SECONDARY, "n": 18, "a_spread": 0.14, "r_spread": 0.25},
            {"angle": 2.7,   "radius": 1.3, "color": SECONDARY, "n": 14, "a_spread": 0.16, "r_spread": 0.20},
            {"angle": 3.5,   "radius": 1.8, "color": ACCENT,    "n": 18, "a_spread": 0.15, "r_spread": 0.26},
            {"angle": 4.2,   "radius": 0.9, "color": ACCENT,    "n": 12, "a_spread": 0.18, "r_spread": 0.16},
            {"angle": 5.0,   "radius": 2.1, "color": "#7db8c9", "n": 16, "a_spread": 0.13, "r_spread": 0.22},
            {"angle": 5.7,   "radius": 1.4, "color": "#c9a0dc", "n": 14, "a_spread": 0.16, "r_spread": 0.24},
            {"angle": 0.0,   "radius": 2.3, "color": PRIMARY,   "n": 10, "a_spread": 0.12, "r_spread": 0.20},
            {"angle": 3.0,   "radius": 2.2, "color": "#c9a0dc", "n": 11, "a_spread": 0.14, "r_spread": 0.18},
        ]

        grid_step = 0.32
        grid_range_r = np.arange(grid_step, max_r + grid_step, grid_step)
        spoke_angles = np.linspace(0, TAU, 24, endpoint=False)

        def snap_polar(angle, radius):
            sa = spoke_angles[np.argmin(np.abs(spoke_angles - (angle % TAU)))]
            sr = grid_range_r[np.argmin(np.abs(grid_range_r - radius))]
            return sa, sr

        blend_left = -1.0
        blend_right = 1.5

        for cdef in cluster_defs:
            ca, cr_center = cdef["angle"], cdef["radius"]
            color = cdef["color"]

            for _ in range(cdef["n"]):
                a = ca + rng.normal(0, cdef["a_spread"])
                r = cr_center + rng.normal(0, cdef["r_spread"])
                r = np.clip(r, 0.25, max_r)

                cx = r * np.cos(a)
                cy = r * np.sin(a)

                if cx < blend_left:
                    t = 0.0
                elif cx > blend_right:
                    t = 1.0
                else:
                    t = (cx - blend_left) / (blend_right - blend_left)
                    t = t * t * (3 - 2 * t)

                sa, sr = snap_polar(a, r)
                sx = sr * np.cos(sa)
                sy = sr * np.sin(sa)

                fx = cx + (sx - cx) * t
                fy = cy + (sy - cy) * t

                line_opacity = rng.uniform(0.05, 0.15)
                self.add(Line(
                    origin, np.array([fx, fy, 0]),
                    color=color, stroke_width=0.5, stroke_opacity=line_opacity,
                ))

                dot_opacity = rng.uniform(0.5, 0.95)
                dot_r = rng.uniform(0.025, 0.05)
                self.add(Dot(np.array([fx, fy, 0]), radius=dot_r * 3.5, color=color, fill_opacity=dot_opacity * 0.07))
                self.add(Dot(np.array([fx, fy, 0]), radius=dot_r, color=color, fill_opacity=dot_opacity))

        self.add(Dot(origin, radius=0.15, color=TEXT_COLOR, fill_opacity=0.05))
        self.add(Dot(origin, radius=0.04, color=TEXT_COLOR, fill_opacity=0.6))
