"""Structural checks on a parsed `PhysicsIR` before it is handed to the compiler."""

from typing import List
from .schema import PhysicsIR, ForceDirection

def validate_ir(ir: PhysicsIR) -> List[str]:
    errors = []

    # Gravity must point DOWN.
    gravity_forces = [f for f in ir.forces if f.id == "gravity" or "grav" in f.id.lower()]
    for f in gravity_forces:
        if f.direction != ForceDirection.DOWN:
            errors.append(f"CONSTRAINT_FAIL: force '{f.id}' gravity must be DOWN, got {f.direction}")

    # Every force must reference an existing object.
    obj_ids = {o.id for o in ir.objects}
    for f in ir.forces:
        if f.on not in obj_ids:
            errors.append(f"CONSTRAINT_FAIL: force '{f.id}' references unknown object '{f.on}'")

    # Every object must have a position.
    for o in ir.objects:
        if o.position is None:
            errors.append(f"CONSTRAINT_FAIL: object '{o.id}' has no position")

    # CUSTOM direction requires a custom_angle_deg.
    for f in ir.forces:
        if f.direction == ForceDirection.CUSTOM and f.custom_angle_deg is None:
            errors.append(f"CONSTRAINT_FAIL: force '{f.id}' CUSTOM direction requires custom_angle_deg")

    return errors
