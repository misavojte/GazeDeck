"""Core type definitions using Pydantic v2."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SceneCoords(BaseModel):
    """Coordinates in scene frame."""

    model_config = ConfigDict(frozen=True)

    x: float
    y: float
    frame: Literal["scene_px", "scene_norm"] = "scene_px"


class HomographyInfo(BaseModel):
    """Homography information for image-to-screen mapping."""

    model_config = ConfigDict(frozen=True)

    H: list[list[float]]  # 3x3 homography matrix
    ts: int  # timestamp in milliseconds
    age_ms: int  # age in milliseconds
    reproj_px: float  # mean reprojection error in pixels
    markers: int  # number of markers used
    screen_w: int  # screen width in pixels
    screen_h: int  # screen height in pixels
    img_w: int  # image width in pixels
    img_h: int  # image height in pixels
    seq: int  # sequence number that increments on meaningful change


class PlaneCoords(BaseModel):
    """Coordinates in plane/screen space."""

    model_config = ConfigDict(frozen=True)

    uid: str = "screen-1"
    x: float | None = None
    y: float | None = None
    on_surface: bool = False
    visible: bool = False
    homography: HomographyInfo | None = None


class GazeSample(BaseModel):
    """Raw gaze sample from provider."""

    model_config = ConfigDict(frozen=True)

    ts_ms: int
    x: float
    y: float
    frame: Literal["scene_px", "scene_norm"] = "scene_px"
    conf: float = Field(default=1.0, ge=0.0, le=1.0)


class SceneFrame(BaseModel):
    """Scene frame metadata."""

    model_config = ConfigDict(frozen=True)

    ts_ms: int
    w: int
    h: int


class GazeEvent(BaseModel):
    """Complete gaze event with scene and plane coordinates."""

    model_config = ConfigDict(frozen=True)

    ts: int
    conf: float = Field(ge=0.0, le=1.0)
    scene: SceneCoords
    plane: PlaneCoords
