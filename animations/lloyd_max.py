"""
Lloyd-Max convergence: data points snap to optimal centroids.

Visual: bell curve with scattered sample points. 16 centroid markers
start uniform, then slide to optimal positions. Points visibly snap
to their nearest centroid at each step.
"""

from manim import *
import numpy as np
from scipy.stats import norm as scipy_norm
from scipy.integrate import quad as scipy_quad
from style import *

config.pixel_width = 1920
config.pixel_height = 1080

D = 3072
SIGMA = 1.0 / np.sqrt(D)
NUM_LEVELS = 16
CLIP = 6.0 * SIGMA
N_SAMPLES = 120


def gpdf(x):
    return float(scipy_norm.pdf(x, 0, SIGMA))


def lloyd_steps(n_steps=30):
    centroids = np.linspace(-CLIP * 0.9, CLIP * 0.9, NUM_LEVELS)
    for _ in range(n_steps):
        boundaries = (centroids[:-1] + centroids[1:]) / 2.0
        edges = np.concatenate([[-CLIP], boundaries, [CLIP]])
        yield centroids.copy(), boundaries.copy()
        new = np.zeros(NUM_LEVELS)
        for i in range(NUM_LEVELS):
            a, b = edges[i], edges[i + 1]
            num, _ = scipy_quad(lambda x: x * gpdf(x), a, b)
            den, _ = scipy_quad(gpdf, a, b)
            new[i] = num / den if den > 1e-15 else (a + b) / 2
        centroids = new
    boundaries = (centroids[:-1] + centroids[1:]) / 2.0
    yield centroids.copy(), boundaries.copy()


def snap_to_nearest(x, centroids):
    """Return the centroid nearest to x."""
    return centroids[np.argmin(np.abs(centroids - x))]


