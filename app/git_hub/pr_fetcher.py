from fastapi import APIRouter, Request, HTTPException
from git_hub.client import git
from llm.reviewer import review_code
from schemas.findings import CodeReviewResponse
from git_hub.status_checks import create_check_run, update_pr_labels
from git_hub.pr_comment import format_pr_comment, post_pr_comment
from utils.rate_limiter import rate_limiter
from utils.cache import review_cache
from utils.logger import webhook_logger, review_logger, audit_logger, error_logger, get_logger
from database.repository import db_repo
from database.mongodb_client import mongodb_client
from datetime import datetime
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid

git_router = APIRouter(prefix='/git')

# Configuration
BLOCKED_EXTENSIONS = [".md", ".txt", ".json", ".yml", ".yaml", ".lock", ".toml", ".gitignore", ".env", ".log"]
ALLOWED_STATUSES = ["added", "modified"]
MAX_CONCURRENT_REVIEWS = 3

# Thread pool for CPU-bound operations
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REVIEWS)

# Setup logger for this module
pr_logger = get_logger("pr_fetcher")

# ============ Helper Functions ============

async def review_file_async(file):
    """Review a single file asynchronously with caching"""
    loop = asyncio.get_event_loop()
    
    # Check cache first
    cached_result = review_cache.get(file.patch)
    if cached_result:
        pr_logger.debug(f"Cache HIT - Using cached result for {file.filename}")
        return cached_result
    
    pr_logger.debug(f"Cache MISS - Reviewing {file.filename}")
    
    # Run review in thread pool
    result = await loop.run_in_executor(
        executor,
        review_code,
        file.patch
    )
    
    # Cache result
    review_cache.set(file.patch, result)
    return result


async def save_review_to_database(
    review_id: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
    repo_name: str,
    pr_author: str,
    action: str,
    head_commit: str,
    files_to_review: list,
    all_findings: list,
    review_results: dict,
    blocking: bool,
    status: str = "completed"
):
    """Save review results to database with logging"""
    try:
        pr_logger.debug(f"Saving review {review_id[:8]} to database...")
        
        # Save main review record
        review_data = {
            "pr_number": pr_number,
            "pr_title": pr_title,
            "pr_url": pr_url,
            "repository": repo_name,
            "author": pr_author,
            "action": action,
            "commit_sha": head_commit,
            "files_reviewed": len(files_to_review),
            "total_findings": len(all_findings),
            "has_issues": len(all_findings) > 0,
            "merge_blocked": blocking,
            "status": status,
            "completed_at": datetime.utcnow()
        }
        
        await db_repo.save_review(review_data, review_id=review_id)
        
        # Save individual findings
        finding_count = 0
        for filename, result in review_results.items():
            for finding in result.findings:
                await db_repo.save_finding(
                    review_id=review_id,
                    pr_number=pr_number,
                    repository=repo_name,
                    filename=filename,
                    finding=finding
                )
                finding_count += 1
        
        # Update developer statistics
        if all_findings:
            await db_repo.update_developer_stats(pr_author, all_findings)
            pr_logger.debug(f"Updated developer stats for {pr_author}")
        
        # Update repository statistics
        await db_repo.update_repository_stats(repo_name, all_findings)
        
        pr_logger.info(f"Database: Saved review {review_id[:8]} with {finding_count} findings")
        
    except Exception as e:
        error_logger.error(f"Database save error for review {review_id}: {e}")
        error_logger.debug(traceback.format_exc())


# ============ Route Handlers ============

@git_router.get('/git_user/{username}')
async def get_git_user(username: str):
    """Get GitHub user information"""
    try:
        pr_logger.info(f"Fetching GitHub user: {username}")
        user = git.get_user(username)
        if user:
            return {
                "login": user.login,
                "name": user.name,
                "bio": user.bio,
                "followers": user.followers,
                "following": user.following,
                "public_repos": user.public_repos,
                "avatar_url": user.avatar_url,
                "profile_url": user.html_url,
                "created_at": str(user.created_at)
            }
        pr_logger.warning(f"User not found: {username}")
        return {"error": "User not found"}
    except Exception as e:
        error_logger.error(f"Error fetching user {username}: {e}")
        return {'error': str(e)}


