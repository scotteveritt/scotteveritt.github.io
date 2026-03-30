"""
QR vs Hadamard: dense all-to-all vs sparse butterfly.

Visual: left side shows a dense matrix multiply (all-to-all connections
between input and output nodes). Right side shows the Hadamard butterfly
pattern (sparse, structured connections). Then the massive QR matrix
collapses into two tiny sign vectors.
"""

from manim import *
import numpy as np
from style import *

config.pixel_width = 1920
config.pixel_height = 1080

N_NODES = 16  # visual simplification of d=3072


class HadamardVsQR(Scene):
    def construct(self):
        setup_scene(self)

        title = Text("How the rotation is applied", font_size=28, color=TEXT_COLOR)
        title.to_edge(UP, buff=0.7)
        self.play(FadeIn(title, shift=DOWN * 0.2), run_time=0.5)

        # ── Left: QR dense multiply ──
        qr_label = Text("QR: dense matrix multiply", font_size=22, color=TERTIARY)
        qr_label.shift(LEFT * 4.5 + UP * 2.2)

        # Input and output nodes
        in_nodes_l = VGroup(*[
            Dot(point=np.array([-6.0, 1.8 - i * 0.3, 0]), radius=0.05, color=TEXT_COLOR)
            for i in range(N_NODES)
        ])
        out_nodes_l = VGroup(*[
            Dot(point=np.array([-3.0, 1.8 - i * 0.3, 0]), radius=0.05, color=TERTIARY)
            for i in range(N_NODES)
        ])

        # Dense connections: every input to every output
        dense_lines = VGroup()
        for i_node in in_nodes_l:
            for o_node in out_nodes_l:
                line = Line(
                    i_node.get_center(), o_node.get_center(),
                    color=TERTIARY, stroke_width=0.4, stroke_opacity=0.25,
                )
                dense_lines.add(line)

        qr_center = (in_nodes_l.get_center() + out_nodes_l.get_center()) / 2
        qr_cost = Text("O(d^2) operations", font_size=20, color=TERTIARY)
        qr_cost.move_to(qr_center).set_y(in_nodes_l.get_bottom()[1] - 0.6)
        qr_mem = Text("75 MB stored", font_size=20, color=TERTIARY)
        qr_mem.next_to(qr_cost, DOWN, buff=0.15)

        self.play(FadeIn(qr_label))
        self.play(FadeIn(in_nodes_l), FadeIn(out_nodes_l), run_time=0.4)
        self.play(
            LaggedStart(*[Create(l) for l in dense_lines], lag_ratio=0.001),
            run_time=1.5,
        )
        self.play(FadeIn(qr_cost), FadeIn(qr_mem))
        self.wait(0.5)

        # ── Right: Hadamard butterfly ──
        had_label = Text("Hadamard: butterfly pattern", font_size=22, color=SECONDARY)
        had_label.shift(RIGHT * 3.5 + UP * 2.2)

        n_stages = int(np.log2(N_NODES))  # 4 stages for 16 nodes
        stage_x = np.linspace(1.5, 6.5, n_stages + 1)
        node_y = np.linspace(1.8, 1.8 - (N_NODES - 1) * 0.3, N_NODES)

        # Create nodes at each stage
        all_stage_nodes = []
        all_stage_dots = VGroup()
        for s in range(n_stages + 1):
            stage_nodes = VGroup(*[
                Dot(point=np.array([stage_x[s], node_y[i], 0]), radius=0.05,
                    color=SECONDARY if s > 0 else TEXT_COLOR)
                for i in range(N_NODES)
            ])
            all_stage_nodes.append(stage_nodes)
            all_stage_dots.add(stage_nodes)

        # Butterfly connections
        butterfly_lines = VGroup()
        butterfly_stages = []
        for s in range(n_stages):
            stage_lines = VGroup()
            half = N_NODES // (2 ** (s + 1))
            for block_start in range(0, N_NODES, 2 * half):
                for i in range(half):
                    top = block_start + i
                    bot = block_start + i + half
                    # Straight connections
                    stage_lines.add(Line(
                        all_stage_nodes[s][top].get_center(),
                        all_stage_nodes[s + 1][top].get_center(),
                        color=SECONDARY, stroke_width=1.2, stroke_opacity=0.6,
                    ))
                    stage_lines.add(Line(
                        all_stage_nodes[s][bot].get_center(),
                        all_stage_nodes[s + 1][bot].get_center(),
                        color=SECONDARY, stroke_width=1.2, stroke_opacity=0.6,
                    ))
                    # Cross connections (the butterfly)
                    stage_lines.add(Line(
                        all_stage_nodes[s][top].get_center(),
                        all_stage_nodes[s + 1][bot].get_center(),
                        color=ACCENT, stroke_width=1.0, stroke_opacity=0.4,
                    ))
                    stage_lines.add(Line(
                        all_stage_nodes[s][bot].get_center(),
                        all_stage_nodes[s + 1][top].get_center(),
                        color=ACCENT, stroke_width=1.0, stroke_opacity=0.4,
                    ))
            butterfly_lines.add(stage_lines)
            butterfly_stages.append(stage_lines)

        had_center_x = (stage_x[0] + stage_x[-1]) / 2
        had_cost = Text("O(d log d) operations", font_size=20, color=SECONDARY)
        had_cost.move_to(RIGHT * had_center_x).set_y(all_stage_nodes[0][-1].get_center()[1] - 0.6)
        had_mem = Text("65 KB stored", font_size=20, color=SECONDARY)
        had_mem.next_to(had_cost, DOWN, buff=0.15)

        self.play(FadeIn(had_label))
        self.play(FadeIn(all_stage_dots), run_time=0.4)

        # Animate butterfly stage by stage
        for stage_lines in butterfly_stages:
            self.play(
                LaggedStart(*[Create(l) for l in stage_lines], lag_ratio=0.01),
                run_time=0.6,
            )

        self.play(FadeIn(had_cost), FadeIn(had_mem))
        self.wait(0.5)

        # ── Comparison callout ──
        vs_line = Line(UP * 2, DOWN * 2.5, color=MUTED_DARK, stroke_width=1)
        vs_line.move_to(ORIGIN)

        comparison = VGroup(
            Text("1,150x less memory", font_size=26, color=ACCENT),
            Text("Better recall: 91.9% vs ~85%", font_size=20, color=MUTED_LIGHT),
        ).arrange(DOWN, buff=0.15).to_edge(DOWN, buff=0.7)

        self.play(Create(vs_line), FadeIn(comparison, shift=UP * 0.2))
        self.wait(2.5)
