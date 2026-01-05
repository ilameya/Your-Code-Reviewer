from typing import List, Optional, Literal
from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
Category = Literal["bug", "security", "style", "design", "performance", "testing", "docs"]

class Finding(BaseModel):
    category: Category
    severity: Severity
    title: str
    details: str
    line_start: int
    line_end: int
    suggestion: str

class ReviewReport(BaseModel):
    path: str
    language: str
    summary: str
    score: int = Field(..., ge=0, le=100)
    findings: List[Finding]
