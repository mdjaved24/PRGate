from langchain_core.prompts import ChatPromptTemplate

def get_security_review_prompt():
    """Get the security review prompt with output format"""
    template = """
You are a senior security engineer reviewing code changes.

Analyze this code diff for security vulnerabilities and coding issues.

**Code Diff:**
{code}

**IMPORTANT:** Return ONLY valid JSON. Do not include any other text, explanations, or markdown formatting.

Return in this exact format:

{{
  "summary": "Brief overall assessment of the code changes (1-2 sentences)",
  "findings": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "sql_injection|hardcoded_secret|xss|path_traversal|command_injection|insecure_deserialization|weak_crypto|bad_practice|other",
      "issue": "Clear description of the security issue",
      "fix": "Specific recommendation to fix the issue",
      "line_number": null,
      "cwe_id": null
    }}
  ],
  "has_issues": true
}}

If no issues found:
{{
  "summary": "No security issues detected in this code change.",
  "findings": [],
  "has_issues": false
}}
"""
    return ChatPromptTemplate.from_template(template)

SECURITY_REVIEW_PROMPT = get_security_review_prompt()