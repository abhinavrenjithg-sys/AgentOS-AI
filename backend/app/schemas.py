from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Tool = Literal["research_public_pages", "generate_csv", "prepare_email_draft"]


class Step(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    title: str = Field(min_length=1, max_length=120)
    tool: Tool
    description: str = Field(min_length=1, max_length=500)
    inputs: dict = Field(default_factory=dict, max_length=20)
    depends_on: list[str] = Field(default_factory=list, max_length=8)
    approval_required: bool = False


class Plan(BaseModel):
    goal: str = Field(min_length=10, max_length=4000)
    steps: list[Step] = Field(min_length=2, max_length=8)
    risks: list[str] = Field(default_factory=list, max_length=10)
    source_urls: list[str] = Field(default_factory=list, max_length=5)
    mode: Literal["deterministic", "llm"] = "deterministic"


class PlanRequest(BaseModel):
    task: str = Field(min_length=10, max_length=4000)
    source_urls: list[str] = Field(default_factory=list, max_length=5)


class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    goal: str
    version: int
    definition: dict
    created_at: datetime


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    title: str
    tool: str
    status: str
    output: dict | None
    error: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workflow_id: int
    status: str
    approved: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: dict | None
    error: str | None
    steps: list[StepOut]
