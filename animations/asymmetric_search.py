"""
Asymmetric search: geometric demonstration.

Scene 1: "Naive" - query arrow in original space, stored arrows in
rotated/compressed space. To compare, each stored vector must be
un-rotated back (N expensive operations, shown sequentially).

Scene 2: "Asymmetric" - instead, rotate the query INTO compressed
space (1 operation). Now it lives alongside all stored vectors.
Score them all directly with quick parallel flashes.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1920
config.pixel_height = 1080

N_STORED = 8


class AsymmetricSearch(Scene):
    def construct(self):
        setup_scene(self)

        rng = np.random.default_rng(42)

        # Generate stored vectors (unit vectors, random angles)
        stored_angles = rng.uniform(0, TAU, N_STORED)
        stored_vecs = np.stack([np.cos(stored_angles), np.sin(stored_angles)], axis=1)

        # Query vector
        query_angle = 0.6
        query_vec = np.array([np.cos(query_angle), np.sin(query_angle)])

        # Rotation angle (the "compression rotation")
        rot_angle = 1.2

        # ═══════════════════════════════════════════════════
        # SCENE 1: The naive way
        # ═══════════════════════════════════════════════════
        title1 = Text("Naive: un-rotate each stored vector",
                       font_size=26, color=TERTIARY)
        title1.to_edge(UP, buff=0.8)

        ax = styled_axes(
            [-1.6, 1.6, 1], [-1.6, 1.6, 1],
            x_length=5.5, y_length=5.5,
        )

        circle = Circle(
            radius=ax.c2p(1, 0)[0] - ax.c2p(0, 0)[0],
            color=MUTED_DARK, stroke_width=1,
        ).move_to(ax.c2p(0, 0))

        self.play(Create(ax, run_time=0.3), Create(circle, run_time=0.3))
        self.play(FadeIn(title1, shift=DOWN * 0.15))

        # Draw query arrow (in original space)
        q_arrow = Arrow(
            ax.c2p(0, 0), ax.c2p(*query_vec), buff=0,
            color=ACCENT, stroke_width=3.5,
            max_tip_length_to_length_ratio=0.12,
        )
        q_label = Text("query", font_size=18, color=ACCENT)
        q_label.next_to(q_arrow.get_end(), UR, buff=0.1)
        self.play(GrowArrow(q_arrow), FadeIn(q_label), run_time=0.5)

        # Draw stored vectors in ROTATED space (shown dimmer, offset by rotation)
        R = np.array([[np.cos(rot_angle), -np.sin(rot_angle)],
                       [np.sin(rot_angle),  np.cos(rot_angle)]])
        rotated_stored = (R @ stored_vecs.T).T

        stored_arrows = VGroup()
        for v in rotated_stored:
            arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(*v), buff=0,
                color=TERTIARY_DIM, stroke_width=2,
                max_tip_length_to_length_ratio=0.1,
            )
            stored_arrows.add(arrow)

        stored_label = Text("stored (compressed space)", font_size=16, color=TERTIARY)
        stored_label.to_edge(DOWN, buff=0.8)

        self.play(
            LaggedStart(*[GrowArrow(a) for a in stored_arrows], lag_ratio=0.05),
            FadeIn(stored_label),
            run_time=0.6,
        )
        self.wait(0.3)

        # Naive approach: un-rotate each stored vector one by one
        # Show each one rotating back and then flashing a comparison
        counter_label = Text("Rotations: 0", font_size=20, color=MUTED_LIGHT)
        counter_label.to_corner(UR, buff=0.8)
        self.play(FadeIn(counter_label))

        count = 0
        for i, (orig_v, rot_v) in enumerate(zip(stored_vecs, rotated_stored)):
            # Animate the stored arrow rotating back to original space
            unrot_arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(*orig_v), buff=0,
                color=PRIMARY, stroke_width=2.5,
                max_tip_length_to_length_ratio=0.1,
            )

            count += 1
            new_counter = Text(f"Rotations: {count}", font_size=20, color=MUTED_LIGHT)
            new_counter.to_corner(UR, buff=0.8)

            # Show rotation arc
            arc = Arc(
                radius=0.3,
                start_angle=np.arctan2(rot_v[1], rot_v[0]),
                angle=-rot_angle,
                arc_center=ax.c2p(0, 0),
                color=TERTIARY, stroke_width=1.5,
            )

            self.play(
                Transform(stored_arrows[i], unrot_arrow),
                Create(arc),
                Transform(counter_label, new_counter),
                run_time=0.25,
            )
            # Quick flash showing similarity measured
            flash = Dot(ax.c2p(*orig_v), radius=0.12, color=ACCENT, fill_opacity=0.6)
            self.play(FadeIn(flash, scale=2), run_time=0.1)
            self.play(
                FadeOut(flash),
                FadeOut(arc),
                Transform(stored_arrows[i], Arrow(
                    ax.c2p(0, 0), ax.c2p(*rot_v), buff=0,
                    color=TERTIARY_DIM, stroke_width=2,
                    max_tip_length_to_length_ratio=0.1,
                )),
                run_time=0.1,
            )

        slow_text = Text(f"{N_STORED} rotations needed", font_size=22, color=TERTIARY)
        slow_text.next_to(stored_label, UP, buff=0.2)
        self.play(FadeIn(slow_text))
        self.wait(0.8)

        # ═══════════════════════════════════════════════════
        # SCENE 2: The asymmetric way
        # ═══════════════════════════════════════════════════
        # Clear and reset
        self.play(
            *[FadeOut(m) for m in [title1, stored_label, slow_text,
                                    counter_label, q_label]],
            *[FadeOut(a) for a in stored_arrows],
            FadeOut(q_arrow),
            run_time=0.4,
        )

        title2 = Text("Asymmetric: rotate the query instead",
                       font_size=26, color=SECONDARY)
        title2.to_edge(UP, buff=0.8)
        self.play(FadeIn(title2, shift=DOWN * 0.15))

        # Redraw query
        q_arrow = Arrow(
            ax.c2p(0, 0), ax.c2p(*query_vec), buff=0,
            color=ACCENT, stroke_width=3.5,
            max_tip_length_to_length_ratio=0.12,
        )
        q_label = Text("query", font_size=18, color=ACCENT)
        q_label.next_to(q_arrow.get_end(), UR, buff=0.1)
        self.play(GrowArrow(q_arrow), FadeIn(q_label), run_time=0.4)

        # Redraw stored vectors (in rotated space)
        stored_arrows = VGroup()
        for v in rotated_stored:
            arrow = Arrow(
                ax.c2p(0, 0), ax.c2p(*v), buff=0,
                color=TERTIARY_DIM, stroke_width=2,
                max_tip_length_to_length_ratio=0.1,
            )
            stored_arrows.add(arrow)

        stored_label = Text("stored (compressed space)", font_size=16, color=TERTIARY)
        stored_label.to_edge(DOWN, buff=0.8)

        self.play(
            LaggedStart(*[FadeIn(a) for a in stored_arrows], lag_ratio=0.03),
            FadeIn(stored_label),
            run_time=0.4,
        )

        # Rotate the query INTO compressed space (one rotation!)
        rotated_query = R @ query_vec
        rq_arrow = Arrow(
            ax.c2p(0, 0), ax.c2p(*rotated_query), buff=0,
            color=SECONDARY, stroke_width=3.5,
            max_tip_length_to_length_ratio=0.12,
        )
        rq_label = Text("rotated query", font_size=18, color=SECONDARY)
        rq_label.next_to(rq_arrow.get_end(), UL, buff=0.1)

        rot_arc = Arc(
            radius=0.4,
            start_angle=query_angle,
            angle=rot_angle,
            arc_center=ax.c2p(0, 0),
            color=SECONDARY, stroke_width=2.5,
        )

        one_label = Text("1 rotation", font_size=22, color=SECONDARY)
        one_label.to_corner(UR, buff=0.8)

        self.play(
            Transform(q_arrow, rq_arrow),
            Transform(q_label, rq_label),
            Create(rot_arc),
            FadeIn(one_label),
            run_time=1.0,
        )
        self.wait(0.3)
        self.play(FadeOut(rot_arc), run_time=0.3)

        # Now score all stored vectors simultaneously - rapid parallel flashes
        score_label = Text("Score all directly - no decompression",
                           font_size=20, color=SECONDARY)
        score_label.next_to(stored_label, UP, buff=0.2)

        # Flash all stored arrows simultaneously turning bright
        flash_anims = []
        score_lines = VGroup()
        for i, v in enumerate(rotated_stored):
            # Draw a brief connecting arc between query and stored vector
            midpoint = (rotated_query + v) / 2 * 0.3
            line = Line(
                ax.c2p(*rotated_query * 0.9),
                ax.c2p(*v * 0.9),
                color=ACCENT, stroke_width=1.5, stroke_opacity=0.5,
            )
            score_lines.add(line)
            flash_anims.append(
                stored_arrows[i].animate.set_color(SECONDARY).set_stroke(width=3)
            )

        self.play(
            LaggedStart(*[Create(l) for l in score_lines], lag_ratio=0.04),
            LaggedStart(*flash_anims, lag_ratio=0.04),
            FadeIn(score_label),
            run_time=0.8,
        )
        self.wait(2)
