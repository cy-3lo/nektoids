"""How a swimmer moves through the fluid: Stokes flow round spheres, far-field RPY (D-601, D-602).

Spheres in 3D, centres in the plane, so only (Ux, Uy, Omega_z) couple to (Fx, Fy, T_z). With no
overlap only the far-field coefficients are needed. A source j (a sphere of radius a_j, or a
point force, a_j = 0) at distance R from a target i of radius a_i, R_hat from j to i:

    U_i     = eye F + hat R_hat (R_hat . F) + pf T x R_hat
    Omega_i = pf F x R_hat + rr T
    eye = (1 + s / 3R^2) / (8 pi mu R),  hat = (1 - s / R^2) / (8 pi mu R),  s = a_i^2 + a_j^2
    pf = 1 / (8 pi mu R^2),  rr = -1 / (16 pi mu R^3)

The swimmer propels itself (D-602): each thruster is a point force on its rim (D-605), the body
getting f there and the fluid -f, so it is force- and torque-free. For the fluid it is a sphere of
radius HYDRO R, turning against the drag of one of radius SPIN R; it is drawn, and meets
obstacles, as a sphere of radius R (D-045). Lights and obstacles are clamped spheres; their grand
mobility is inverted once (`clamped_inverse`), at rest, the springs of D-424 left out of it, and
the swimmer's flow reaches them where they are now. Each swimmer moves alone among them.

Pumps and sources stir the fluid (D-700). A pump is the stokeslet of a sphere of radius
STIR_RADIUS, its holder taking the reaction, so it is not clamped; a source puts out
u = Q R_hat / (4 pi R^2), harmonic. Faxén's laws give a sphere in either flow its velocity and
spin: for a pump, `apply`'s terms with the sum of the radii squared; for a source, u itself, its
Laplacian and vorticity being nil. Both are fixed, so what the clamped spheres hold against
their flow is solved once (`stirred_reactions`); neither feels the swimmer's flow back.

Every product is a broadcast and a sum along a fixed axis, never `@`, so a row does not depend
on the batch it is in (invariant 1). Lengths in u, forces in f, mu the game's. Pure numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, STIR_RADIUS, Arena
from nektoids.sim.contact import SPRING, drag
from nektoids.sim.motion import VISCOSITY

HYDRO = 0.5  # the swimmer's hydrodynamic radius, in body radii: thrusters 0.5 R outside it
SPIN = 0.75  # the radius whose rotational drag it has, in body radii: struts and thrusters add
# more drag to turning than to moving; HYDRO's would turn it 7 times as fast as D-022's
BLOB = 0.25  # [u] the core a point's flow sees round a point force: no singularity (D-603)
TOUCH = 0.01  # [u] a body this near a light or an obstacle touches it: one sliding along it
# drifts (V dt)^2 / 2(R + r), about 1e-3 u, off it each tick (D-609)
CONTACT_PASSES = 3  # over the lights and obstacles a body touches, each held in turn

_C = 1.0 / (8.0 * np.pi * VISCOSITY)


@dataclass(frozen=True)
class Swim:
    """One tick's solve for N swimmers, in the world's frame."""

    velocity: np.ndarray  # (N, 2) [u/s]
    spin: np.ndarray  # (N,) [rad/s]
    load: np.ndarray  # (N, 3) what each body puts on the fluid, its thrusters' and contacts'
    # force [f] and torque [f u] about its centre
    tips: np.ndarray  # (N, k, 2) the thrusters [u]
    forces: np.ndarray  # (N, k, 2) what each pushes its body with [f]; the fluid gets the opposite
    reactions: np.ndarray  # (N, M, 3) force and torque the fluid puts on each clamped sphere
    contact: np.ndarray  # (N, 2) [f] what the lights and obstacles touched push each body with
    pushes: np.ndarray  # (M, 2) [f] what the bodies push each obstacle with, against its spring


def apply(dx, dy, s, fx, fy, tz) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(Ux, Uy, Omega_z), each (..., ), of targets at offsets (dx, dy) (..., q) [u] from q sources
    with forces (fx, fy) and torques tz, broadcast to (..., q), summed over the sources."""
    r2 = dx * dx + dy * dy
    r = np.sqrt(r2)
    rx, ry = dx / r, dy / r
    eye = _C * (1.0 + s / (3.0 * r2)) / r
    hat = _C * (1.0 - s / r2) / r
    pf = _C / r2
    along = hat * (rx * fx + ry * fy)
    ux = eye * fx + along * rx - pf * ry * tz
    uy = eye * fy + along * ry + pf * rx * tz
    om = pf * (ry * fx - rx * fy) - 0.5 * pf / r * tz
    return ux.sum(axis=-1), uy.sum(axis=-1), om.sum(axis=-1)