class LloydMaxConvergence(Scene):
    def construct(self):
        setup_scene(self)

        # Axes
        x_lo, x_hi = -CLIP * 1.3, CLIP * 1.3
        y_max = gpdf(0) * 1.15
        ax = styled_axes(
            [x_lo, x_hi, SIGMA], [0, y_max, y_max / 4],
            x_length=13, y_length=5,
        ).shift(DOWN * 0.3)

        # Gaussian curve
        curve = ax.plot(gpdf, x_range=[x_lo, x_hi], color=PRIMARY, stroke_width=MED_STROKE)
        fill = ax.get_area(curve, x_range=(x_lo, x_hi), color=PRIMARY_DIM, opacity=0.08)
        self.play(Create(ax, run_time=0.4), Create(curve, run_time=0.8), FadeIn(fill))

        # Generate sample points from the distribution
        rng = np.random.default_rng(42)
        sample_xs = rng.normal(0, SIGMA, N_SAMPLES)
        sample_xs = sample_xs[(sample_xs > x_lo * 0.9) & (sample_xs < x_hi * 0.9)]

        # Place sample points as dots along x-axis
        sample_dots = VGroup(*[
            Dot(ax.c2p(x, 0), radius=0.04, color=TEXT_COLOR, fill_opacity=0.6)
            for x in sample_xs
        ])
        self.play(
            LaggedStart(*[FadeIn(d, shift=UP * 0.15) for d in sample_dots], lag_ratio=0.008),
            run_time=0.8,
        )

        # Lloyd-Max iteration
        steps = list(lloyd_steps(30))
        c0, b0 = steps[0]

        # Centroid markers: vertical lines with diamonds at top
        def make_centroid_markers(centroids):
            markers = VGroup()
            for c in centroids:
                line = Line(
                    ax.c2p(c, 0), ax.c2p(c, gpdf(c) * 0.7),
                    color=ACCENT, stroke_width=2,
                )
                diamond = Dot(ax.c2p(c, 0), radius=0.06, color=ACCENT)
                markers.add(VGroup(line, diamond))
            return markers

        markers = make_centroid_markers(c0)

        # Boundary shading: color regions between centroids
        def make_regions(centroids, boundaries):
            regions = VGroup()
            edges = np.concatenate([[x_lo], boundaries, [x_hi]])
            colors = [SECONDARY, PRIMARY]
            for i in range(len(centroids)):
                a, b = edges[i], edges[i + 1]
                rect = Rectangle(
                    width=abs(ax.c2p(b, 0)[0] - ax.c2p(a, 0)[0]),
                    height=0.12,
                    fill_color=colors[i % 2],
                    fill_opacity=0.15,
                    stroke_width=0,
                )
                rect.move_to(ax.c2p((a + b) / 2, 0))
                rect.align_to(ax.c2p(0, 0), DOWN).shift(DOWN * 0.15)
                regions.add(rect)
            return regions

        regions = make_regions(c0, b0)

        title = Text("Lloyd-Max: finding optimal centroid positions",
                      font_size=28, color=TEXT_COLOR)
        title.to_edge(UP, buff=0.7)

        self.play(FadeIn(title, shift=DOWN * 0.2))
        self.play(
            LaggedStart(*[GrowFromCenter(m) for m in markers], lag_ratio=0.03),
            FadeIn(regions),
            run_time=0.8,
        )

        # Snap sample dots to nearest centroid
        def snap_dots(dots, centroids, ax_ref):
            anims = []
            for dot in dots:
                x = ax_ref.p2c(dot.get_center())[0]
                nearest = snap_to_nearest(x, centroids)
                target = ax_ref.c2p(nearest, 0)
                anims.append(dot.animate.move_to(target).set_color(ACCENT).set_opacity(0.8))
            return anims

        # Show initial snap
        snap_anims = snap_dots(sample_dots, c0, ax)
        self.play(*snap_anims, run_time=1.0)
        self.wait(0.3)

        # Unsnap (return to original positions)
        original_positions = [ax.c2p(x, 0) for x in sample_xs]

        def unsnap_dots(dots, positions):
            return [
                d.animate.move_to(p).set_color(TEXT_COLOR).set_opacity(0.6)
                for d, p in zip(dots, positions)
            ]

        self.play(*unsnap_dots(sample_dots, original_positions), run_time=0.5)

        # Animate convergence
        iter_label = Text("Iteration 0", font_size=22, color=MUTED_LIGHT)
        iter_label.to_corner(UR, buff=0.8)
        self.play(FadeIn(iter_label))

        show_iters = [1, 2, 3, 5, 8, 14, len(steps) - 1]
        for si in show_iters:
            ci, bi = steps[si]
            new_markers = make_centroid_markers(ci)
            new_regions = make_regions(ci, bi)
            new_label = Text(f"Iteration {si}", font_size=22, color=MUTED_LIGHT)
            new_label.to_corner(UR, buff=0.8)

            # Snap dots to new centroids
            snap_anims = snap_dots(sample_dots, ci, ax)

            self.play(
                Transform(markers, new_markers),
                Transform(regions, new_regions),
                Transform(iter_label, new_label),
                *snap_anims,
                run_time=0.7 if si <= 5 else 0.5,
            )

            if si < show_iters[-1]:
                self.play(*unsnap_dots(sample_dots, original_positions), run_time=0.3)

        # Final state: dots stay snapped, show "converged"
        done = Text("Converged", font_size=32, color=SECONDARY)
        detail = Text("16 optimal centroids for N(0, 1/sqrt(d))",
                       font_size=20, color=MUTED_LIGHT)
        detail.next_to(done, DOWN, buff=0.15)
        callout_bg = Rectangle(
            width=done.width + 1.0, height=1.2,
            fill_color=BG, fill_opacity=0.9, stroke_width=0,
        )
        callout = VGroup(callout_bg, done, detail)
        done.move_to(callout_bg.get_center() + UP * 0.2)
        detail.next_to(done, DOWN, buff=0.15)
        callout.to_edge(DOWN, buff=0.7)
        self.play(FadeIn(callout, shift=UP * 0.2))
        self.wait(2)
