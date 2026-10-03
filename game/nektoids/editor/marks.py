"""The swimmer at work (D-076): what the run and Diagnostic draw on and round its body.

Its parts: each eye's face and each thruster's back where the board puts them on the body
(D-018), with their outlines, the board's shapes scaled by the body's reach. Its flames: specks
drifting out of each thruster's back, FLAME_LENGTH long at any rate, the rate being their
density. The light it draws in: the flames run backwards, specks drawn into each eye's face from
each light the eye sees, along that light's direction, as many as that light gives the reading;
they come in over the face's width as the light sees it, its cosine (D-019). Its motion: the
velocity as a segment from the rim, the spin as an arc from the heading, both from the thrust
the nodes have now (D-022), which is what the next tick does.

Every function returns points in the plane [u]; the drawing turns them into pixels. The specks
are a picture, never read by the model: drawn from a table made once and read by the frame, so
they stand still while the run is paused and come back the same on a replay, as the rays do
(invariant 1). Pure numpy, no pygame.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from nektoids.editor.geometry import EYE_DISC, SQUARE_POINT
from nektoids.graph.dynamics import RATE_MAX, thrust_rates
from nektoids.graph.hexgrid import Cell
from nektoids.graph.network import Network, body_disc
from nektoids.sim.arena import LIGHT_RADIUS, Arena
from nektoids.sim.motion import SPEED, stokes, thrust
from nektoids.sim.optics import FACING_STEP, TINY, discs, exposure, eye_poses, visible
from nektoids.sim.world import parts

FLAME_LENGTH = 3.0  # [body radii] every flame, whatever its rate: the rate is its density
FLAME_SPECKS = 12  # specks in a flame at once at RATE_MAX, on average
FLAME_SPREAD = math.radians(10.0)  # a flame widens by this much either side
FLAME_LIFE = 16  # [frames] a speck's way out
INTAKE_LENGTH = 3.0  # [body radii] how far out the specks of light start
INTAKE_SPECKS = 12  # specks drawn into an eye reading RATE_MAX, at once, on average
INTAKE_SPREAD = math.radians(10.0)
INTAKE_LIFE = 30  # [frames] a speck's way in, 0.5 s
VELOCITY_SPAN = 1.0  # [s] the segment is the way the body goes in this long
# [s] ... on Diagnostic's main screen, where the body is large: there 6 u/s, two thrusters at
# RATE_MAX through the centre, reaches one body radius past the rim
PREVIEW_SPAN = 1.0 / (2.0 * SPEED)
SPIN_SPAN = 2.0  # [s] the arc is the angle the body turns in this long
SPIN_RADIUS = 1.6  # [body radii]
SPIN_MOST = math.radians(300.0)  # the longest arc
ARC_STEP = math.radians(6.0)  # an arc is a polyline of steps this long at most
TABLE_FRAMES = 251  # the specks' table repeats after this many frames
SLOTS = 2  # the most specks a stream starts in one frame
STREAM_STEP = 97  # from one stream's rows of the table to the next's, so no two move alike
LIGHT_STREAMS = 64  # the streams of light drawn in come after the flames', which are fewer

Point = tuple[float, float]
Pose = tuple[float, float, float]  # x, y [u], heading [rad]
NOWHERE = np.zeros((0, 2))


class Specks:
    """Random draws for the specks, made once (invariant 1): for each frame of a cycle and each
    slot, whether a speck starts then, when within that frame, and where across its stream."""

    def __init__(self, seed: int = 0):
        self.table = np.random.default_rng(seed).random((TABLE_FRAMES, SLOTS, 3))

    def stream(
        self, density: float, frame: int, life: int, stream: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """The specks of one stream at `frame`: how far along its way each is, u in [0, 1), 0
        where it starts; and where across the stream, in [-1, 1]; two arrays (P,). `density`:
        specks alive at once, on average; `life`: frames from a speck's start to its end;
        `stream`: which stream, so that no two move alike."""
        if density <= 0.0:
            return np.zeros(0), np.zeros(0)
        ages = np.arange(life)
        rows = self.table[(frame - ages + STREAM_STEP * stream) % TABLE_FRAMES]  # (life, SLOTS, 3)
        started = np.minimum(SLOTS, np.floor(density / life + rows[:, 0, 0]))
        alive = np.arange(SLOTS)[None, :] < started[:, None]
        u = (ages[:, None] + rows[:, :, 1]) / life
        return u[alive], 2.0 * rows[:, :, 2][alive] - 1.0


SPECKS = Specks()


@dataclass(frozen=True)
class AtWork:
    """One swimmer at work, all in the plane [u]."""

    intake: np.ndarray  # (P, 2) the specks of light its eyes draw in
    flames: np.ndarray  # (Q, 2) the specks of its thrusters' flames
    eyes: np.ndarray  # (k, m, 2) each eye's outline; its face, the edge from last point to first
    thrusters: np.ndarray  # (j, m, 2) each thruster's, its face its back
    velocity: np.ndarray | None  # (2, 2) from the rim along the velocity; None while still
    spin: np.ndarray | None  # (m, 2) the arc from the heading; None while it does not turn


def at_work(
    arena: Arena,
    net: Network,
    cells: Sequence[Cell],
    y: np.ndarray,
    pose: Pose,
    radius: float,
    frame: int,
    specks: Specks = SPECKS,
) -> AtWork:
    """What a swimmer running `net` on a board of `cells`, its nodes at rates `y` (n,), shows
    at `pose` in `arena`, at `frame` of the run."""
    scale = part_scale(cells)
    eye_mount, eye_facing = parts(net, net.eyes)
    thr_mount, thr_facing = parts(net, net.thrusters)
    eyes = outlines(eye_mount, eye_facing, EYE_DISC, scale)
    thrusters = outlines(thr_mount, thr_facing, SQUARE_POINT, scale)
    vel, spin = motion(net, y, radius)
    centre, heading = pose[:2], pose[2]
    return AtWork(
        intake=intake(arena, eye_mount, eye_facing, eyes, pose, radius, frame, specks),
        flames=flames(y[net.thrusters], thr_facing, thrusters, pose, radius, frame, specks),
        eyes=to_plane(eyes, pose, radius),
        thrusters=to_plane(thrusters, pose, radius),
        velocity=velocity_segment(centre, heading, radius, vel),
        spin=spin_arc(centre, heading, radius, spin),
    )


def part_scale(cells: Sequence[Cell]) -> float:
    """A hex size of the board in body radii: the board's reach is the body's radius (D-018)."""
    _, reach = body_disc(cells)
    return 1.0 / reach if reach > 0.0 else 0.0


def outlines(
    mount: np.ndarray, facing: np.ndarray, shape: Sequence[Point], scale: float
) -> np.ndarray:
    """(k, m, 2): each part's outline on the body [body radii], `shape` (m points, hex sizes,
    forward +x) turned to its facing and scaled by `scale` [body radii per hex size]."""
    shape = np.asarray(shape, dtype=np.float64)
    angle = FACING_STEP * np.asarray(facing, dtype=np.float64)[:, None]
    cos, sin = np.cos(angle), np.sin(angle)
    x = mount[:, 0, None] + scale * (cos * shape[None, :, 0] - sin * shape[None, :, 1])
    y = mount[:, 1, None] + scale * (sin * shape[None, :, 0] + cos * shape[None, :, 1])
    return np.stack((x, y), axis=2).reshape(len(mount), len(shape), 2)


def to_plane(points: np.ndarray, pose: Pose, radius: float) -> np.ndarray:
    """Points on the body [body radii], any shape (..., 2), in the plane [u]."""
    x, y, heading = pose
    cos, sin = math.cos(heading), math.sin(heading)
    px, py = points[..., 0], points[..., 1]
    return np.stack((x + radius * (cos * px - sin * py), y + radius * (sin * px + cos * py)), -1)


def face(outline: np.ndarray) -> tuple[np.ndarray, float]:
    """The middle of a part's face, the edge from its outline's last point to its first, and
    half its length, in the outline's units."""
    a, b = outline[-1], outline[0]
    return 0.5 * (a + b), 0.5 * float(np.hypot(*(b - a)))


