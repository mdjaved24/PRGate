from typing import Dict
from schemas.findings import CodeReviewResponse

def format_pr_comment(review_results: Dict[str, CodeReviewResponse], pr_number: int, pr_title: str) -> str:
    """Format review results as a PR comment"""
    
    # Calculate statistics
    total_issues = sum(
        len(result.findings) for result in review_results.values() if result.has_issues
    )
    files_with_issues = sum(
        1 for result in review_results.values() if result.has_issues
    )
    
    # Count by severity
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0
    }
    
    for result in review_results.values():
        for finding in result.findings:
            severity_counts[finding.severity.value] += 1
    
    # Build comment
    comment = f"""## 🔒 PRGate Security Review

**Pull Request:** #{pr_number} - {pr_title}
**Files Reviewed:** {len(review_results)}
**Issues Found:** {total_issues} in {files_with_issues} file(s)

### Severity Breakdown
"""
    
    if severity_counts["critical"] > 0:
        comment += f"- 🔴 **Critical:** {severity_counts['critical']}\n"
    if severity_counts["high"] > 0:
        comment += f"- 🟠 **High:** {severity_counts['high']}\n"
    if severity_counts["medium"] > 0:
        comment += f"- 🟡 **Medium:** {severity_counts['medium']}\n"
    if severity_counts["low"] > 0:
        comment += f"- 🔵 **Low:** {severity_counts['low']}\n"
    if severity_counts["info"] > 0:
        comment += f"- ℹ️ **Info:** {severity_counts['info']}\n"
    
    comment += "\n---\n\n"
    
    if total_issues == 0:
        comment += "✅ **No security issues detected!**\n\n"
        comment += "The code changes look secure. Good job! 👍"
        return comment

    comment += "### 📋 Detailed Findings\n\n"
    
    for filename, result in review_results.items():
        if result.has_issues:
            comment += f"#### 📄 `{filename}`\n\n"
            
            for i, finding in enumerate(result.findings, 1):
                severity_emoji = {
                    "critical": "🔴 **CRITICAL**",
                    "high": "🟠 **HIGH**",
                    "medium": "🟡 **MEDIUM**",
                    "low": "🔵 **LOW**",
                    "info": "ℹ️ **INFO**"
                }.get(finding.severity.value, "⚪")
                
                comment += f"**{i}. {severity_emoji}** - *{finding.category.value}*\n\n"
                comment += f"**Issue:** {finding.issue}\n\n"
                comment += f"**Fix:** {finding.fix}\n\n"
                
                if finding.cwe_id:
                    comment += f"*CWE: {finding.cwe_id}*\n\n"
                
                if finding.line_number:
                    comment += f"*Line: {finding.line_number}*\n\n"
                
                comment += "---\n\n"
    
    # Add recommendations
    if severity_counts["critical"] > 0 or severity_counts["high"] > 0:
        comment += "\n### 🚫 Merge Blocked\n\n"
        comment += "This PR contains **critical or high severity** security issues and **cannot be merged** until they are fixed.\n\n"
    else:
        comment += "\n### 💡 Recommendations\n\n"
        comment += "Please review the issues above and apply the suggested fixes before merging.\n\n"
    
    comment += "*This is an automated security review. Please verify findings manually if needed.*"
    
    return comment

async def post_pr_comment(repo, pr_number: int, comment: str):
    """Post a comment to the PR"""
    try:
        pr = repo.get_pull(pr_number)
        
        # Check if bot already commented
        comments = pr.get_issue_comments()
        bot_comment = None
        
        for comment_obj in comments:
            if comment_obj.user.login == "github-actions[bot]" or "PRGate" in comment_obj.body:
                bot_comment = comment_obj
                break

        if bot_comment:
            bot_comment.edit(comment)
            print(f"✅ Updated existing comment on PR #{pr_number}")
        else:
            pr.create_issue_comment(comment)
            print(f"✅ Posted new comment to PR #{pr_number}")
            
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")