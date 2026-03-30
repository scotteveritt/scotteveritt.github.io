"""
IVF partition pruning animation.

Vectors clustered in 2D. Query arrives, nearest partitions light up,
the rest fade out. Shows the 6.8x speedup visually.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1920
config.pixel_height = 1080

N_CLUSTERS = 12
PTS_PER = 25
N_PROBE = 3


class IVFPartitions(Scene):
    def construct(self):
        setup_scene(self)

        t = title_text("IVF Index: Partition Pruning")
        t.to_edge(UP, buff=0.45)
        self.play(FadeIn(t, shift=DOWN * 0.3), run_time=0.7)

        rng = np.random.default_rng(42)

        # Generate well-separated cluster centers
        centers = rng.uniform(-3.2, 3.2, (N_CLUSTERS, 2))
        for _ in range(15):
            for i in range(N_CLUSTERS):
                for j in range(i + 1, N_CLUSTERS):
                    diff = centers[i] - centers[j]
                    d = np.linalg.norm(diff)
                    if d < 1.6:
                        push = diff / (d + 0.01) * 0.25
                        centers[i] += push
                        centers[j] -= push

        # Points
        all_dots = VGroup()
        groups = []
        for ci in range(N_CLUSTERS):
            cx, cy = centers[ci]
            g = VGroup()
            for _ in range(PTS_PER):
                px = cx + rng.normal(0, 0.32)
                py = cy + rng.normal(0, 0.32)
                dot = Dot(
                    point=np.array([px * 0.65, py * 0.5 - 0.4, 0.0]),
                    radius=0.035,
                    color=MUTED,
                    fill_opacity=0.4,
                )
                g.add(dot)
                all_dots.add(dot)
            groups.append(g)

        # Cluster boundaries
        circles = VGroup()
        for ci in range(N_CLUSTERS):
            cx, cy = centers[ci]
            c = Circle(
                radius=0.48, color=MUTED_DARK,
                stroke_width=0.6, stroke_opacity=0.25,
            ).move_to(np.array([cx * 0.65, cy * 0.5 - 0.4, 0.0]))
            circles.add(c)

        self.play(
            LaggedStart(*[FadeIn(d, scale=0.5) for d in all_dots], lag_ratio=0.003),
            FadeIn(circles),
            run_time=1.2,
        )

        stats = label_text(
            f"{N_CLUSTERS} partitions, {N_CLUSTERS * PTS_PER} vectors", color=MUTED
        )
        stats.to_edge(DOWN, buff=1.0)
        self.play(FadeIn(stats))
        self.wait(0.4)

        # Query
        qx, qy = centers[2] + rng.normal(0, 0.25, 2)
        qpt = np.array([qx * 0.65, qy * 0.5 - 0.4, 0.0])
        q_dot = Dot(qpt, radius=0.09, color=ACCENT)
        q_lbl = label_text("query", color=ACCENT)
        q_lbl.next_to(q_dot, UR, buff=0.08)

        self.play(FadeIn(q_dot, scale=2.5), FadeIn(q_lbl), run_time=0.6)
        self.wait(0.3)

        # Find nearest partitions
        dists = []
        for ci in range(N_CLUSTERS):
            cx, cy = centers[ci]
            cp = np.array([cx * 0.65, cy * 0.5 - 0.4])
            dists.append((np.linalg.norm(cp - qpt[:2]), ci))
        dists.sort()
        nearest = [d[1] for d in dists[:N_PROBE]]

        probe_lbl = body_text(f"Probe nearest {N_PROBE} partitions", color=SECONDARY)
        probe_lbl.next_to(stats, DOWN, buff=0.15)
        self.play(FadeIn(probe_lbl))

        # Highlight nearest
        hi = []
        for ci in nearest:
            for dot in groups[ci]:
                hi.append(dot.animate.set_color(SECONDARY).set_opacity(1.0))
            hi.append(circles[ci].animate.set_color(SECONDARY).set_stroke(width=1.8, opacity=0.7))
        self.play(*hi, run_time=0.8)
        self.wait(0.3)

        # Dim the rest
        dim = []
        for ci in range(N_CLUSTERS):
            if ci not in nearest:
                for dot in groups[ci]:
                    dim.append(dot.animate.set_opacity(0.08))
                dim.append(circles[ci].animate.set_stroke(opacity=0.06))
        self.play(*dim, run_time=0.6)

        # Stats
        scored = N_PROBE * PTS_PER
        total = N_CLUSTERS * PTS_PER
        pct = (1 - scored / total) * 100

        result = body_text(
            f"Score {scored}/{total} vectors ({pct:.0f}% skipped)", color=SECONDARY
        )
        result.next_to(probe_lbl, DOWN, buff=0.15)
        self.play(FadeIn(result))
        self.wait(0.3)

        real = label_text(
            "25K vectors, 158 partitions: ~2,055 scored instead of 25,000 (6.8x speedup)",
            color=ACCENT,
        )
        real.next_to(result, DOWN, buff=0.12)
        self.play(FadeIn(real, shift=UP * 0.1))
        self.wait(2.5)