def flames(
    rates: np.ndarray,
    facing: np.ndarray,
    outline: np.ndarray,
    pose: Pose,
    radius: float,
    frame: int,
    specks: Specks = SPECKS,
) -> np.ndarray:
    """(P, 2) [u]: the specks of the flames of thrusters at `rates` (k,), facing `facing` (k,),
    with outlines (k, m, 2) on the body [body radii]: out of each one's back, FLAME_LENGTH long,
    as many as its rate."""
    found = [NOWHERE]
    for k, rate in enumerate(np.asarray(rates, dtype=np.float64) / RATE_MAX):
        start, half = face(outline[k])
        angle = FACING_STEP * float(facing[k])
        way = np.array([-math.cos(angle), -math.sin(angle)])  # out of the back
        side = np.array([-way[1], way[0]])
        u, across = specks.stream(FLAME_SPECKS * rate, frame, FLAME_LIFE, k)
        along = u * FLAME_LENGTH
        wide = across * (half + along * math.tan(FLAME_SPREAD))
        found.append(start + along[:, None] * way + wide[:, None] * side)
    return to_plane(np.concatenate(found), pose, radius)


def light_shares(
    arena: Arena, mount: np.ndarray, facing: np.ndarray, pose: Pose, radius: float
) -> tuple[np.ndarray, np.ndarray]:
    """What each light gives each eye's reading, (k, L) in [0, RATE_MAX], summing to what the
    eye reads (`optics.eye_rates`), and each eye's look (k, 2): the light it reads, shared out
    between the lights in proportion to what each gives it unshadowed."""
    x, y, heading = pose
    pos, turn, size = np.array([[x, y]]), np.array([heading]), np.array([radius])
    points, looks = eye_poses(pos, turn, size, mount, facing)
    points, looks = points[0], looks[0]
    given = exposure(points, looks, arena.light_xy, arena.light_power)
    centres, radii = discs(arena, pos, size)
    own = np.full(len(points), len(arena.obstacles))  # the body is transparent to its own parts
    seen = visible(points, arena.light_xy, centres, radii, skip=own)
    part = np.where(seen, given, 0.0)
    total = part.sum(axis=1, keepdims=True)
    return part * np.minimum(RATE_MAX, total) / np.maximum(total, TINY), looks


