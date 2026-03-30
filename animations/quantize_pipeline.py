"""
Quantization pipeline: vectors normalize, rotate, and snap to a grid.

Visual: many 2D arrows from origin.
  Step 1 - arrows grow/shrink onto the unit circle
  Step 2 - the whole constellation rotates
  Step 3 - a quantization grid appears, arrow tips snap to grid points
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1920
config.pixel_height = 1080

N_VECTORS = 40


class QuantizePipeline(Scene):
    def construct(self):
        setup_scene(self)

        # Axes (centered)
        ax = styled_axes(
            [-2.2, 2.2, 1], [-2.2, 2.2, 1],
            x_length=7, y_length=7,
        ).shift(LEFT * 0.3)

        circle = Circle(
            radius=ax.c2p(1, 0)[0] - ax.c2p(0, 0)[0],
            color=MUTED_DARK, stroke_width=1,
        ).move_to(ax.c2p(0, 0))

        self.play(Create(ax, run_time=0.4), Create(circle, run_time=0.4))

        # Generate random 2D vectors (not on unit circle)
        rng = np.random.default_rng(42)
        raw_vecs = rng.normal(0, 0.7, (N_VECTORS, 2))
        # Scale some up/down to show varying magnitudes
        scales = rng.uniform(0.5, 1.8, N_VECTORS)
        raw_vecs = raw_vecs * scales[:, None]

        # Create arrows
        arrows = VGroup()
        for v in raw_vecs:
            arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(v[0], v[1]), buff=0,
                color=PRIMARY, stroke_width=2.5,
                max_tip_length_to_length_ratio=0.12,
            )
            arrows.add(arrow)

        step_label = Text("Raw vectors (varying magnitudes)",
                          font_size=24, color=TEXT_COLOR)
        step_label.to_edge(UP, buff=0.7)

        self.play(
            FadeIn(step_label),
            LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.02),
            run_time=1.0,
        )
        self.wait(0.5)

        # ── Step 1: Normalize onto unit circle ──
        norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
        unit_vecs = raw_vecs / norms

        step1_label = Text("1. Normalize: project onto unit circle",
                           font_size=24, color=SECONDARY)
        step1_label.to_edge(UP, buff=0.7)

        norm_arrows = VGroup()
        for v in unit_vecs:
            arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(v[0], v[1]), buff=0,
                color=SECONDARY, stroke_width=2.5,
                max_tip_length_to_length_ratio=0.12,
            )
            norm_arrows.add(arrow)

        self.play(
            Transform(step_label, step1_label),
            *[Transform(a, b) for a, b in zip(arrows, norm_arrows)],
            circle.animate.set_color(SECONDARY).set_stroke(width=2),
            run_time=1.5,
        )
        self.wait(0.5)

        # ── Step 2: Rotate (spin the whole constellation) ──
        step2_label = Text("2. Rotate: Hadamard transform scrambles coordinates",
                           font_size=24, color=ACCENT)
        step2_label.to_edge(UP, buff=0.7)

        theta = 0.8  # radians
        R = np.array([[np.cos(theta), -np.sin(theta)],
                       [np.sin(theta),  np.cos(theta)]])
        rotated_vecs = (R @ unit_vecs.T).T

        rot_arrows = VGroup()
        for v in rotated_vecs:
            arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(v[0], v[1]), buff=0,
                color=ACCENT, stroke_width=2.5,
                max_tip_length_to_length_ratio=0.12,
            )
            rot_arrows.add(arrow)

        self.play(
            Transform(step_label, step2_label),
            *[Transform(a, b) for a, b in zip(arrows, rot_arrows)],
            run_time=1.5,
        )
        self.wait(0.5)

        # ── Step 3: Quantize (grid appears, tips snap) ──
        step3_label = Text("3. Quantize: snap each coordinate to nearest centroid",
                           font_size=24, color=TERTIARY)
        step3_label.to_edge(UP, buff=0.7)

        # Draw quantization grid (16 levels = 15 internal lines per axis)
        grid_vals = np.linspace(-1.3, 1.3, 16)
        grid_lines = VGroup()
        for gv in grid_vals:
            # Horizontal
            grid_lines.add(Line(
                ax.c2p(-1.5, gv), ax.c2p(1.5, gv),
                color=TERTIARY_DIM, stroke_width=0.5, stroke_opacity=0.3,
            ))
            # Vertical
            grid_lines.add(Line(
                ax.c2p(gv, -1.5), ax.c2p(gv, 1.5),
                color=TERTIARY_DIM, stroke_width=0.5, stroke_opacity=0.3,
            ))

        self.play(
            Transform(step_label, step3_label),
            LaggedStart(*[Create(l) for l in grid_lines], lag_ratio=0.005),
            run_time=0.8,
        )

        # Snap arrow tips to nearest grid intersection
        def snap_to_grid(v, grid):
            sx = grid[np.argmin(np.abs(grid - v[0]))]
            sy = grid[np.argmin(np.abs(grid - v[1]))]
            return np.array([sx, sy])

        snapped_vecs = np.array([snap_to_grid(v, grid_vals) for v in rotated_vecs])

        snap_arrows = VGroup()
        for v in snapped_vecs:
            arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(v[0], v[1]), buff=0,
                color=TERTIARY, stroke_width=2.5,
                max_tip_length_to_length_ratio=0.12,
            )
            snap_arrows.add(arrow)

        # Show dots at snapped positions for emphasis
        snap_dots = VGroup(*[
            Dot(ax.c2p(v[0], v[1]), radius=0.05, color=TERTIARY)
            for v in snapped_vecs
        ])

        self.play(
            *[Transform(a, b) for a, b in zip(arrows, snap_arrows)],
            FadeIn(snap_dots),
            run_time=1.2,
        )
        self.wait(0.3)

        # Summary
        summary = Text("Continuous vectors -> discrete 4-bit indices",
                        font_size=22, color=MUTED_LIGHT)
        summary.to_edge(DOWN, buff=0.7)
        self.play(FadeIn(summary, shift=UP * 0.2))
        self.wait(2)
