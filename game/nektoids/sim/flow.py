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

Every product is a broadcast and a sum along a fixed axis, never `@`, so a row does not depend
on the batch it is in (invariant 1). Lengths in u, forces in f, mu the game's. Pure numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nektoids.sim.arena import LIGHT_RADIUS, Arena
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


def swim(
    arena: Arena, pos: np.ndarray, radius: np.ndarray, tips: np.ndarray, forces: np.ndarray
) -> Swim:
    """The motion of N swimmers at pos (N, 2) [u] of radius (N,) [u], each pushed by k point
    forces (N, k, 2) [f] at tips (N, k, 2) [u], the fluid getting the opposite there. A force
    inside the hydrodynamic sphere, or on it, moves nothing (D-602) and is left out.

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
    lights = len(arena.lights)
    centres = np.concatenate((arena.light_xy, arena.disc_xy))  # (K, 2): lights, then obstacles
    reach = np.concatenate((np.full(lights, LIGHT_RADIUS), arena.disc_radius))
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


def flow_at(arena: Arena, x: np.ndarray, pos: np.ndarray, radius: float, swum: Swim) -> np.ndarray:
    """(P, 2): the flow [u/s] at points x (P, 2) [u] round the first swimmer of `swum`, at pos
    (2,) [u], of `radius` [u]: the swimmer and the clamped spheres as spheres (stokeslet with its
    Faxén term, rotlet), the reactions as point forces with a core BLOB. Inside a source the
    distance is held at its radius: bounded, and on a sphere's surface its rigid motion, 0 for
    a clamped one."""
    xy, size = clamped(arena)
    tips, forces = swum.tips[0], swum.forces[0]
    sx = np.concatenate(([pos[0]], xy[:, 0], tips[:, 0]))
    sy = np.concatenate(([pos[1]], xy[:, 1], tips[:, 1]))
    a = np.concatenate(([HYDRO * radius], size, np.full(len(tips), BLOB)))
    load, held = swum.load[0], swum.reactions[0]
    fx = np.concatenate(([load[0]], held[:, 0], -forces[:, 0]))
    fy = np.concatenate(([load[1]], held[:, 1], -forces[:, 1]))
    tz = np.concatenate(([load[2]], held[:, 2], np.zeros(len(tips))))
    dx, dy = x[:, None, 0] - sx[None], x[:, None, 1] - sy[None]
    r = np.sqrt(dx * dx + dy * dy)
    scale = np.maximum(r, a) / np.maximum(r, 1e-12)  # held at the radius inside
    ux, uy, _ = apply(dx * scale, dy * scale, a * a, fx, fy, tz)
    return np.stack((ux, uy), axis=1)