def intake(
    arena: Arena,
    mount: np.ndarray,
    facing: np.ndarray,
    outline: np.ndarray,
    pose: Pose,
    radius: float,
    frame: int,
    specks: Specks = SPECKS,
) -> np.ndarray:
    """(P, 2) [u]: the specks of light drawn into eyes at `mount` (k, 2) [body radii], facing
    `facing` (k,), with outlines (k, m, 2): into each face from each light it sees, along the
    light's direction, from INTAKE_LENGTH out, as many as that light gives the reading."""
    if len(mount) == 0 or len(arena.lights) == 0:
        return NOWHERE
    shares, looks = light_shares(arena, mount, facing, pose, radius)
    found = [NOWHERE]
    for k in range(len(mount)):
        middle, half = face(outline[k])
        end = to_plane(middle, pose, radius)
        for light, share in enumerate(shares[k] / RATE_MAX):
            if share <= 0.0:
                continue
            toward = arena.light_xy[light] - end
            far = float(np.hypot(*toward))
            if far <= LIGHT_RADIUS:
                continue
            way = toward / far
            side = np.array([-way[1], way[0]])
            cosine = max(0.0, float(looks[k] @ way))  # the face as the light sees it
            stream = LIGHT_STREAMS + k * len(arena.lights) + light
            u, across = specks.stream(INTAKE_SPECKS * share, frame, INTAKE_LIFE, stream)
            out = (1.0 - u) * min(INTAKE_LENGTH * radius, far - LIGHT_RADIUS)
            wide = across * (half * radius * cosine + out * math.tan(INTAKE_SPREAD))
            found.append(end + out[:, None] * way + wide[:, None] * side)
    return np.concatenate(found)


def motion(net: Network, y: np.ndarray, radius: float) -> tuple[np.ndarray, float]:
    """The velocity (2,) in the body's frame [u/s] and the spin [rad/s] that the thrust of
    rates `y` (n,) gives a body of `radius` [u] (D-022): what the next tick does."""
    size = np.array([radius])
    force, torque = thrust(thrust_rates(net, y[None, :]), size, *parts(net, net.thrusters))
    vel, spin = stokes(force, torque, size)
    return vel[0], float(spin[0])


def velocity_segment(
    centre: Point, heading: float, radius: float, vel: np.ndarray, span: float = VELOCITY_SPAN
) -> np.ndarray | None:
    """(2, 2) [u]: from the rim along the velocity `vel` (2,) [u/s, body frame], as long as the
    way gone in `span` [s]; None while the body is still."""
    cos, sin = math.cos(heading), math.sin(heading)
    v = np.array([cos * vel[0] - sin * vel[1], sin * vel[0] + cos * vel[1]])
    speed = float(np.hypot(*v))
    if speed * span <= TINY:
        return None
    start = np.asarray(centre, dtype=np.float64) + radius * v / speed
    return np.array([start, start + span * v])


def spin_arc(
    centre: Point, heading: float, radius: float, spin: float, span: float = SPIN_SPAN
) -> np.ndarray | None:
    """(m, 2) [u]: an arc SPIN_RADIUS body radii from the centre, from the heading, as long as
    the angle turned in `span` [s] at `spin` [rad/s], at most SPIN_MOST; None if it does not
    turn."""
    sweep = max(-SPIN_MOST, min(SPIN_MOST, spin * span))
    if abs(sweep) <= TINY:
        return None
    steps = max(1, math.ceil(abs(sweep) / ARC_STEP))
    angle = heading + np.linspace(0.0, sweep, steps + 1)
    x, y = centre
    reach = SPIN_RADIUS * radius
    return np.stack((x + reach * np.cos(angle), y + reach * np.sin(angle)), axis=1)
