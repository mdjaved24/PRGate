from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from schemas.findings import Finding

class ReviewLog(BaseModel):
    """Schema for storing review logs"""
    review_id: str
    pr_number: int
    pr_title: str
    pr_url: str
    repository: str
    author: str
    action: str
    commit_sha: str
    files_reviewed: int
    total_findings: int
    has_issues: bool
    merge_blocked: bool
    created_at: datetime = datetime.utcnow()
    completed_at: Optional[datetime] = None
    status: str  # pending, completed, failed

class FindingLog(BaseModel):
    """Schema for storing individual findings"""
    finding_id: str
    review_id: str
    pr_number: int
    repository: str
    filename: str
    severity: str
    category: str
    issue: str
    fix: str
    line_number: Optional[int]
    cwe_id: Optional[str]
    created_at: datetime = datetime.utcnow()

class DeveloperStats(BaseModel):
    """Schema for developer statistics"""
    username: str
    email: Optional[str]
    total_prs: int = 0
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    recurring_issues: dict = {}  # {category: count}
    last_active: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

class RepositoryStats(BaseModel):
    """Schema for repository statistics"""
    full_name: str
    total_reviews: int = 0
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    risk_score: float = 0.0  # 0-100, higher = more risky
    last_reviewed: Optional[datetime]
    updated_at: datetime = datetime.utcnow()