from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any


# =========================================================
# BASIC TYPES
# =========================================================

class RelativePosition(BaseModel):
    x: float
    y: float


# =========================================================
# FORCE SYSTEM
# =========================================================

class ForceDirection(str, Enum):
    DOWN = "DOWN"
    UP = "UP"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    PERPENDICULAR_TO_SURFACE = "PERPENDICULAR_TO_SURFACE"

    ALONG_SLOPE_UP = "ALONG_SLOPE_UP"
    ALONG_SLOPE_DOWN = "ALONG_SLOPE_DOWN"

    TANGENT_TO_PATH = "TANGENT_TO_PATH"
    RADIAL_INWARD = "RADIAL_INWARD"

    CUSTOM = "CUSTOM"


class Force(BaseModel):
    id: str

    # object id
    on: str

    direction: ForceDirection

    # only used if direction == CUSTOM
    custom_angle_deg: Optional[float] = Field(None, description="Angle in degrees, only used if direction is CUSTOM.")

    # e.g. "mg", "N", "f_k"
    magnitude: str = Field(..., description="Symbolic or numeric magnitude, e.g. 'mg', '10', 'N', '0.1 * N'.")

    label: Optional[str] = Field(None, description="Display label for the force arrow.")


# =========================================================
# PHYSICS OBJECTS
# =========================================================

class PhysicsObjectType(str, Enum):
    BLOCK = "BLOCK"
    BALL = "BALL"
    CIRCLE = "CIRCLE"
    RECTANGLE = "RECTANGLE"

    SPRING = "SPRING"
    PULLEY = "PULLEY"
    ROPE = "ROPE"

    VEHICLE = "VEHICLE"
    SKATEBOARD = "SKATEBOARD"

    CUSTOM = "CUSTOM"


class PhysicsObject(BaseModel):
    id: str

    type: PhysicsObjectType

    label: Optional[str] = None

    # initial position
    position: Optional[RelativePosition] = None

    angle_deg: float = 0.0

    mass_kg: Optional[float] = None


# =========================================================
# TRACK / PATH SYSTEM
# =========================================================

class TrackSegmentType(str, Enum):
    LINE = "LINE"

    ARC = "ARC"

    BEZIER = "BEZIER"

    PARABOLA = "PARABOLA"

    CUSTOM = "CUSTOM"


class TrackSegment(BaseModel):
    id: str

    type: TrackSegmentType

    start: RelativePosition

    end: RelativePosition

    # =========================
    # ARC PROPERTIES
    # =========================

    radius: Optional[float] = Field(None, description="Radius of the arc. Required for ARC segments if center is not provided.")

    center: Optional[RelativePosition] = Field(None, description="Center position of the arc. Strongly recommended for ARC segments.")

    angle_deg: Optional[float] = Field(None, description="Sweep angle in degrees. Positive for CCW, negative for CW.")

    clockwise: bool = Field(False, description="Whether the arc is drawn clockwise. Default is False (CCW).")

    # =========================
    # SURFACE PROPERTIES
    # =========================

    friction_coefficient: float = Field(0.0, description="Coefficient of kinetic friction (mu_k) for this segment.")

    label: Optional[str] = Field(None, description="Label for this segment (e.g., 'A-B').")


class Track(BaseModel):
    id: str

    segments: List[TrackSegment]


# =========================================================
# MOTION SYSTEM
# =========================================================

class MotionType(str, Enum):
    STATIC = "STATIC"

    FOLLOW_TRACK = "FOLLOW_TRACK"

    LINEAR = "LINEAR"

    ROTATION = "ROTATION"


class Motion(BaseModel):
    id: str

    object_id: str

    type: MotionType

    # for FOLLOW_TRACK
    track_id: Optional[str] = None

    # order of traversal
    segment_ids: Optional[List[str]] = None

    start_time: float = 0.0

    duration: float = 3.0


# =========================================================
# ANNOTATIONS
# =========================================================

class Annotation(BaseModel):
    id: str

    text: str

    position: RelativePosition


# =========================================================
# CAMERA (OPTIONAL)
# =========================================================

class CameraAction(BaseModel):
    id: str

    type: Literal[
        "zoom_in",
        "zoom_out",
        "follow_object",
        "pan"
    ]

    target_object_id: Optional[str] = None


# =========================================================
# ROOT IR
# =========================================================

class PhysicsIR(BaseModel):

    # physical entities
    objects: List[PhysicsObject]

    # force vectors
    forces: List[Force]

    # environment geometry
    tracks: List[Track]

    # movement instructions
    motions: List[Motion]

    # text/math labels
    annotations: List[Annotation]

    # optional cinematic control
    camera_actions: Optional[List[CameraAction]] = None