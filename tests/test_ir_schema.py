import pytest
from pydantic import ValidationError
from src.ir.schema import PhysicsIR, PhysicsObject, Force, ForceDirection, RelativePosition

def test_valid_physics_ir():
    ir = PhysicsIR(
        objects=[
            PhysicsObject(id="box1", type="rectangle", position=RelativePosition(x=0, y=0))
        ],
        forces=[
            Force(id="gravity", on="box1", direction=ForceDirection.DOWN, magnitude="10N")
        ]
    )
    assert len(ir.objects) == 1
    assert ir.forces[0].direction == "DOWN"

def test_invalid_force_direction():
    with pytest.raises(ValidationError):
        Force(id="f1", on="box1", direction="INVALID_DIR", magnitude="10N")
