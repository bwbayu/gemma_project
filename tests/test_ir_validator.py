import pytest
from src.ir.schema import PhysicsIR, PhysicsObject, Force, ForceDirection, RelativePosition
from src.ir.validator import validate_ir

def test_validate_gravity_must_be_down():
    ir = PhysicsIR(
        objects=[PhysicsObject(id="box1", type="rectangle", position=RelativePosition(x=0, y=0))],
        forces=[Force(id="gravity", on="box1", direction=ForceDirection.UP)]
    )
    errors = validate_ir(ir)
    assert any("gravity must be DOWN" in err for err in errors)

def test_validate_unknown_object():
    ir = PhysicsIR(
        objects=[PhysicsObject(id="box1", type="rectangle", position=RelativePosition(x=0, y=0))],
        forces=[Force(id="f1", on="unknown_box", direction=ForceDirection.RIGHT)]
    )
    errors = validate_ir(ir)
    assert any("unknown object" in err for err in errors)

def test_validate_missing_position():
    ir = PhysicsIR(
        objects=[PhysicsObject(id="box1", type="rectangle")],
        forces=[]
    )
    errors = validate_ir(ir)
    assert any("has no position" in err for err in errors)

def test_validate_custom_angle_missing():
    ir = PhysicsIR(
        objects=[PhysicsObject(id="box1", type="rectangle", position=RelativePosition(x=0, y=0))],
        forces=[Force(id="f1", on="box1", direction=ForceDirection.CUSTOM)]
    )
    errors = validate_ir(ir)
    assert any("requires custom_angle_deg" in err for err in errors)