@git_router.post("/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events"""
    try:
        payload = await request.json()
    except Exception as e:
        error_logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event_type = request.headers.get('X-GitHub-Event')
    delivery_id = request.headers.get('X-GitHub-Delivery', 'unknown')
    
    # Log webhook receipt
    webhook_logger.info(f"Webhook received - Event: {event_type}, Delivery ID: {delivery_id[:8]}...")
    audit_logger.info(f"Webhook event - Type: {event_type}, ID: {delivery_id}")
    
    # Handle different event types
    if event_type == 'ping':
        return await handle_ping_event(payload)
    elif event_type == 'pull_request':
        return await handle_pull_request_event(payload)
    else:
        webhook_logger.warning(f"Unhandled event type: {event_type}")
        return {
            "message": f"Event {event_type} received but not processed",
            "event_type": event_type
        }


async def handle_ping_event(payload: dict) -> dict:
    """Handle GitHub ping event"""
    repo_name = payload.get('repository', {}).get('full_name', 'Unknown')
    zen = payload.get('zen', 'No zen message')
    
    webhook_logger.info(f"Ping received from repository: {repo_name}")
    webhook_logger.debug(f"Ping zen: {zen}")
    
    return {
        "message": "Webhook configured successfully!",
        "repository": repo_name,
        "zen": zen
    }


async def handle_pull_request_event(payload: dict) -> dict:
    """Handle GitHub pull request event with full database logging"""
    
    # Extract payload data
    action = payload.get('action')
    pr_data = payload.get('pull_request', {})
    repo_data = payload.get('repository', {})
    
    pr_number = pr_data.get('number')
    pr_title = pr_data.get('title', 'No title')
    pr_author = pr_data.get('user', {}).get('login', 'Unknown')
    repo_name = repo_data.get('full_name')
    pr_url = pr_data.get('html_url')
    head_commit = pr_data.get('head', {}).get('sha')
    
    # Generate unique review ID
    review_id = str(uuid.uuid4())
    
    # Log PR receipt
    review_logger.info(f"PR #{pr_number} - Review ID: {review_id[:8]}...")
    review_logger.info(f"  Repository: {repo_name}")
    review_logger.info(f"  Author: {pr_author}")
    review_logger.info(f"  Action: {action}")
    review_logger.info(f"  Commit: {head_commit[:8] if head_commit else 'N/A'}...")
    review_logger.info(f"  URL: {pr_url}")
    
    audit_logger.info(f"PR Review started - #{pr_number}, Repo: {repo_name}, Author: {pr_author}, Action: {action}")
    
    # Rate limiting check
    if not rate_limiter.is_allowed(repo_name):
        remaining = rate_limiter.get_remaining(repo_name)
        review_logger.warning(f"Rate limit exceeded for {repo_name}")
        audit_logger.warning(f"Rate limit exceeded - Repo: {repo_name}, PR: #{pr_number}")
        return {"message": f"Rate limit exceeded. Try again later. Remaining: {remaining}"}
    
    # Only process opened and synchronize events
    if action not in ["opened", "synchronize"]:
        review_logger.info(f"Ignoring action: {action} (only 'opened' or 'synchronize' events are processed)")
        return {"message": f"Ignored - action: {action}"}
    
    start_time = datetime.utcnow()
    
    try:
        # Get GitHub repository and PR objects
        review_logger.debug(f"Fetching GitHub repo: {repo_name}")
        repo = git.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Get changed files
        files = list(pr.get_files())
        review_logger.info(f"Total files changed: {len(files)}")
        
        # Filter files to review
        files_to_review = []
        skipped_count = 0
        
        for file in files:
            filename = file.filename
            status = file.status
            
            # Check if we should review this file
            if any(filename.endswith(ext) for ext in BLOCKED_EXTENSIONS):
                review_logger.debug(f"Skipping {filename} (blocked extension)")
                skipped_count += 1
                continue
            if status not in ALLOWED_STATUSES:
                review_logger.debug(f"Skipping {filename} (status: {status})")
                skipped_count += 1
                continue
            if not file.patch:
                review_logger.debug(f"Skipping {filename} (no patch content)")
                skipped_count += 1
                continue
            
            files_to_review.append(file)
            review_logger.info(f"Will review: {filename} ({status})")
        
        review_logger.info(f"Files to review: {len(files_to_review)}, Skipped: {skipped_count}")
        
        if not files_to_review:
            review_logger.warning(f"No files to review in PR #{pr_number}")
            
            # Save empty review to database
            await save_review_to_database(
                review_id=review_id,
                pr_number=pr_number,
                pr_title=pr_title,
                pr_url=pr_url,
                repo_name=repo_name,
                pr_author=pr_author,
                action=action,
                head_commit=head_commit,
                files_to_review=[],
                all_findings=[],
                review_results={},
                blocking=False,
                status="no_files_to_review"
            )
            return {"message": "No files to review"}
        
        review_logger.info(f"Reviewing {len(files_to_review)} file(s) in parallel...")
        
        # Review files in parallel
        review_tasks = [review_file_async(file) for file in files_to_review]
        review_results_list = await asyncio.gather(*review_tasks)
        
        # Process results
        all_findings = []
        review_results = {}
        
        for file, review_result in zip(files_to_review, review_results_list):
            review_results[file.filename] = review_result
            if review_result.has_issues:
                all_findings.extend(review_result.findings)
                review_logger.info(f"⚠️ {file.filename}: {len(review_result.findings)} issue(s)")
                # Log findings at debug level
                for finding in review_result.findings:
                    review_logger.debug(f"  - [{finding.severity.value}] {finding.issue[:80]}...")
            else:
                review_logger.info(f"✅ {file.filename}: No issues found")
        
        # Create status check (blocks merge if critical/high)
        blocking = False
        if head_commit:
            try:
                review_logger.debug(f"Creating status check for commit {head_commit[:8]}...")
                blocking = await create_check_run(repo, head_commit, all_findings, pr_number)
                if blocking:
                    review_logger.warning(f"PR #{pr_number} - Merge blocked due to critical/high severity issues")
                    audit_logger.warning(f"PR #{pr_number} - Merge blocked, Critical/High issues found")
                else:
                    review_logger.info(f"PR #{pr_number} - Merge not blocked (no critical/high issues)")
            except Exception as e:
                error_logger.error(f"Status check failed for PR #{pr_number}: {e}")
        
        # Update PR labels
        try:
            review_logger.debug(f"Updating labels for PR #{pr_number}")
            await update_pr_labels(pr, all_findings)
            review_logger.info(f"Labels updated for PR #{pr_number}")
        except Exception as e:
            error_logger.error(f"Label update failed for PR #{pr_number}: {e}")
        
        # Post or update PR comment
        try:
            review_logger.debug(f"Formatting PR comment for #{pr_number}")
            comment = format_pr_comment(review_results, pr_number, pr_title)
            await post_pr_comment(repo, pr_number, comment)
            review_logger.info(f"Comment {'updated' if all_findings else 'posted'} on PR #{pr_number}")
        except Exception as e:
            error_logger.error(f"Comment post failed for PR #{pr_number}: {e}")
        
        # Save everything to database
        await save_review_to_database(
            review_id=review_id,
            pr_number=pr_number,
            pr_title=pr_title,
            pr_url=pr_url,
            repo_name=repo_name,
            pr_author=pr_author,
            action=action,
            head_commit=head_commit,
            files_to_review=files_to_review,
            all_findings=all_findings,
            review_results=review_results,
            blocking=blocking,
            status="completed"
        )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        review_logger.info(f"PR #{pr_number} processed successfully in {processing_time:.2f} seconds")
        audit_logger.info(f"PR Review completed - #{pr_number}, Findings: {len(all_findings)}, Blocked: {blocking}, Time: {processing_time:.2f}s")
        
        critical_count = sum(1 for f in all_findings if f.severity.value == "critical")
        high_count = sum(1 for f in all_findings if f.severity.value == "high")
        
        return {
            "message": "Pull request reviewed successfully",
            "review_id": review_id,
            "pr_number": pr_number,
            "files_reviewed": len(files_to_review),
            "total_findings": len(all_findings),
            "has_issues": len(all_findings) > 0,
            "merge_blocked": blocking,
            "critical_count": critical_count,
            "high_count": high_count,
            "processing_time_seconds": round(processing_time, 2)
        }
        
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        error_logger.error(f"Error processing PR #{pr_number}: {e}")
        error_logger.error(traceback.format_exc())
        audit_logger.error(f"PR Review failed - #{pr_number}, Error: {str(e)[:200]}, Time: {processing_time:.2f}s")
        
        # Save failed review to database
        try:
            await save_review_to_database(
                review_id=review_id,
                pr_number=pr_number,
                pr_title=pr_title,
                pr_url=pr_url,
                repo_name=repo_name,
                pr_author=pr_author,
                action=action,
                head_commit=head_commit,
                files_to_review=[],
                all_findings=[],
                review_results={},
                blocking=False,
                status=f"failed: {str(e)[:100]}"
            )
        except Exception as db_error:
            error_logger.error(f"Could not save failed review to database: {db_error}")
        
        return {
            "error": "Failed to process pull request",
            "details": str(e),
            "review_id": review_id
        }


# ============ Utility Endpoints ============

@git_router.get("/health")
async def health_check():
    """Health check endpoint with cache stats"""
    from utils.cache import review_cache
    
    pr_logger.debug("Health check endpoint called")
    
    cache_stats = {}
    
    try:
        cache_stats = review_cache.get_stats()
    except AttributeError:
        cache_stats = {
            "type": "memory",
            "available": True,
            "entry_count": len(review_cache.cache) if hasattr(review_cache, 'cache') else 0
        }
    
    # Check database status
    db_status = "connected" if mongodb_client.is_connected else "disconnected"
    
    return {
        "status": "healthy",
        "service": "PRGate Security Bot",
        "cache": cache_stats,
        "database": db_status,
        "blocked_extensions": BLOCKED_EXTENSIONS,
        "max_concurrent_reviews": MAX_CONCURRENT_REVIEWS
    }


@git_router.get("/cache/stats")
async def cache_stats():
    """Get detailed cache statistics"""
    from utils.cache import review_cache
    
    pr_logger.debug("Cache stats endpoint called")
    stats = review_cache.get_stats()
    pr_logger.debug(f"Cache stats: {stats}")
    
    return stats


@git_router.post("/cache/clear")
async def clear_cache():
    """Clear all cache (admin endpoint)"""
    from utils.cache import review_cache
    
    pr_logger.warning("Cache clear endpoint called - Clearing all cache")
    review_cache.clear()
    
    audit_logger.info("Cache manually cleared via API")
    
    return {
        "message": "Cache cleared successfully",
        "cache_type": review_cache.cache_type if hasattr(review_cache, 'cache_type') else "memory"
    }


@git_router.get("/review/{review_id}")
async def get_review(review_id: str):
    """Get review details by ID from database"""
    pr_logger.debug(f"Fetching review: {review_id}")
    
    try:
        review = await db_repo.db.reviews.find_one({"review_id": review_id})
        if not review:
            pr_logger.warning(f"Review not found: {review_id}")
            return {"error": "Review not found"}
        
        # Convert ObjectId to string for JSON serialization
        if '_id' in review:
            review['_id'] = str(review['_id'])
        
        # Get findings for this review
        findings_cursor = db_repo.db.findings.find({"review_id": review_id})
        findings = await findings_cursor.to_list(length=100)
        for finding in findings:
            if '_id' in finding:
                finding['_id'] = str(finding['_id'])
        
        pr_logger.debug(f"Found review {review_id} with {len(findings)} findings")
        
        return {
            "review": review,
            "findings": findings,
            "total_findings": len(findings)
        }
    except Exception as e:
        error_logger.error(f"Error fetching review {review_id}: {e}")
        return {"error": str(e)}


@git_router.get("/stats/developer/{username}")
async def get_developer_stats(username: str):
    """Get developer statistics"""
    pr_logger.debug(f"Fetching developer stats for: {username}")
    
    try:
        dev = await db_repo.db.developers.find_one({"username": username})
        if not dev:
            pr_logger.warning(f"Developer not found: {username}")
            return {"error": "Developer not found"}
        
        if '_id' in dev:
            dev['_id'] = str(dev['_id'])
        
        # Calculate risk level
        risk_score = dev.get('critical_count', 0) * 10 + dev.get('high_count', 0) * 5
        if dev.get('total_prs', 0) > 0:
            risk_score = risk_score / dev['total_prs']
        
        risk_level = "low"
        if risk_score > 20:
            risk_level = "high"
        elif risk_score > 10:
            risk_level = "medium"
        
        dev['risk_score'] = round(risk_score, 2)
        dev['risk_level'] = risk_level
        
        pr_logger.debug(f"Developer {username} - Risk score: {risk_score}, Level: {risk_level}")
        
        return dev
    except Exception as e:
        error_logger.error(f"Error fetching developer stats for {username}: {e}")
        return {"error": str(e)}


@git_router.get("/stats/repository/{repository}")
async def get_repository_stats(repository: str):
    """Get repository statistics"""
    pr_logger.debug(f"Fetching repository stats for: {repository}")
    
    try:
        repo_stats = await db_repo.db.repositories.find_one({"full_name": repository})
        if not repo_stats:
            pr_logger.warning(f"Repository not found: {repository}")
            return {"error": "Repository not found"}
        
        if '_id' in repo_stats:
            repo_stats['_id'] = str(repo_stats['_id'])
        
        pr_logger.debug(f"Repository {repository} - Risk score: {repo_stats.get('risk_score', 0)}")
        
        return repo_stats
    except Exception as e:
        error_logger.error(f"Error fetching repository stats for {repository}: {e}")
        return {"error": str(e)}