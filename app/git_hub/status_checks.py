from typing import List
from schemas.findings import Finding

async def create_check_run(repo, commit_sha: str, findings: List[Finding], pr_number: int):
    """Create a check run (supports emojis and rich formatting)"""
    
    critical_count = sum(1 for f in findings if f.severity.value == "critical")
    high_count = sum(1 for f in findings if f.severity.value == "high")
    medium_count = sum(1 for f in findings if f.severity.value == "medium")
    low_count = sum(1 for f in findings if f.severity.value == "low")
    
    # Determine conclusion and summary
    if critical_count > 0 or high_count > 0:
        conclusion = "failure"
        title = f"🚫 Merge Blocked: {critical_count + high_count} Critical/High Issues"
        summary = f"## Security Issues Found\n\n"
        summary += f"| Severity | Count |\n|----------|-------|\n"
        summary += f"| 🔴 Critical | {critical_count} |\n"
        summary += f"| 🟠 High | {high_count} |\n"
        summary += f"| 🟡 Medium | {medium_count} |\n"
        summary += f"| 🔵 Low | {low_count} |\n\n"
        summary += "**This pull request cannot be merged until critical/high issues are fixed.**"
    elif findings:
        conclusion = "neutral"
        title = f"⚠️ Review Recommended: {len(findings)} Issues Found"
        summary = f"## Security Review Complete\n\n"
        summary += f"Found {len(findings)} security issue(s) to review:\n\n"
        summary += f"| Severity | Count |\n|----------|-------|\n"
        summary += f"| 🟡 Medium | {medium_count} |\n"
        summary += f"| 🔵 Low | {low_count} |\n\n"
        summary += "Please review the findings in the PR comment."
    else:
        conclusion = "success"
        title = "✅ Security Review Passed"
        summary = "## No Security Issues Detected\n\nThe code changes look secure. Good job! 👍"
    
    try:
        # Create check run
        check = repo.create_check_run(
            name="PRGate Security Review",
            head_sha=commit_sha,
            status="completed",
            conclusion=conclusion,
            output={
                "title": title,
                "summary": summary,
                "text": format_findings_for_check(findings) if findings else "No issues found."
            }
        )
        print(f"✅ Check run created: {conclusion} - {title[:50]}...")
        return conclusion == "failure"
        
    except Exception as e:
        print(f"❌ Failed to create check run: {e}")
        # Fall back to status check
        return await create_status_check(repo, commit_sha, findings, pr_number)

def format_findings_for_check(findings: List[Finding]) -> str:
    """Format findings for check run output"""
    if not findings:
        return "No security issues detected."
    
    text = "## Detailed Findings\n\n"
    for i, finding in enumerate(findings, 1):
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️"
        }.get(finding.severity.value, "⚪")
        
        text += f"### {i}. {severity_emoji} {finding.severity.value.upper()}: {finding.category.value}\n\n"
        text += f"**Issue:** {finding.issue}\n\n"
        text += f"**Fix:** {finding.fix}\n\n"
        
        if finding.cwe_id:
            text += f"**CWE:** `{finding.cwe_id}`\n\n"
        if finding.line_number:
            text += f"**Line:** `{finding.line_number}`\n\n"
        
        text += "---\n\n"
    
    return text

async def create_status_check(repo, commit_sha: str, findings: List[Finding], pr_number: int):
    """Fallback status check without emojis"""
    critical_count = sum(1 for f in findings if f.severity.value == "critical")
    
    if critical_count > 0:
        state = "failure"
        description = f"{critical_count} CRITICAL issue(s) found - merge blocked"
        context = "PRGate Security Review"
    elif findings:
        state = "success"
        description = f"{len(findings)} issue(s) found - review recommended"
        context = "PRGate Security Review"
    else:
        state = "success"
        description = "No security issues detected - ready to merge"
        context = "PRGate Security Review"
    
    try:
        status = repo.get_commit(commit_sha).create_status(
            state=state,
            description=description[:140],
            context=context,
            target_url=f"https://github.com/repo/pull/{pr_number}"
        )
        print(f"✅ Status check created: {state}")
        return state == "failure"
    except Exception as e:
        print(f"❌ Failed to create status check: {e}")
        return False

async def update_pr_labels(pr, findings: List[Finding]):
    """Add labels to PR based on findings"""
    try:
        labels_to_add = []
        
        if any(f.severity.value == "critical" for f in findings):
            labels_to_add.append("security-critical")
        if any(f.severity.value == "high" for f in findings):
            labels_to_add.append("security-high")
        if any(f.severity.value == "medium" for f in findings):
            labels_to_add.append("security-medium")
        if findings:
            labels_to_add.append("needs-security-review")
        
        for label in labels_to_add:
            try:
                pr.add_to_labels(label)
                print(f"✅ Added label: {label}")
            except Exception as e:
                print(f"⚠️ Could not add label {label}: {e}")
    except Exception as e:
        print(f"❌ Failed to update labels: {e}")