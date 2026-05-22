from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Category(str, Enum):
    # Injection attacks
    SQL_INJECTION = "sql_injection"
    NOSQL_INJECTION = "nosql_injection"
    COMMAND_INJECTION = "command_injection"
    XXE = "xxe"
    SSTI = "ssti"
    
    # Secrets & crypto
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"
    
    # Web vulnerabilities
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    OPEN_REDIRECT = "open_redirect"
    CORS_MISCONFIGURATION = "cors_misconfiguration"
    
    # Deserialization
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    
    # Configuration
    DEBUG_MODE = "debug_mode"
    MISSING_SECURITY_HEADERS = "missing_security_headers"
    INFORMATION_DISCLOSURE = "information_disclosure"
    WEAK_RANDOM = "weak_random"
    
    # General
    BAD_PRACTICE = "bad_practice"
    OTHER = "other"

class Finding(BaseModel):
    severity: Severity
    category: Category
    issue: str = Field(..., description="Description of the security issue")
    fix: str = Field(..., description="Suggested fix for the issue")
    line_number: Optional[int] = Field(None, description="Line number where issue occurs")
    cwe_id: Optional[str] = Field(None, description="CWE ID if applicable")

class CodeReviewResponse(BaseModel):
    findings: List[Finding] = Field(default_factory=list, description="List of security findings")
    summary: Optional[str] = Field(None, description="Overall summary of the code review")
    has_issues: bool = Field(False, description="Whether any issues were found")