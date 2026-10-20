#!/usr/bin/env python3
"""
svg_tools.py - SVG Animation & Path Helper Utilities
A zero-dependency helper tool for SVG animation development.

Capabilities:
1. measure: Estimate total length of SVG elements/paths to set stroke-dasharray & stroke-dashoffset.
2. check-morph: Validate whether two SVG path `d` strings have matching command topologies for smooth morphing.
3. scaffold: Generate a clean, responsive SVG wrapper with viewBox, accessibility attributes, and defs.
"""

import argparse
import math
import re
import sys
from typing import List, Tuple


def sample_cubic_bezier(p0, p1, p2, p3, steps=50) -> float:
    length = 0.0
    prev_pt = p0
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        length += math.hypot(x - prev_pt[0], y - prev_pt[1])
        prev_pt = (x, y)
    return length


def sample_quad_bezier(p0, p1, p2, steps=40) -> float:
    length = 0.0
    prev_pt = p0
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = mt**2 * p0[0] + 2 * mt * t * p1[0] + t**2 * p2[0]
        y = mt**2 * p0[1] + 2 * mt * t * p1[1] + t**2 * p2[1]
        length += math.hypot(x - prev_pt[0], y - prev_pt[1])
        prev_pt = (x, y)
    return length


def parse_path_commands(d: str) -> List[Tuple[str, List[float]]]:
    """Tokenize an SVG path into (command, list of float args)."""
    # Tokenizer for commands and numerical coordinates
    tokens = re.findall(r"([a-df-z]|[A-DF-Z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)", d)
    commands = []
    current_cmd = None
    args = []

    for token in tokens:
        if token.isalpha():
            if current_cmd is not None:
                commands.append((current_cmd, args))
                args = []
            current_cmd = token
        else:
            args.append(float(token))

    if current_cmd is not None:
        commands.append((current_cmd, args))

    return commands


