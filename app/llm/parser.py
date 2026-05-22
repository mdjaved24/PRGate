import json
import re
from typing import List, Optional
from schemas.findings import Finding, Severity, Category, CodeReviewResponse

def clean_json_response(raw_response: str) -> str:
    """Extract and clean JSON from LLM response"""
    # Remove markdown code blocks
    raw_response = re.sub(r'```json\s*', '', raw_response)
    raw_response = re.sub(r'```\s*', '', raw_response)
    
    # Try to find JSON object or array
    json_match = re.search(r'(\{.*\}|\[.*\])', raw_response, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return raw_response.strip()

def parse_findings(response_dict: dict) -> List[Finding]:
    """Parse findings from response dictionary with validation"""
    findings = []
    
    # Handle different response formats
    if 'findings' in response_dict:
        findings_data = response_dict['findings']
    elif isinstance(response_dict, list):
        findings_data = response_dict
    else:
        findings_data = []
    
    for finding_data in findings_data:
        try:
            # Ensure required fields exist
            finding = Finding(
                severity=Severity(finding_data.get('severity', 'low')),
                category=Category(finding_data.get('category', 'other')),
                issue=finding_data.get('issue', 'No description provided'),
                fix=finding_data.get('fix', 'No fix suggested'),
                line_number=finding_data.get('line_number'),
                cwe_id=finding_data.get('cwe_id')
            )
            findings.append(finding)
        except (ValueError, KeyError) as e:
            print(f"Error parsing finding: {e}")
            continue
    
    return findings

def parse_review_response(raw_response: str) -> CodeReviewResponse:
    """Parse LLM response into CodeReviewResponse object"""
    try:
        cleaned_response = clean_json_response(raw_response)
        response_dict = json.loads(cleaned_response)
        
        if isinstance(response_dict, list):
            findings = parse_findings(response_dict)
            return CodeReviewResponse(
                findings=findings,
                summary=f"Found {len(findings)} security issues",
                has_issues=len(findings) > 0
            )
        else:
            findings = parse_findings(response_dict)
            return CodeReviewResponse(
                findings=findings,
                summary=response_dict.get('summary', f"Found {len(findings)} security issues"),
                has_issues=response_dict.get('has_issues', len(findings) > 0)
            )
    
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        return CodeReviewResponse(
            summary="Failed to parse security review response",
            has_issues=False
        )
    except Exception as e:
        print(f"Unexpected error parsing response: {e}")
        return CodeReviewResponse(
            summary=f"Error processing review: {str(e)}",
            has_issues=False
        )

def format_findings_as_markdown(findings: List[Finding]) -> str:
    """Format findings as markdown for PR comments"""
    if not findings:
        return "✅ No security issues detected."
    
    markdown = "## 🔒 Security Review Findings\n\n"
    for i, finding in enumerate(findings, 1):
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️"
        }.get(finding.severity.value, "⚪")
        
        markdown += f"### {i}. {severity_emoji} {finding.severity.value.upper()}: {finding.category.value}\n\n"
        markdown += f"**Issue:** {finding.issue}\n\n"
        markdown += f"**Fix:** {finding.fix}\n\n"
        
        if finding.line_number:
            markdown += f"*Line: {finding.line_number}*\n\n"
        if finding.cwe_id:
            markdown += f"*CWE: {finding.cwe_id}*\n\n"
        
        markdown += "---\n\n"
    
    return markdown