import uuid
from datetime import datetime
from typing import List, Optional
from database.mongodb_client import mongodb_client
from database.models import ReviewLog, FindingLog, DeveloperStats, RepositoryStats
from schemas.findings import Finding, CodeReviewResponse

class DatabaseRepository:
    """Database operations for CodeSentry"""
    
    def __init__(self):
        self.db = None
    
    async def ensure_connection(self):
        """Ensure database connection"""
        if self.db is None:
            self.db = await mongodb_client.connect()
        return self.db is not None
    
    async def save_review(self, review_data: dict, review_id: str = None):
        """Save a review record"""
        if self.db is None:  # Change this line
            if not await self.ensure_connection():
                return None
        
        if review_id is None:
            review_id = str(uuid.uuid4())
        
        review = ReviewLog(
            review_id=review_id,
            **review_data
        )
        
        await self.db.reviews.insert_one(review.model_dump())
        return review_id
    
    async def save_finding(self, review_id: str, pr_number: int, 
                          repository: str, filename: str, 
                          finding: Finding) -> str:
        """Save an individual finding"""
        if not await self.ensure_connection():
            return None
        
        finding_id = str(uuid.uuid4())
        finding_log = FindingLog(
            finding_id=finding_id,
            review_id=review_id,
            pr_number=pr_number,
            repository=repository,
            filename=filename,
            severity=finding.severity.value,
            category=finding.category.value,
            issue=finding.issue,
            fix=finding.fix,
            line_number=finding.line_number,
            cwe_id=finding.cwe_id
        )
        
        await self.db.findings.insert_one(finding_log.model_dump())
        return finding_id
    
    async def update_developer_stats(self, username: str, findings: List[Finding]):
        """Update developer statistics"""
        if not await self.ensure_connection():
            return
        
        stats = {
            "total_findings": len(findings),
            "critical_count": sum(1 for f in findings if f.severity.value == "critical"),
            "high_count": sum(1 for f in findings if f.severity.value == "high"),
            "medium_count": sum(1 for f in findings if f.severity.value == "medium"),
            "low_count": sum(1 for f in findings if f.severity.value == "low"),
            "last_active": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Update recurring issues
        category_counts = {}
        for finding in findings:
            category = finding.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        await self.db.developers.update_one(
            {"username": username},
            {
                "$inc": {
                    "total_prs": 1,
                    "total_findings": stats["total_findings"],
                    "critical_count": stats["critical_count"],
                    "high_count": stats["high_count"],
                    "medium_count": stats["medium_count"],
                    "low_count": stats["low_count"]
                },
                "$set": {
                    "last_active": stats["last_active"],
                    "updated_at": stats["updated_at"]
                },
                "$inc": {f"recurring_issues.{k}": v for k, v in category_counts.items()}
            },
            upsert=True
        )
    
    async def update_repository_stats(self, repository: str, findings: List[Finding]):
        """Update repository statistics and risk score"""
        if not await self.ensure_connection():
            return
        
        critical_count = sum(1 for f in findings if f.severity.value == "critical")
        high_count = sum(1 for f in findings if f.severity.value == "high")
        
        # Calculate risk score (0-100)
        # Critical: 50 points, High: 20 points, Medium: 5 points, Low: 1 point
        risk_score = min(100, (critical_count * 50) + (high_count * 20) + 
                               (len(findings) * 5))
        
        await self.db.repositories.update_one(
            {"full_name": repository},
            {
                "$inc": {
                    "total_reviews": 1,
                    "total_findings": len(findings),
                    "critical_count": critical_count,
                    "high_count": high_count
                },
                "$set": {
                    "risk_score": risk_score,
                    "last_reviewed": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    async def get_pr_history(self, repository: str, pr_number: int) -> List[dict]:
        """Get historical reviews for a specific PR"""
        if not await self.ensure_connection():
            return []
        
        cursor = self.db.reviews.find({
            "repository": repository,
            "pr_number": pr_number
        }).sort("created_at", -1)
        
        return await cursor.to_list(length=100)
    
    async def get_developer_risk_score(self, username: str) -> float:
        """Calculate developer risk score based on history"""
        if not await self.ensure_connection():
            return 0.0
        
        dev = await self.db.developers.find_one({"username": username})
        if not dev:
            return 0.0
        
        # Weighted score
        score = (dev.get('critical_count', 0) * 10 + 
                dev.get('high_count', 0) * 5 +
                dev.get('medium_count', 0) * 2 +
                dev.get('low_count', 0) * 1)
        
        # Normalize to 0-100 based on total PRs
        total_prs = dev.get('total_prs', 1)
        normalized_score = min(100, (score / total_prs) * 20)
        
        return round(normalized_score, 2)
    
    async def get_trends(self, repository: str, days: int = 30) -> dict:
        """Get security trends for a repository"""
        if not await self.ensure_connection():
            return {}
        
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {
                "repository": repository,
                "created_at": {"$gte": cutoff}
            }},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "total_findings": {"$sum": "$total_findings"},
                "critical_count": {"$sum": "$critical_count"},
                "high_count": {"$sum": "$high_count"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        cursor = self.db.reviews.aggregate(pipeline)
        results = await cursor.to_list(length=days)
        
        return {
            "daily_trends": results,
            "total_days": len(results),
            "average_findings_per_day": sum(r['total_findings'] for r in results) / max(1, len(results))
        }

# Global database repository
db_repo = DatabaseRepository()