def estimate_path_length(d: str) -> float:
    """Calculates approximate arc length of an SVG path definition."""
    commands = parse_path_commands(d)
    total_length = 0.0
    current_x, current_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    prev_control_x, prev_control_y = 0.0, 0.0

    for cmd, args in commands:
        is_rel = cmd.islower()
        op = cmd.upper()
        i = 0

        while i < len(args) or (op == "Z" and i == 0):
            if op == "M":
                target_x = current_x + args[i] if is_rel else args[i]
                target_y = current_y + args[i + 1] if is_rel else args[i + 1]
                current_x, current_y = target_x, target_y
                start_x, start_y = current_x, current_y
                prev_control_x, prev_control_y = current_x, current_y
                i += 2
                op = "L"  # Subsequent pairs after M act as L
            elif op == "L":
                target_x = current_x + args[i] if is_rel else args[i]
                target_y = current_y + args[i + 1] if is_rel else args[i + 1]
                total_length += math.hypot(target_x - current_x, target_y - current_y)
                current_x, current_y = target_x, target_y
                prev_control_x, prev_control_y = current_x, current_y
                i += 2
            elif op == "H":
                target_x = current_x + args[i] if is_rel else args[i]
                total_length += abs(target_x - current_x)
                current_x = target_x
                prev_control_x, prev_control_y = current_x, current_y
                i += 1
            elif op == "V":
                target_y = current_y + args[i] if is_rel else args[i]
                total_length += abs(target_y - current_y)
                current_y = target_y
                prev_control_x, prev_control_y = current_x, current_y
                i += 1
            elif op == "C":
                cp1_x = current_x + args[i] if is_rel else args[i]
                cp1_y = current_y + args[i + 1] if is_rel else args[i + 1]
                cp2_x = current_x + args[i + 2] if is_rel else args[i + 2]
                cp2_y = current_y + args[i + 3] if is_rel else args[i + 3]
                target_x = current_x + args[i + 4] if is_rel else args[i + 4]
                target_y = current_y + args[i + 5] if is_rel else args[i + 5]

                seg_len = sample_cubic_bezier(
                    (current_x, current_y), (cp1_x, cp1_y), (cp2_x, cp2_y), (target_x, target_y)
                )
                total_length += seg_len
                current_x, current_y = target_x, target_y
                prev_control_x, prev_control_y = cp2_x, cp2_y
                i += 6
            elif op == "S":
                cp1_x = 2 * current_x - prev_control_x
                cp1_y = 2 * current_y - prev_control_y
                cp2_x = current_x + args[i] if is_rel else args[i]
                cp2_y = current_y + args[i + 1] if is_rel else args[i + 1]
                target_x = current_x + args[i + 2] if is_rel else args[i + 2]
                target_y = current_y + args[i + 3] if is_rel else args[i + 3]

                seg_len = sample_cubic_bezier(
                    (current_x, current_y), (cp1_x, cp1_y), (cp2_x, cp2_y), (target_x, target_y)
                )
                total_length += seg_len
                current_x, current_y = target_x, target_y
                prev_control_x, prev_control_y = cp2_x, cp2_y
                i += 4
            elif op == "Q":
                cp_x = current_x + args[i] if is_rel else args[i]
                cp_y = current_y + args[i + 1] if is_rel else args[i + 1]
                target_x = current_x + args[i + 2] if is_rel else args[i + 2]
                target_y = current_y + args[i + 3] if is_rel else args[i + 3]

                seg_len = sample_quad_bezier((current_x, current_y), (cp_x, cp_y), (target_x, target_y))
                total_length += seg_len
                current_x, current_y = target_x, target_y
                prev_control_x, prev_control_y = cp_x, cp_y
                i += 4
            elif op == "T":
                cp_x = 2 * current_x - prev_control_x
                cp_y = 2 * current_y - prev_control_y
                target_x = current_x + args[i] if is_rel else args[i]
                target_y = current_y + args[i + 1] if is_rel else args[i + 1]

                seg_len = sample_quad_bezier((current_x, current_y), (cp_x, cp_y), (target_x, target_y))
                total_length += seg_len
                current_x, current_y = target_x, target_y
                prev_control_x, prev_control_y = cp_x, cp_y
                i += 2
            elif op == "A":
                # Elliptical arc fallback: chord distance
                target_x = current_x + args[i + 5] if is_rel else args[i + 5]
                target_y = current_y + args[i + 6] if is_rel else args[i + 6]
                chord = math.hypot(target_x - current_x, target_y - current_y)
                rx, ry = abs(args[i]), abs(args[i + 1])
                # Approximate arc length: slightly greater than chord if radii are large
                avg_r = (rx + ry) / 2.0 if (rx + ry) > 0 else chord / 2.0
                ratio = min(1.0, chord / (2.0 * max(avg_r, chord / 2.0)))
                arc_len = avg_r * 2.0 * math.asin(ratio) if avg_r > 0 else chord
                total_length += arc_len
                current_x, current_y = target_x, target_y
                prev_control_x, prev_control_y = current_x, current_y
                i += 7
            elif op == "Z":
                total_length += math.hypot(start_x - current_x, start_y - current_y)
                current_x, current_y = start_x, start_y
                prev_control_x, prev_control_y = current_x, current_y
                break
            else:
                break

    return total_length


def cmd_measure(args):
    """Measures path or SVG file paths and prints recommended stroke-dash CSS."""
    paths = []
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
            found = re.findall(r'<path[^>]*\bd=["\']([^"\']+)["\']', content)
            if not found:
                print(f"[!] No <path> elements found in {args.file}")
                return
            for idx, d_str in enumerate(found):
                paths.append((f"Path #{idx + 1}", d_str))
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            sys.exit(1)
    elif args.d:
        paths.append(("Provided Path", args.d))
    else:
        print("Please provide --d '<path_data>' or --file <svg_file>")
        return

    print("=" * 60)
    print("SVG Path Length Measurements & CSS Stroke Animation Helper")
    print("=" * 60)
    for label, d_str in paths:
        length = estimate_path_length(d_str)
        rounded = round(length, 1)
        int_ceil = math.ceil(length)
        print(f"\n[{label}]")
        print(f"Path Snippet: {d_str[:50]}..." if len(d_str) > 50 else f"Path: {d_str}")
        print(f"Calculated Arc Length: ~{rounded}px")
        print("Recommended CSS snippet:")
        print(
            f"  stroke-dasharray: {int_ceil};\n"
            f"  stroke-dashoffset: {int_ceil};\n"
            f"  animation: drawLine 1.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;\n\n"
            f"  @keyframes drawLine {{\n"
            f"    to {{ stroke-dashoffset: 0; }}\n"
            f"  }}"
        )


