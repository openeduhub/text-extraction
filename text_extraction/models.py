from pydantic import BaseModel


class GrabbedContent(BaseModel):
    fulltext: str | None = None
    status: int


class FailedContent(BaseModel):
    content: str | None = None
    reason: str
    status: int
