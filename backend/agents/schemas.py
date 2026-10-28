from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Template = Literal["TextReveal", "Flowchart", "SocialMockup", "SearchBar", "DeviceMockup", "CallToAction"]
TEMPLATES = ["TextReveal", "Flowchart", "SocialMockup", "SearchBar", "DeviceMockup", "CallToAction"]
Hex = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class OrchestratorOut(BaseModel):
    productName: str = Field(min_length=1, max_length=40)
    audience: str = Field(min_length=1, max_length=120)
    tone: str = Field(min_length=1, max_length=80)
    keyMessage: str = Field(min_length=1, max_length=160)
    sceneCount: int = Field(ge=3, le=6)


class PlanScene(BaseModel):
    template: Template
    purpose: str = Field(min_length=1, max_length=160)
    durationSec: float = Field(ge=1.5, le=6)


class PlannerOut(BaseModel):
    scenes: List[PlanScene] = Field(min_length=2, max_length=6)


class CopyScene(BaseModel):
    headline: str = Field(min_length=1, max_length=70)
    subline: str = Field(default="", max_length=140)
    eyebrow: str = Field(default="", max_length=32)
    steps: List[str] = Field(default_factory=list, max_length=4)
    button: str = Field(default="", max_length=32)
    label: str = Field(default="", max_length=48)
    query: str = Field(default="", max_length=60)
    post: str = Field(default="", max_length=180)
    voiceover: str = Field(default="", max_length=220)


class CopywriterOut(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    scenes: List[CopyScene] = Field(min_length=2, max_length=6)


class DesignerOut(BaseModel):
    primaryColor: str = Hex
    accentColor: str = Hex
    background: str = Hex
    font: Literal["Outfit", "Manrope", "Sora", "IBM Plex Sans", "Space Mono"]


class DirectScene(BaseModel):
    transition: Literal["fade", "slide", "zoom", "wipe"]
    motion: Literal["rise", "pop", "drift", "type"]
    durationSec: float = Field(ge=1.5, le=6)


class DirectorOut(BaseModel):
    pacing: str = Field(default="", max_length=80)
    scenes: List[DirectScene] = Field(min_length=2, max_length=6)


class CriticFix(BaseModel):
    sceneIndex: int = Field(ge=0, le=5)
    field: Literal["headline", "subline", "eyebrow", "button"]
    value: str = Field(min_length=1, max_length=70)


class CriticOut(BaseModel):
    approved: bool
    issues: List[str] = Field(default_factory=list, max_length=6)
    fixes: List[CriticFix] = Field(default_factory=list, max_length=6)


class Scene(BaseModel):
    template: Template
    durationSec: float = Field(ge=0.5, le=20)
    props: Dict[str, Any] = {}


class Brand(BaseModel):
    name: str
    primaryColor: str
    accentColor: str = "#55D6FF"
    background: str = "#0B1016"
    font: str = "Outfit"


class SceneProject(BaseModel):
    title: str
    aspectRatio: Literal["16:9", "9:16"]
    brand: Brand
    scenes: List[Scene] = Field(min_length=1, max_length=12)
    captions: Optional[List[Dict[str, Any]]] = None
