"""
Animated home hero: coordinate system metamorphosis.

A regular Cartesian grid of points smoothly transforms through stages:
  1. Uniform grid (structured data)
  2. Rotate/warp into polar layout (transformation)
  3. Points drift into semantic clusters (embeddings)
  4. Snap to a quantized grid (compression)

Each stage morphs smoothly into the next. Loops back to start.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1400
config.pixel_height = 400
config.frame_width = 14
config.frame_height = 4


class HomeHero(Scene):
    def construct(self):
        self.camera.background_color = "#1a1a1a"  # matches site $bg exactly

        rng = np.random.default_rng(42)

        # ── Stage 1: Cartesian grid ──
        nx, ny = 28, 8
        grid_pts = []
        for ix in range(nx):
            for iy in range(ny):
                x = (ix / (nx - 1) - 0.5) * 12
                y = (iy / (ny - 1) - 0.5) * 3
                grid_pts.append(np.array([x, y, 0]))
        grid_pts = np.array(grid_pts)
        n = len(grid_pts)

        # Assign colors by x-position (creates visual continuity through transforms)
        colors = []
        palette = [PRIMARY, SECONDARY, ACCENT, "#7db8c9", "#c9a0dc"]
        for pt in grid_pts:
            ci = int(((pt[0] + 6) / 12) * (len(palette) - 1))
            ci = max(0, min(len(palette) - 1, ci))
            colors.append(palette[ci])

        dots = VGroup(*[
            Dot(pt, radius=0.035, color=colors[i], fill_opacity=0.7)
            for i, pt in enumerate(grid_pts)
        ])

        # Faint grid lines
        grid_lines = VGroup()
        for iy in range(ny):
            pts_row = [grid_pts[ix * ny + iy] for ix in range(nx)]
            line = VMobject()
            line.set_points_as_corners(pts_row)
            line.set_stroke(MUTED_DARK, width=0.4, opacity=0.15)
            grid_lines.add(line)
        for ix in range(nx):
            pts_col = [grid_pts[ix * ny + iy] for iy in range(ny)]
            line = VMobject()
            line.set_points_as_corners(pts_col)
            line.set_stroke(MUTED_DARK, width=0.4, opacity=0.15)
            grid_lines.add(line)

        self.play(
            LaggedStart(*[FadeIn(d, scale=0.3) for d in dots], lag_ratio=0.003),
            FadeIn(grid_lines),
            run_time=1.0,
        )
        self.wait(0.5)

        # ── Stage 2: Warp into polar/radial layout ──
        polar_pts = []
        for pt in grid_pts:
            x, y = pt[0], pt[1]
            r = np.sqrt(x * x + y * y) * 0.35
            a = np.arctan2(y, x) + x * 0.08  # slight spiral
            px = r * np.cos(a)
            py = r * np.sin(a)
            polar_pts.append(np.array([px, py, 0]))
        polar_pts = np.array(polar_pts)

        polar_dots = VGroup(*[
            Dot(pt, radius=0.035, color=colors[i], fill_opacity=0.7)
            for i, pt in enumerate(polar_pts)
        ])

        # Polar grid lines (concentric rings + radial spokes)
        polar_lines = VGroup()
        for r in np.linspace(0.3, 2.0, 5):
            polar_lines.add(Arc(
                radius=r, start_angle=0, angle=TAU,
                color=MUTED_DARK, stroke_width=0.4, stroke_opacity=0.12,
            ))
        for a in np.linspace(0, TAU, 16, endpoint=False):
            polar_lines.add(Line(
                ORIGIN, 2.0 * np.array([np.cos(a), np.sin(a), 0]),
                color=MUTED_DARK, stroke_width=0.3, stroke_opacity=0.08,
            ))

        self.play(
            *[Transform(dots[i], polar_dots[i]) for i in range(n)],
            Transform(grid_lines, polar_lines),
            run_time=2.0,
            rate_func=smooth,
        )
        self.wait(0.5)

        # ── Stage 3: Drift into semantic clusters ──
        cluster_centers = [
            np.array([-3.5, 0.5, 0]),
            np.array([-1.5, -0.8, 0]),
            np.array([0.5, 0.7, 0]),
            np.array([2.5, -0.3, 0]),
            np.array([4.5, 0.4, 0]),
        ]
        cluster_pts = []
        for i, pt in enumerate(grid_pts):
            # Assign to nearest cluster based on original x
            ci = int(((pt[0] + 6) / 12) * (len(cluster_centers) - 1))
            ci = max(0, min(len(cluster_centers) - 1, ci))
            center = cluster_centers[ci]
            offset = rng.normal(0, 0.35, 3)
            offset[2] = 0
            cluster_pts.append(center + offset)
        cluster_pts = np.array(cluster_pts)

        cluster_dots = VGroup(*[
            Dot(pt, radius=0.04, color=colors[i], fill_opacity=0.8)
            for i, pt in enumerate(cluster_pts)
        ])

        # Cluster boundary circles
        cluster_lines = VGroup()
        for cc in cluster_centers:
            cluster_lines.add(Circle(
                radius=0.6, color=MUTED_DARK,
                stroke_width=0.5, stroke_opacity=0.15,
            ).move_to(cc))

        # Add faint connection lines within clusters
        for ci, cc in enumerate(cluster_centers):
            members = [j for j in range(n)
                       if np.linalg.norm(cluster_pts[j] - cc) < 0.8]
            for a_idx in members[:8]:
                for b_idx in members[:8]:
                    if a_idx < b_idx and np.linalg.norm(cluster_pts[a_idx] - cluster_pts[b_idx]) < 0.6:
                        cluster_lines.add(Line(
                            cluster_pts[a_idx], cluster_pts[b_idx],
                            color=colors[a_idx],
                            stroke_width=0.4, stroke_opacity=0.08,
                        ))

        self.play(
            *[Transform(dots[i], cluster_dots[i]) for i in range(n)],
            Transform(grid_lines, cluster_lines),
            run_time=2.0,
            rate_func=smooth,
        )
        self.wait(0.5)

        # ── Stage 4: Snap to quantized grid ──
        q_step = 0.22
        q_grid = np.arange(-5, 5, q_step)

        def snap(v):
            sx = q_grid[np.argmin(np.abs(q_grid - v[0]))]
            sy = q_grid[np.argmin(np.abs(q_grid - v[1]))]
            return np.array([sx, sy, 0])

        snapped_pts = np.array([snap(pt) for pt in cluster_pts])

        snapped_dots = VGroup(*[
            Dot(pt, radius=0.04, color=colors[i], fill_opacity=0.85)
            for i, pt in enumerate(snapped_pts)
        ])

        # Quantization grid (subtle)
        quant_lines = VGroup()
        for gv in q_grid:
            if abs(gv) < 5:
                quant_lines.add(Line(
                    np.array([gv, -1.8, 0]), np.array([gv, 1.8, 0]),
                    color=MUTED_DARK, stroke_width=0.3, stroke_opacity=0.06,
                ))
                quant_lines.add(Line(
                    np.array([-5.5, gv, 0]), np.array([5.5, gv, 0]),
                    color=MUTED_DARK, stroke_width=0.3, stroke_opacity=0.06,
                ))

        self.play(
            *[Transform(dots[i], snapped_dots[i]) for i in range(n)],
            Transform(grid_lines, quant_lines),
            run_time=1.5,
            rate_func=smooth,
        )
        self.wait(0.8)

        # ── Stage 5: Morph back to Cartesian grid (seamless loop) ──
        original_dots = VGroup(*[
            Dot(pt, radius=0.035, color=colors[i], fill_opacity=0.7)
            for i, pt in enumerate(grid_pts)
        ])

        # Rebuild original grid lines
        original_lines = VGroup()
        for iy in range(ny):
            pts_row = [grid_pts[ix * ny + iy] for ix in range(nx)]
            line = VMobject()
            line.set_points_as_corners(pts_row)
            line.set_stroke(MUTED_DARK, width=0.4, opacity=0.15)
            original_lines.add(line)
        for ix in range(nx):
            pts_col = [grid_pts[ix * ny + iy] for iy in range(ny)]
            line = VMobject()
            line.set_points_as_corners(pts_col)
            line.set_stroke(MUTED_DARK, width=0.4, opacity=0.15)
            original_lines.add(line)

        self.play(
            *[Transform(dots[i], original_dots[i]) for i in range(n)],
            Transform(grid_lines, original_lines),
            run_time=2.0,
            rate_func=smooth,
        )
        # No wait at end - last frame matches first frame for seamless loop