def cmd_check_morph(args):
    """Compares two paths to verify if they can be smoothly morphed via SMIL/CSS."""
    d1 = args.d1
    d2 = args.d2

    cmds1 = parse_path_commands(d1)
    cmds2 = parse_path_commands(d2)

    seq1 = [c[0].upper() for c in cmds1]
    seq2 = [c[0].upper() for c in cmds2]

    print("=" * 60)
    print("SVG Shape Morph Compatibility Checker")
    print("=" * 60)
    print(f"Path 1 Command Count: {len(seq1)} -> {' '.join(seq1)}")
    print(f"Path 2 Command Count: {len(seq2)} -> {' '.join(seq2)}")

    if seq1 == seq2:
        print("\n[MATCH] Both paths share the exact same command sequence.")
        print("They are fully compatible for SMIL <animate attributeName='d'> or CSS d: path(...) transitions.")
    elif len(seq1) == len(seq2):
        print("\n[WARNING] Paths have identical segment counts, but differing command types:")
        for idx, (c1, c2) in enumerate(zip(seq1, seq2)):
            status = "MATCH" if c1 == c2 else f"DIFF ({c1} vs {c2})"
            print(f"  Step {idx + 1}: {status}")
        print("Interpolation may fail or produce visual artifacts. Convert commands to match types.")
    else:
        print(f"\n[MISMATCH] Path 1 has {len(seq1)} segments, but Path 2 has {len(seq2)} segments.")
        print("SVG morphing engines require an identical number of points and command structure.")
        print("Tip: Add dummy colinear points or matching Bezier sub-paths to the simpler shape.")


def cmd_scaffold(args):
    """Generates an accessible, clean SVG template."""
    title = args.title or "Animated Graphic"
    desc = args.desc or "Scalable vector illustration with smooth animations"
    viewbox = args.viewbox or "0 0 100 100"

    svg_template = f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="{viewbox}"
     role="img"
     aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">{desc}</desc>

  <defs>
    <!-- Add gradients, filters, or masks here -->
  </defs>

  <g id="animated-elements">
    <!-- Insert graphic nodes and animations here -->
  </g>
</svg>'''
    print(svg_template)


def main():
    parser = argparse.ArgumentParser(description="SVG Animation & Geometry Utilities")
    subparsers = parser.add_subparsers(dest="command")

    # measure
    p_measure = subparsers.add_parser("measure", help="Estimate path length for stroke animations")
    p_measure.add_argument("--d", help="Path 'd' attribute string", type=str)
    p_measure.add_argument("--file", help="Path to SVG file to measure", type=str)

    # check-morph
    p_morph = subparsers.add_parser("check-morph", help="Check morph compatibility between two paths")
    p_morph.add_argument("--d1", required=True, help="First path 'd' string")
    p_morph.add_argument("--d2", required=True, help="Second path 'd' string")

    # scaffold
    p_scaffold = subparsers.add_parser("scaffold", help="Generate SVG wrapper template")
    p_scaffold.add_argument("--title", help="SVG title for accessibility")
    p_scaffold.add_argument("--desc", help="SVG description for accessibility")
    p_scaffold.add_argument("--viewbox", help="viewBox attribute (default: 0 0 100 100)")

    args = parser.parse_args()
    if args.command == "measure":
        cmd_measure(args)
    elif args.command == "check-morph":
        cmd_check_morph(args)
    elif args.command == "scaffold":
        cmd_scaffold(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
