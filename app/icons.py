"""Small vector icon library rendered with Dear PyGui draw primitives."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeAlias

import dearpygui.dearpygui as dpg


Color: TypeAlias = tuple[int, int, int, int]
Point: TypeAlias = tuple[float, float]

GLYPHS: frozenset[str] = frozenset(
    {
        "shield",
        "lock",
        "eye-off",
        "pin",
        "wifi",
        "globe",
        "cloud",
        "gauge",
        "battery",
        "bolt",
        "gamepad",
        "cursor",
        "monitor",
        "stop",
        "pause",
        "chart",
        "trash",
        "undo",
    }
)


def _arc_points(
    center: Point,
    radii: Point,
    start_angle: float,
    end_angle: float,
    *,
    rotation: float = 0.0,
    segments_per_quarter: int = 10,
) -> list[Point]:
    """Approximate an elliptical arc defined by centre, radii and angles."""
    sweep = end_angle - start_angle
    segments = max(
        1,
        math.ceil(abs(sweep) / (math.pi / 2.0) * segments_per_quarter),
    )
    cos_rotation = math.cos(rotation)
    sin_rotation = math.sin(rotation)
    points: list[Point] = []
    for index in range(segments + 1):
        angle = start_angle + sweep * index / segments
        local_x = radii[0] * math.cos(angle)
        local_y = radii[1] * math.sin(angle)
        points.append(
            (
                center[0] + cos_rotation * local_x - sin_rotation * local_y,
                center[1] + sin_rotation * local_x + cos_rotation * local_y,
            )
        )
    return points


def _svg_arc_points(
    start: Point,
    end: Point,
    rx: float,
    ry: float,
    large_arc: bool,
    sweep: bool,
    rotation_degrees: float = 0.0,
) -> list[Point]:
    """Convert an SVG endpoint arc to points from :func:`_arc_points`."""
    if start == end:
        return [start]
    rx = abs(rx)
    ry = abs(ry)
    if rx == 0.0 or ry == 0.0:
        return [start, end]

    rotation = math.radians(rotation_degrees % 360.0)
    cos_rotation = math.cos(rotation)
    sin_rotation = math.sin(rotation)
    half_dx = (start[0] - end[0]) / 2.0
    half_dy = (start[1] - end[1]) / 2.0
    x_prime = cos_rotation * half_dx + sin_rotation * half_dy
    y_prime = -sin_rotation * half_dx + cos_rotation * half_dy

    radius_scale = x_prime * x_prime / (rx * rx) + y_prime * y_prime / (ry * ry)
    if radius_scale > 1.0:
        scale = math.sqrt(radius_scale)
        rx *= scale
        ry *= scale

    numerator = max(
        0.0,
        rx * rx * ry * ry
        - rx * rx * y_prime * y_prime
        - ry * ry * x_prime * x_prime,
    )
    denominator = rx * rx * y_prime * y_prime + ry * ry * x_prime * x_prime
    coefficient = 0.0 if denominator == 0.0 else math.sqrt(numerator / denominator)
    if large_arc == sweep:
        coefficient = -coefficient
    center_x_prime = coefficient * rx * y_prime / ry
    center_y_prime = coefficient * -ry * x_prime / rx
    center = (
        cos_rotation * center_x_prime
        - sin_rotation * center_y_prime
        + (start[0] + end[0]) / 2.0,
        sin_rotation * center_x_prime
        + cos_rotation * center_y_prime
        + (start[1] + end[1]) / 2.0,
    )

    start_vector = (
        (x_prime - center_x_prime) / rx,
        (y_prime - center_y_prime) / ry,
    )
    end_vector = (
        (-x_prime - center_x_prime) / rx,
        (-y_prime - center_y_prime) / ry,
    )
    start_angle = math.atan2(start_vector[1], start_vector[0])
    delta_angle = math.atan2(
        start_vector[0] * end_vector[1] - start_vector[1] * end_vector[0],
        start_vector[0] * end_vector[0] + start_vector[1] * end_vector[1],
    )
    if not sweep and delta_angle > 0.0:
        delta_angle -= math.tau
    elif sweep and delta_angle < 0.0:
        delta_angle += math.tau
    return _arc_points(
        center,
        (rx, ry),
        start_angle,
        start_angle + delta_angle,
        rotation=rotation,
    )


@dataclass(frozen=True)
class _Canvas:
    parent: int | str
    size: float
    color: Color
    base_thickness: float

    @property
    def scale(self) -> float:
        return self.size / 24.0

    @property
    def thickness(self) -> float:
        return self.base_thickness * self.scale

    def point(self, point: Point) -> Point:
        return (point[0] * self.scale, point[1] * self.scale)

    def _round_joint(self, point: Point) -> None:
        dpg.draw_circle(
            self.point(point),
            self.thickness / 2.0,
            parent=self.parent,
            color=self.color,
            fill=self.color,
            segments=12,
        )

    def line(self, start: Point, end: Point) -> None:
        dpg.draw_line(
            self.point(start),
            self.point(end),
            parent=self.parent,
            color=self.color,
            thickness=self.thickness,
        )
        self._round_joint(start)
        self._round_joint(end)

    def polyline(self, points: list[Point], *, closed: bool = False) -> None:
        dpg.draw_polyline(
            [self.point(point) for point in points],
            parent=self.parent,
            closed=closed,
            color=self.color,
            thickness=self.thickness,
        )
        for point in points if closed else (points[0], points[-1]):
            self._round_joint(point)

    def bezier(self, p1: Point, p2: Point, p3: Point, p4: Point) -> None:
        dpg.draw_bezier_cubic(
            self.point(p1),
            self.point(p2),
            self.point(p3),
            self.point(p4),
            parent=self.parent,
            color=self.color,
            thickness=self.thickness,
            segments=24,
        )
        self._round_joint(p1)
        self._round_joint(p4)

    def circle(self, center: Point, radius: float, *, filled: bool = False) -> None:
        dpg.draw_circle(
            self.point(center),
            radius * self.scale,
            parent=self.parent,
            color=self.color,
            fill=self.color if filled else (0, 0, 0, 0),
            thickness=self.thickness,
            segments=32,
        )

    def rectangle(self, pmin: Point, pmax: Point, rounding: float) -> None:
        dpg.draw_rectangle(
            self.point(pmin),
            self.point(pmax),
            parent=self.parent,
            color=self.color,
            rounding=rounding * self.scale,
            thickness=self.thickness,
        )


def _joined(*parts: list[Point]) -> list[Point]:
    points: list[Point] = []
    for part in parts:
        points.extend(part if not points else part[1:])
    return points


def _shield(canvas: _Canvas) -> None:
    canvas.line((12, 3), (20, 6.2))
    canvas.line((20, 6.2), (20, 12))
    canvas.bezier((20, 12), (20, 16.8), (12, 21), (12, 21))
    canvas.bezier((12, 21), (12, 21), (4, 16.8), (4, 12))
    canvas.line((4, 12), (4, 6.2))
    canvas.line((4, 6.2), (12, 3))


def _lock(canvas: _Canvas) -> None:
    canvas.rectangle((4.5, 10.5), (19.5, 20.5), 2)
    canvas.line((8, 10.5), (8, 7.5))
    canvas.polyline(_arc_points((12, 7.5), (4, 4), math.pi, math.tau))
    canvas.line((16, 7.5), (16, 10.5))


def _eye_off(canvas: _Canvas) -> None:
    canvas.bezier((3, 12), (5.5, 7.5), (8.5, 5.5), (12, 5.5))
    canvas.bezier((12, 5.5), (15.5, 5.5), (18.5, 7.5), (21, 12))
    canvas.bezier((21, 12), (19.8, 14.2), (18.4, 15.8), (16.8, 16.9))
    canvas.polyline(_svg_arc_points((9.6, 9.6), (14.4, 14.4), 3.4, 3.4, False, False))
    canvas.line((4, 20), (20, 4))


def _pin(canvas: _Canvas) -> None:
    canvas.bezier((12, 21), (12, 21), (18.5, 14.6), (18.5, 10.5))
    canvas.polyline(_svg_arc_points((18.5, 10.5), (5.5, 10.5), 6.5, 6.5, True, False))
    canvas.bezier((5.5, 10.5), (5.5, 14.6), (12, 21), (12, 21))
    canvas.circle((12, 10.3), 2.4)


def _wifi(canvas: _Canvas) -> None:
    canvas.bezier((2.5, 8.8), (8, 4), (16, 4), (21.5, 8.8))
    canvas.bezier((6, 12.6), (9.4, 9.6), (14.6, 9.6), (18, 12.6))
    canvas.bezier((9.4, 16.3), (11, 14.9), (13, 14.9), (14.6, 16.3))
    canvas.circle((12, 19.6), 0.9, filled=True)


def _globe(canvas: _Canvas) -> None:
    canvas.circle((12, 12), 8.5)
    canvas.line((3.5, 12), (20.5, 12))
    canvas.bezier((12, 3.5), (15, 6.6), (15, 17.4), (12, 20.5))
    canvas.bezier((12, 20.5), (9, 17.4), (9, 6.6), (12, 3.5))


def _cloud(canvas: _Canvas) -> None:
    outline = _joined(
        _svg_arc_points((6.8, 18.5), (7, 10), 4.3, 4.3, False, True),
        _svg_arc_points((7, 10), (17.7, 10.6), 5.6, 5.6, False, True),
        _svg_arc_points((17.7, 10.6), (17.4, 18.5), 3.9, 3.9, False, True),
        [(17.4, 18.5), (6.8, 18.5)],
    )
    canvas.polyline(outline, closed=True)


def _gauge(canvas: _Canvas) -> None:
    canvas.polyline(_svg_arc_points((4, 17.5), (20, 17.5), 9, 9, True, True))
    canvas.line((12, 17), (16.2, 10.6))
    canvas.circle((12, 17.4), 1.2, filled=True)


def _battery(canvas: _Canvas) -> None:
    canvas.rectangle((2.5, 8), (19.5, 17), 2)
    canvas.line((21.8, 11), (21.8, 14))
    canvas.line((6, 11), (6, 14))
    canvas.line((9.4, 11), (9.4, 14))


def _bolt(canvas: _Canvas) -> None:
    canvas.polyline(
        [(13.2, 2.5), (4.5, 13.8), (11, 13.8), (10.4, 21.5), (19.5, 10.2), (13, 10.2)],
        closed=True,
    )


def _gamepad(canvas: _Canvas) -> None:
    outline = _joined(
        [(8.4, 8), (15.6, 8)],
        _svg_arc_points((15.6, 8), (21, 15), 5.6, 5.6, False, True),
        [(21, 15), (20.2, 17.6)],
        _svg_arc_points((20.2, 17.6), (15.7, 18.3), 2.6, 2.6, False, True),
        [(15.7, 18.3), (14.2, 16.2), (9.8, 16.2), (8.3, 18.3)],
        _svg_arc_points((8.3, 18.3), (3.8, 17.6), 2.6, 2.6, False, True),
        [(3.8, 17.6), (3, 15)],
        _svg_arc_points((3, 15), (8.4, 8), 5.6, 5.6, False, True),
    )
    canvas.polyline(outline, closed=True)
    canvas.line((7.6, 12.6), (9.9, 12.6))
    canvas.line((8.75, 11.4), (8.75, 13.8))
    canvas.circle((16, 12.6), 0.9, filled=True)


def _cursor(canvas: _Canvas) -> None:
    canvas.polyline(
        [(5.5, 3), (18.5, 12.4), (12.6, 13.4), (15.9, 19.6), (13.4, 20.9), (10.1, 14.7), (5.5, 18.6)],
        closed=True,
    )


def _monitor(canvas: _Canvas) -> None:
    canvas.rectangle((2.8, 4.2), (21.2, 16.6), 2)
    canvas.line((8.4, 20.2), (15.6, 20.2))
    canvas.line((12, 16.6), (12, 20.2))


def _stop(canvas: _Canvas) -> None:
    canvas.rectangle((5.5, 5.5), (18.5, 18.5), 2.4)


def _pause(canvas: _Canvas) -> None:
    canvas.line((9.2, 5), (9.2, 19))
    canvas.line((14.8, 5), (14.8, 19))


def _chart(canvas: _Canvas) -> None:
    canvas.line((4, 20), (20.5, 20))
    canvas.line((7.4, 20), (7.4, 13))
    canvas.line((12, 20), (12, 6.5))
    canvas.line((16.6, 20), (16.6, 10))


def _trash(canvas: _Canvas) -> None:
    canvas.line((3.8, 6.5), (20.2, 6.5))
    lid = _joined(
        [(9.4, 6.5), (9.4, 4.4)],
        _svg_arc_points((9.4, 4.4), (10.4, 3.4), 1, 1, False, True),
        [(10.4, 3.4), (13.6, 3.4)],
        _svg_arc_points((13.6, 3.4), (14.6, 4.4), 1, 1, False, True),
        [(14.6, 4.4), (14.6, 6.5)],
    )
    canvas.polyline(lid)
    body = _joined(
        [(5.8, 6.5), (6.8, 19.6)],
        _svg_arc_points((6.8, 19.6), (8.4, 21), 1.6, 1.6, False, False),
        [(8.4, 21), (15.6, 21)],
        _svg_arc_points((15.6, 21), (17.2, 19.6), 1.6, 1.6, False, False),
        [(17.2, 19.6), (18.2, 6.5)],
    )
    canvas.polyline(body)
    canvas.line((10.2, 10.4), (10.2, 17))
    canvas.line((13.8, 10.4), (13.8, 17))


def _undo(canvas: _Canvas) -> None:
    canvas.line((3.6, 8.2), (9.6, 8.2))
    canvas.line((3.6, 8.2), (3.6, 14.2))
    canvas.bezier((3.6, 8.2), (8, 3.4), (16, 3.6), (19.2, 8.8))
    canvas.bezier((19.2, 8.8), (22, 13.4), (20.4, 19), (15.6, 20.8))


_DRAWERS = {
    "shield": _shield,
    "lock": _lock,
    "eye-off": _eye_off,
    "pin": _pin,
    "wifi": _wifi,
    "globe": _globe,
    "cloud": _cloud,
    "gauge": _gauge,
    "battery": _battery,
    "bolt": _bolt,
    "gamepad": _gamepad,
    "cursor": _cursor,
    "monitor": _monitor,
    "stop": _stop,
    "pause": _pause,
    "chart": _chart,
    "trash": _trash,
    "undo": _undo,
}


def draw_glyph(
    name: str,
    parent: int | str,
    size: float = 24,
    color: Color = (240, 240, 240, 255),
    thickness: float = 1.5,
) -> None:
    """Draw a named glyph into *parent*, scaling its 24x24 design grid."""
    try:
        drawer = _DRAWERS[name]
    except KeyError as error:
        expected = ", ".join(sorted(GLYPHS))
        raise ValueError(f"Unknown glyph {name!r}; expected one of: {expected}") from error
    if size <= 0:
        raise ValueError("Glyph size must be positive")
    if thickness <= 0:
        raise ValueError("Glyph thickness must be positive")
    drawer(_Canvas(parent, float(size), color, float(thickness)))