def clamped(arena: Arena) -> tuple[np.ndarray, np.ndarray]:
    """Centres (M, 2) [u] and radii (M,) [u] of the clamped spheres, lights then obstacles, where
    they are now."""
    xy = np.concatenate((arena.light_xy, arena.disc_xy))
    radius = np.concatenate((np.full(len(arena.lights), LIGHT_RADIUS), arena.disc_radius))
    return xy, radius


def grand_mobility(xy: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """(3M, 3M): the grand mobility of M spheres at xy (M, 2) [u] of radius (M,) [u], none
    overlapping."""
    m = xy.shape[0]
    sum2 = radius[:, None] ** 2 + radius[None, :] ** 2
    out = np.zeros((m, 3, m, 3))
    dx = xy[:, None, 0] - xy[None, :, 0] + np.eye(m)  # the diagonal is replaced below
    dy = xy[:, None, 1] - xy[None, :, 1]
    off = 1.0 - np.eye(m)
    for k in range(3):  # the response to a unit load k on every sphere j, one at a time
        load = [off * (k == 0), off * (k == 1), off * (k == 2)]
        r2 = dx * dx + dy * dy
        r = np.sqrt(r2)
        rx, ry = dx / r, dy / r
        eye = _C * (1.0 + sum2 / (3.0 * r2)) / r
        hat = _C * (1.0 - sum2 / r2) / r
        pf = _C / r2
        along = hat * (rx * load[0] + ry * load[1])
        out[:, 0, :, k] = eye * load[0] + along * rx - pf * ry * load[2]
        out[:, 1, :, k] = eye * load[1] + along * ry + pf * rx * load[2]
        out[:, 2, :, k] = pf * (ry * load[0] - rx * load[1]) - 0.5 * pf / r * load[2]
    own = np.stack((6 * np.pi * radius, 6 * np.pi * radius, 8 * np.pi * radius**3), axis=1)
    diag = np.arange(m)
    out[diag, :, diag, :] = np.eye(3)[None] / (VISCOSITY * own[:, None, :])
    return out.reshape(3 * m, 3 * m)


def clamped_inverse(arena: Arena) -> np.ndarray:
    """(3M, 3M): the inverse of the clamped spheres' grand mobility at rest (D-601)."""
    xy = np.concatenate((arena.light_xy, arena.rest_xy))
    radius = np.concatenate((np.full(len(arena.lights), LIGHT_RADIUS), arena.disc_radius))
    if len(xy) == 0:
        return np.zeros((0, 0))
    return np.linalg.inv(grand_mobility(xy, radius))


def stirred(
    arena: Arena, x: np.ndarray, a: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(Ux, Uy, Omega_z), each (P,), of spheres of radius a (P,) [u] at x (P, 2) [u] in the flow
    of the pumps and sources alone (D-700); a point inside one taken as on its surface."""
    p = len(x)
    ux, uy, om = np.zeros(p), np.zeros(p), np.zeros(p)
    if arena.pumps:
        dx, dy = _held_off(x, arena.pump_xy)
        f = arena.pump_force
        ux, uy, om = apply(dx, dy, (a * a)[:, None] + STIR_RADIUS**2, f[:, 0], f[:, 1], 0.0)
    if arena.sources:
        dx, dy = _held_off(x, arena.source_xy)
        r2 = dx * dx + dy * dy
        out = arena.source_rate / (4.0 * np.pi * r2 * np.sqrt(r2))
        ux, uy = ux + (out * dx).sum(axis=1), uy + (out * dy).sum(axis=1)
    return ux, uy, om


def _held_off(x: np.ndarray, centres: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Offsets (P, Q) [u] of points x (P, 2) from pumps or sources at centres (Q, 2), each no
    nearer than STIR_RADIUS: bounded inside one, and a point on its centre taken along +x."""
    dx, dy = x[:, None, 0] - centres[None, :, 0], x[:, None, 1] - centres[None, :, 1]
    r = np.sqrt(dx * dx + dy * dy)
    dx, r = np.where(r > 0.0, dx, STIR_RADIUS), np.where(r > 0.0, r, STIR_RADIUS)
    scale = np.maximum(r, STIR_RADIUS) / r
    return dx * scale, dy * scale


def stirred_reactions(arena: Arena) -> np.ndarray:
    """(K, 3): the force [f] and torque [f u] each light and obstacle, held at rest, puts on the
    fluid against the pumps' and sources' flow (D-700), by `clamped_inverse`."""
    xy = np.concatenate((arena.light_xy, arena.rest_xy))
    m = xy.shape[0]
    if m == 0 or not (arena.pumps or arena.sources):
        return np.zeros((m, 3))
    radius = np.concatenate((np.full(len(arena.lights), LIGHT_RADIUS), arena.disc_radius))
    induced = np.stack(stirred(arena, xy, radius), axis=1).reshape(1, 3 * m)
    return -(arena.clamped_inverse * induced).sum(axis=1).reshape(m, 3)


def _stir(
    arena: Arena, pos: np.ndarray, a: np.ndarray, velocity, spin, reactions
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Velocity, spin and reactions of bodies at pos (N, 2) [u] of hydrodynamic radius a (N,),
    with the flow of the pumps and sources and of what the clamped spheres hold against it
    added (D-700); unchanged, bit for bit, in a plane with neither."""
    if not (arena.pumps or arena.sources):
        return velocity, spin, reactions
    ux, uy, om = stirred(arena, pos, a)
    xy, size = clamped(arena)
    if len(xy):
        held = arena.stirred_reactions
        bx, by, bo = apply(
            pos[:, None, 0] - xy[None, :, 0],
            pos[:, None, 1] - xy[None, :, 1],
            (a * a)[:, None] + (size * size)[None, :],
            held[:, 0],
            held[:, 1],
            held[:, 2],
        )
        ux, uy, om = ux + bx, uy + by, om + bo
        reactions = reactions + held[None]
    return velocity + np.stack((ux, uy), axis=1), spin + om, reactions


def swim(
    arena: Arena, pos: np.ndarray, radius: np.ndarray, tips: np.ndarray, forces: np.ndarray
) -> Swim:
    """The motion of N swimmers at pos (N, 2) [u] of radius (N,) [u], each pushed by k point
    forces (N, k, 2) [f] at tips (N, k, 2) [u], the fluid getting the opposite there. A force
    inside the hydrodynamic sphere, or on it, moves nothing (D-602) and is left out.

    The pumps and sources carry it and turn it (D-700), and it meets them as it meets a light.

    A body touching a light or an obstacle is pushed by it along their centres, frictionless
    (D-609), as hard as it takes for the body to close in no faster than the other gives: a
    light not at all, an obstacle as its drag and spring let it, zeta du/dt = C - k u (D-424).
    That force is the body's, so the fluid gets it too: pinned, its thrust held, the body pumps.
    The obstacles get `pushes`, which `contact.collide` moves them by."""
    pos = np.asarray(pos, dtype=np.float64).reshape(-1, 2)
    radius = np.asarray(radius, dtype=np.float64)
    a, b = HYDRO * radius, SPIN * radius
    arm_x, arm_y = tips[..., 0] - pos[:, None, 0], tips[..., 1] - pos[:, None, 1]
    outside = arm_x * arm_x + arm_y * arm_y > (a * a)[:, None]
    forces = np.where(outside[..., None], forces, 0.0)
    tips = np.where(outside[..., None], tips, pos[:, None, :] + np.stack((a, 0 * a), 1)[:, None])
    arm_x, arm_y = tips[..., 0] - pos[:, None, 0], tips[..., 1] - pos[:, None, 1]
    fx, fy = forces[..., 0], forces[..., 1]
    thrust = np.stack((fx.sum(axis=1), fy.sum(axis=1), (arm_x * fy - arm_y * fx).sum(axis=1)), 1)
    load = thrust
    velocity, spin, reactions = _respond(arena, pos, a, b, load, tips, fx, fy)
    velocity, spin, reactions = _stir(arena, pos, a, velocity, spin, reactions)
    lights = len(arena.solid_xy)  # what gives nothing: lights, pumps and sources
    centres = np.concatenate((arena.solid_xy, arena.disc_xy))  # (K, 2): those, then obstacles
    reach = np.concatenate((arena.solid_radius, arena.disc_radius))
    gives = np.concatenate((np.zeros(lights), 1.0 / drag(arena.disc_radius)))  # 1 / zeta [u/f s]
    away = pos[:, None, :] - centres[None]  # (N, K, 2)
    far = np.sqrt((away * away).sum(axis=2))
    normal = away / np.maximum(far, 1e-12)[..., None]  # out of each, towards the body
    touch = far <= radius[:, None] + reach[None] + TOUCH
    offsets = arena.offsets if arena.offsets is not None else arena.at_rest
    pushed = -(offsets[None] * normal[:, lights:]).sum(axis=2)  # (N, M) [u] given, away from it
    preload = np.concatenate((np.zeros((len(pos), lights)), SPRING * pushed * gives[lights:]), 1)
    held = np.zeros(far.shape)  # (N, K) [f], each contact's force, along its normal
    if touch.any():
        none = np.zeros_like(fx)
        units = [
            _respond(arena, pos, a, b, np.tile(unit, (len(pos), 1)), tips, none, none)
            for unit in (np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]))
        ]
        for _ in range(CONTACT_PASSES):  # each contact in turn, a few passes over them
            for k in range(len(centres)):
                if not touch[:, k].any():
                    continue
                nx, ny = normal[:, k, 0], normal[:, k, 1]
                give = [  # the response to a unit push along the normal: velocity, spin, held
                    _rows(nx, units[0][q]) + _rows(ny, units[1][q]) for q in range(3)
                ]
                along = give[0][:, 0] * nx + give[0][:, 1] * ny  # > 0: a mobility
                into = -(velocity[:, 0] * nx + velocity[:, 1] * ny)  # how fast it closes in
                # the body closes in as fast as the touched one gives: zeta du/dt = C - k u
                need = (into + held[:, k] * along + preload[:, k]) / (along + gives[k])
                more = np.where(touch[:, k], np.maximum(0.0, need), 0.0)
                step, held[:, k] = more - held[:, k], more
                velocity = velocity + step[:, None] * give[0]
                spin = spin + step * give[1]
                reactions = reactions + step[:, None, None] * give[2]
                load = load + step[:, None] * np.stack((nx, ny, 0 * nx), axis=1)
    contact = (held[..., None] * normal).sum(axis=1)
    pushes = -(held[:, lights:, None] * normal[:, lights:]).sum(axis=0)  # (M, 2) on obstacles
    return Swim(velocity, spin, load, tips, forces, reactions, contact, pushes)


def _rows(scale: np.ndarray, array: np.ndarray) -> np.ndarray:
    """`array` (N, ...) with each row times scale (N,)."""
    return scale.reshape(-1, *([1] * (array.ndim - 1))) * array


def _respond(
    arena: Arena,
    pos: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    load: np.ndarray,
    tips: np.ndarray,
    fx: np.ndarray,
    fy: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Velocity (N, 2) [u/s], spin (N,) [rad/s] and the held spheres' reactions (N, M, 3) of
    bodies of hydrodynamic radius a (N,) [u], turning as of radius b (N,) [u], that put `load`
    (N, 3) [f, f u] on the fluid, and point forces -(fx, fy) (N, k) [f] at tips (N, k, 2) [u]."""
    n = pos.shape[0]
    arm_x, arm_y = tips[..., 0] - pos[:, None, 0], tips[..., 1] - pos[:, None, 1]
    # its own drag, and the flow of its thrusters' reactions at its centre
    drag = 6.0 * np.pi * VISCOSITY * a
    ux, uy, om = apply(-arm_x, -arm_y, (a * a)[:, None], -fx, -fy, 0.0)
    velocity = np.stack((load[:, 0] / drag + ux, load[:, 1] / drag + uy), axis=1)
    spin = load[:, 2] / (8.0 * np.pi * VISCOSITY * b**3) + om
    xy, size = clamped(arena)
    m = xy.shape[0]
    if m == 0:
        return velocity, spin, np.zeros((n, 0, 3))
    # the clamped spheres, held: the flow of the swimmer and of the reactions at each
    sx = np.concatenate((pos[:, None, 0], tips[..., 0]), axis=1)  # (N, 1 + k)
    sy = np.concatenate((pos[:, None, 1], tips[..., 1]), axis=1)
    own = np.concatenate(((a * a)[:, None], np.zeros_like(fx)), axis=1)
    gx = np.concatenate((load[:, :1], -fx), axis=1)
    gy = np.concatenate((load[:, 1:2], -fy), axis=1)
    gt = np.concatenate((load[:, 2:], np.zeros_like(fx)), axis=1)
    ux, uy, om = apply(
        xy[None, :, None, 0] - sx[:, None, :],
        xy[None, :, None, 1] - sy[:, None, :],
        (size * size)[None, :, None] + own[:, None, :],
        gx[:, None, :],
        gy[:, None, :],
        gt[:, None, :],
    )  # (N, M) each
    induced = np.stack((ux, uy, om), axis=2).reshape(n, 1, 3 * m)
    reactions = -(arena.clamped_inverse[None] * induced).sum(axis=2).reshape(n, m, 3)
    # back at the swimmer: the flow of what holds them
    ux, uy, om = apply(
        pos[:, None, 0] - xy[None, :, 0],
        pos[:, None, 1] - xy[None, :, 1],
        (a * a)[:, None] + (size * size)[None, :],
        reactions[..., 0],
        reactions[..., 1],
        reactions[..., 2],
    )
    return velocity + np.stack((ux, uy), axis=1), spin + om, reactions


FAINT = 0.02  # [u/s] the water a Hair reads on a log scale above: below, nearly in proportion
FULL = 1.0  # [u/s] the water past it that a Hair reads RATE_MAX for (D-708)


def felt(speed: np.ndarray) -> np.ndarray:
    """A Hair's rate for water `speed` [u/s] >= 0 past it the way it points, on a log scale, as
    a sense organ compresses (D-708): log(1 + u/FAINT) / log(1 + FULL/FAINT), 0 for still water,
    1 at FULL, about u/FAINT/log(1 + FULL/FAINT) for the faintest; the caller caps it."""
    return np.log1p(speed / FAINT) / np.log1p(FULL / FAINT)


RELATIVE = False  # a Hair reads the water past the plane, not past itself: D-700's first try


def hair_rates(
    arena: Arena,
    pos: np.ndarray,
    heading: np.ndarray,
    radius: np.ndarray,
    mount: np.ndarray,
    facing: np.ndarray,
    swum: Swim | None = None,
) -> np.ndarray:
    """(N, k, C): what the k Hairs of each of N bodies read, the same in each channel:
    `felt`(max(0, u . n)), u the flow at each, all but its own body's (D-700): the pumps' and the
    sources', and what the lights and obstacles hold against it and against the body's own flow,
    `swum`'s reactions, its echo; with RELATIVE, less the Hair's own velocity, V + Omega x r.
    Arguments as for `optics.eye_poses`; with no `swum`, no echo and the body still."""
    from nektoids.graph.dynamics import CHANNELS
    from nektoids.sim.optics import eye_poses

    points, looks = eye_poses(pos, heading, radius, mount, facing)  # (N, k, 2) each
    n, k = points.shape[:2]
    flat = points.reshape(-1, 2)
    ux, uy, _ = stirred(arena, flat, np.zeros(n * k))
    ux, uy = ux.reshape(n, k), uy.reshape(n, k)
    xy, size = clamped(arena)
    if swum is not None and len(xy):
        held = swum.reactions  # (N, M, 3)
        dx = points[:, :, None, 0] - xy[None, None, :, 0]
        dy = points[:, :, None, 1] - xy[None, None, :, 1]
        r = np.sqrt(dx * dx + dy * dy)
        scale = np.maximum(r, size) / np.maximum(r, 1e-12)  # held at its radius inside
        ex, ey, _ = apply(
            dx * scale,
            dy * scale,
            (size * size)[None, None, :],
            held[:, None, :, 0],
            held[:, None, :, 1],
            held[:, None, :, 2],
        )
        ux, uy = ux + ex, uy + ey
    if RELATIVE and swum is not None:
        arm_x, arm_y = points[..., 0] - pos[:, None, 0], points[..., 1] - pos[:, None, 1]
        spin = swum.spin[:, None]
        ux = ux - swum.velocity[:, None, 0] + spin * arm_y
        uy = uy - swum.velocity[:, None, 1] - spin * arm_x
    past = np.maximum(0.0, ux * looks[..., 0] + uy * looks[..., 1])
    return np.repeat(felt(past)[..., None], CHANNELS, axis=2)


def flow_at(arena: Arena, x: np.ndarray, pos: np.ndarray, radius: float, swum: Swim) -> np.ndarray:
    """(P, 2): the flow [u/s] at points x (P, 2) [u] round the first swimmer of `swum`, at pos
    (2,) [u], of `radius` [u]: the swimmer and the clamped spheres as spheres (stokeslet with its
    Faxén term, rotlet), the reactions as point forces with a core BLOB, and the pumps' and
    sources' flow (D-700). Inside a source the distance is held at its radius: bounded, and on a
    sphere's surface its rigid motion, 0 for a clamped one."""
    sx, sy, a, fx, fy, tz = _singularities(arena, pos, radius, swum)
    dx, dy = _held_at(x, sx, sy, a)
    ux, uy, _ = apply(dx, dy, a * a, fx, fy, tz)
    if arena.pumps or arena.sources:
        sx, sy, _ = stirred(arena, x, np.zeros(len(x)))
        ux, uy = ux + sx, uy + sy
    return np.stack((ux, uy), axis=1)


def rise_at(arena: Arena, x: np.ndarray, pos: np.ndarray, radius: float, swum: Swim) -> np.ndarray:
    """(P,): dw/dz [1/s] at points x (P, 2) [u] in the plane, of the flow `flow_at` gives: how
    fast the fluid leaves the plane, up and down, where positive, and comes into it where
    negative; the in-plane flow's divergence, negated (D-704). A rotlet keeps to the plane; a
    sphere's stokeslet F, with its Faxén term, rises as hat (R . F) / R^2, a source as
    Q / (4 pi R^3), each distance held at the radius as `flow_at` holds it."""
    sx, sy, a, fx, fy, _ = _singularities(arena, pos, radius, swum)
    dx, dy = _held_at(x, sx, sy, a)
    rise = _rising(dx, dy, a * a, fx, fy)
    if arena.pumps:
        dx, dy = _held_off(x, arena.pump_xy)
        f = arena.pump_force
        rise = rise + _rising(dx, dy, STIR_RADIUS**2, f[:, 0], f[:, 1])
    if arena.sources:
        dx, dy = _held_off(x, arena.source_xy)
        r2 = dx * dx + dy * dy
        rise = rise + (arena.source_rate / (4.0 * np.pi * r2 * np.sqrt(r2))).sum(axis=1)
    return rise


def _rising(dx, dy, s, fx, fy) -> np.ndarray:
    """(P,): dw/dz of point forces (fx, fy) (q,) [f] of radius squared s at offsets (dx, dy)
    (P, q) [u] from them, summed over them: hat (R . F) / R^2."""
    r2 = dx * dx + dy * dy
    r = np.sqrt(r2)
    hat = _C * (1.0 - s / r2) / r
    return (hat * (dx * fx + dy * fy) / r2).sum(axis=1)


def _singularities(arena: Arena, pos: np.ndarray, radius: float, swum: Swim):
    """Centres (Q,) [u] x and y, radii (Q,) [u], forces (Q,) [f] x and y and torques (Q,) [f u]
    of what makes the first swimmer's flow: its body, the clamped spheres and its thrusters'
    reactions, cored by BLOB."""
    xy, size = clamped(arena)
    tips, forces = swum.tips[0], swum.forces[0]
    sx = np.concatenate(([pos[0]], xy[:, 0], tips[:, 0]))
    sy = np.concatenate(([pos[1]], xy[:, 1], tips[:, 1]))
    a = np.concatenate(([HYDRO * radius], size, np.full(len(tips), BLOB)))
    load, held = swum.load[0], swum.reactions[0]
    fx = np.concatenate(([load[0]], held[:, 0], -forces[:, 0]))
    fy = np.concatenate(([load[1]], held[:, 1], -forces[:, 1]))
    tz = np.concatenate(([load[2]], held[:, 2], np.zeros(len(tips))))
    return sx, sy, a, fx, fy, tz


def _held_at(x: np.ndarray, sx, sy, a) -> tuple[np.ndarray, np.ndarray]:
    """Offsets (P, Q) [u] of points x (P, 2) from centres (sx, sy) (Q,), each no nearer than its
    radius a (Q,)."""
    dx, dy = x[:, None, 0] - sx[None], x[:, None, 1] - sy[None]
    r = np.sqrt(dx * dx + dy * dy)
    scale = np.maximum(r, a) / np.maximum(r, 1e-12)  # held at the radius inside
    return dx * scale, dy * scale
