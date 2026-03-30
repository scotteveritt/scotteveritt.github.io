"""
Hero image: embeddings in polar space, continuous to quantized.

Clusters of points arranged radially, with thin direction lines from
the origin showing the "vector" nature. Left half continuous, right
half snapped to polar grid (quantized angles and radii). Concentric
rings and radial spokes fade in on the quantized side.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1400
config.pixel_height = 480
config.frame_width = 14
config.frame_height = 4.8


class HeroImage(Scene):
    def construct(self):
        self.camera.background_color = BG

        rng = np.random.default_rng(7)
        origin = ORIGIN

        # Polar grid parameters (for quantized side)
        n_rings = 7
        n_spokes = 24
        max_r = 2.1
        ring_radii = np.linspace(max_r / n_rings, max_r, n_rings)
        spoke_angles = np.linspace(0, TAU, n_spokes, endpoint=False)

        # Draw polar grid (fades in from center-right)
        for r in ring_radii:
            arc = Arc(
                radius=r, start_angle=0, angle=TAU,
                arc_center=origin,
                color=MUTED_DARK, stroke_width=0.5,
                stroke_opacity=0.1,
            )
            self.add(arc)

        for a in spoke_angles:
            end = origin + max_r * np.array([np.cos(a), np.sin(a), 0])
            line = Line(
                origin, end,
                color=MUTED_DARK, stroke_width=0.3,
                stroke_opacity=0.07,
            )
            self.add(line)

        # Cluster definitions (angle-centered, spread in angle and radius)
        cluster_defs = [
            {"angle": 0.4,   "radius": 1.4, "color": PRIMARY,   "n": 18, "a_spread": 0.18, "r_spread": 0.25},
            {"angle": 1.1,   "radius": 0.9, "color": PRIMARY,   "n": 14, "a_spread": 0.15, "r_spread": 0.20},
            {"angle": 1.9,   "radius": 1.6, "color": SECONDARY, "n": 16, "a_spread": 0.14, "r_spread": 0.22},
            {"angle": 2.7,   "radius": 1.1, "color": SECONDARY, "n": 15, "a_spread": 0.16, "r_spread": 0.18},
            {"angle": 3.5,   "radius": 1.5, "color": ACCENT,    "n": 17, "a_spread": 0.15, "r_spread": 0.24},
            {"angle": 4.2,   "radius": 0.8, "color": ACCENT,    "n": 12, "a_spread": 0.18, "r_spread": 0.15},
            {"angle": 5.0,   "radius": 1.7, "color": "#7db8c9", "n": 16, "a_spread": 0.13, "r_spread": 0.20},
            {"angle": 5.7,   "radius": 1.2, "color": "#c9a0dc", "n": 14, "a_spread": 0.16, "r_spread": 0.22},
            {"angle": 0.0,   "radius": 1.9, "color": PRIMARY,   "n": 10, "a_spread": 0.12, "r_spread": 0.18},
            {"angle": 3.0,   "radius": 1.9, "color": "#c9a0dc", "n": 11, "a_spread": 0.14, "r_spread": 0.16},
        ]

        def snap_polar(angle, radius):
            """Snap to nearest polar grid intersection."""
            sa = spoke_angles[np.argmin(np.abs(spoke_angles - (angle % TAU)))]
            sr = ring_radii[np.argmin(np.abs(ring_radii - radius))]
            return sa, sr

        # Blend zone: angles near PI (left=continuous, right=quantized)
        # Use the x-coordinate of the point to determine blend
        blend_left = -1.5
        blend_right = 1.5

        for cdef in cluster_defs:
            ca, cr_center = cdef["angle"], cdef["radius"]
            color = cdef["color"]

            for _ in range(cdef["n"]):
                a = ca + rng.normal(0, cdef["a_spread"])
                r = cr_center + rng.normal(0, cdef["r_spread"])
                r = np.clip(r, 0.2, max_r)

                # Cartesian position (continuous)
                cx = r * np.cos(a)
                cy = r * np.sin(a)

                # Determine blend factor based on x position
                if cx < blend_left:
                    t = 0.0
                elif cx > blend_right:
                    t = 1.0
                else:
                    t = (cx - blend_left) / (blend_right - blend_left)
                    t = t * t * (3 - 2 * t)  # smoothstep

                # Snapped position
                sa, sr = snap_polar(a, r)
                sx = sr * np.cos(sa)
                sy = sr * np.sin(sa)

                # Blended final position
                fx = cx + (sx - cx) * t
                fy = cy + (sy - cy) * t

                # Direction line from origin (the "vector" flavor)
                line_opacity = rng.uniform(0.06, 0.18)
                direction_line = Line(
                    origin,
                    np.array([fx, fy, 0]),
                    color=color,
                    stroke_width=0.6,
                    stroke_opacity=line_opacity,
                )
                self.add(direction_line)

                # Glow + dot
                dot_opacity = rng.uniform(0.55, 0.95)
                dot_r = rng.uniform(0.025, 0.045)

                glow = Dot(
                    np.array([fx, fy, 0]),
                    radius=dot_r * 3.5,
                    color=color,
                    fill_opacity=dot_opacity * 0.07,
                )
                dot = Dot(
                    np.array([fx, fy, 0]),
                    radius=dot_r,
                    color=color,
                    fill_opacity=dot_opacity,
                )
                self.add(glow, dot)

        # Small bright dot at origin
        origin_dot = Dot(origin, radius=0.04, color=TEXT_COLOR, fill_opacity=0.6)
        origin_glow = Dot(origin, radius=0.15, color=TEXT_COLOR, fill_opacity=0.05)
        self.add(origin_glow, origin_dot)
