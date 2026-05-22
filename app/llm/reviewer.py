from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from schemas.findings import CodeReviewResponse
from llm.prompts import SECURITY_REVIEW_PROMPT
from llm.parser import parse_review_response, format_findings_as_markdown
from utils.cache import review_cache
from utils.logger import get_logger
import time

load_dotenv()

# Setup logger for this module
llm_logger = get_logger("llm")


def get_llm(model: str = "llama-3.3-70b-versatile", temperature: float = 0):
    """Get LLM instance"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        llm_logger.error("GROQ_API_KEY not found in environment variables")
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    llm_logger.debug(f"Initializing LLM with model: {model}, temperature: {temperature}")
    return ChatGroq(
        model=model,
        temperature=temperature,
        api_key=api_key
    )


# Initialize LLM and prompt
llm = get_llm()
prompt = SECURITY_REVIEW_PROMPT
llm_logger.info("LLM and prompt initialized successfully")


def review_code(code: str, max_retries: int = 2) -> CodeReviewResponse:
    """
    Review code diff for security issues with caching and logging
    """
    code_length = len(code)
    llm_logger.debug(f"Review request received - Code length: {code_length} chars, Max retries: {max_retries}")
    
    # Check cache first
    start_time = time.time()
    cached_result = review_cache.get(code)
    
    if cached_result:
        cache_time = time.time() - start_time
        llm_logger.info(f"Cache HIT - Returning cached result (took {cache_time:.3f}s)")
        return cached_result
    
    llm_logger.debug("Cache MISS - Performing new LLM review")
    
    for attempt in range(max_retries):
        attempt_start = time.time()
        llm_logger.info(f"LLM review attempt {attempt + 1}/{max_retries}")
        
        try:
            # Invoke LLM chain
            llm_logger.debug("Invoking LLM chain...")
            chain = prompt | llm
            response = chain.invoke({'code': code})
            
            # Parse response
            llm_logger.debug("Parsing LLM response...")
            result = parse_review_response(response.content)
            
            attempt_time = time.time() - attempt_start
            findings_count = len(result.findings)
            
            llm_logger.info(f"Attempt {attempt + 1} completed in {attempt_time:.2f}s - Found {findings_count} issues")
            
            # Log findings at debug level
            if result.has_issues:
                for finding in result.findings:
                    llm_logger.debug(f"  Finding: [{finding.severity.value}] {finding.category.value} - {finding.issue[:100]}...")
            
            if result.has_issues or attempt == max_retries - 1:
                # Cache the result
                review_cache.set(code, result)
                llm_logger.info(f"Review completed and cached - Total findings: {findings_count}, Has issues: {result.has_issues}")
                return result
            
            llm_logger.warning(f"Retrying review (attempt {attempt + 2}/{max_retries})...")
            
        except Exception as e:
            attempt_time = time.time() - attempt_start
            llm_logger.error(f"Error in review attempt {attempt + 1} after {attempt_time:.2f}s: {e}")
            
            if attempt == max_retries - 1:
                llm_logger.error(f"All {max_retries} attempts failed - Returning error response")
                return CodeReviewResponse(
                    summary=f"Failed to complete security review: {str(e)}",
                    has_issues=False
                )
            
            llm_logger.warning(f"Retrying after error (attempt {attempt + 2}/{max_retries})...")
    
    llm_logger.warning("Review completed with no findings (exhausted retries)")
    return CodeReviewResponse(
        summary="Review completed with no findings",
        has_issues=False
    )


def review_multiple_files(files_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Review multiple files and aggregate results with logging
    
    Args:
        files_data: List of dicts with 'filename' and 'patch' keys
        
    Returns:
        Dictionary with aggregated results
    """
    total_start_time = time.time()
    llm_logger.info(f"Starting multi-file review - Total files: {len(files_data)}")
    
    all_findings = []
    file_results = {}
    files_reviewed = 0
    files_skipped = 0
    
    for idx, file_data in enumerate(files_data, 1):
        filename = file_data.get('filename')
        patch = file_data.get('patch')
        
        if not patch:
            llm_logger.debug(f"Skipping file {idx}/{len(files_data)}: {filename} (no patch content)")
            files_skipped += 1
            continue
        
        llm_logger.info(f"Reviewing file {idx}/{len(files_data)}: {filename}")
        file_start_time = time.time()
        
        result = review_code(patch)
        file_results[filename] = result
        
        file_time = time.time() - file_start_time
        
        if result.has_issues:
            all_findings.extend(result.findings)
            llm_logger.info(f"  ✅ {filename}: {len(result.findings)} issue(s) found in {file_time:.2f}s")
        else:
            llm_logger.info(f"  ✅ {filename}: No issues found in {file_time:.2f}s")
        
        files_reviewed += 1
    
    total_time = time.time() - total_start_time
    llm_logger.info(f"Multi-file review completed - Files reviewed: {files_reviewed}, Skipped: {files_skipped}, Total findings: {len(all_findings)}, Total time: {total_time:.2f}s")
    
    return {
        'total_findings': len(all_findings),
        'files_reviewed': files_reviewed,
        'files_skipped': files_skipped,
        'file_results': file_results,
        'all_findings': all_findings,
        'markdown_summary': _generate_summary_markdown(file_results),
        'total_time_seconds': round(total_time, 2)
    }


def _generate_summary_markdown(file_results: Dict[str, CodeReviewResponse]) -> str:
    """Generate a markdown summary for all files with logging"""
    llm_logger.debug("Generating markdown summary for review results")
    
    if not file_results:
        llm_logger.debug("No file results to generate summary")
        return "No files were reviewed."
    
    total_issues = sum(len(r.findings) for r in file_results.values())
    llm_logger.debug(f"Generating summary for {len(file_results)} files with {total_issues} total issues")
    
    if total_issues == 0:
        return "✅ **PRGate Review Complete**\n\nNo security issues found in any files."
    
    markdown = f"## 🔒 PRGate Security Review\n\n"
    markdown += f"**Summary:** Found {total_issues} security issue(s) across {len(file_results)} file(s).\n\n"
    
    for filename, result in file_results.items():
        if result.findings:
            markdown += f"### 📄 `{filename}`\n\n"
            markdown += format_findings_as_markdown(result.findings)
            markdown += "\n"
    
    llm_logger.debug(f"Markdown summary generated - Length: {len(markdown)} chars")
    return markdown


def review_pull_request(files: list) -> Dict[str, Any]:
    """Review all files in a pull request with logging"""
    llm_logger.info(f"Reviewing pull request - Total files in PR: {len(files)}")
    
    # Filter files with patches
    files_with_patch = [f for f in files if f.patch]
    files_without_patch = len(files) - len(files_with_patch)
    
    llm_logger.info(f"Files with patch: {len(files_with_patch)}, Without patch: {files_without_patch}")
    
    files_data = [{'filename': f.filename, 'patch': f.patch} for f in files if f.patch]
    
    result = review_multiple_files(files_data)
    
    llm_logger.info(f"PR review completed - Total findings: {result['total_findings']}, Time: {result.get('total_time_seconds', 0)}s")
    
    return result