from github import Github
from dotenv import load_dotenv
import os
from git_hub.app_auth import github_app
from utils.logger import get_logger

load_dotenv()

github_logger = get_logger("github")


class GitHubClient:
    """GitHub client supporting both App and PAT authentication"""
    
    def __init__(self):
        self._client = None
        self._auth_method = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize GitHub client with best available authentication"""
        
        # Try GitHub App first
        if github_app.initialize():
            client = github_app.get_github_client()
            if client:
                self._client = client
                self._auth_method = "GitHub App"
                github_logger.info("✅ Using GitHub App authentication")
                return
        
        # Fallback to PAT
        token = os.getenv('GITHUB_TOKEN')
        if token:
            self._client = Github(token)
            self._auth_method = "Personal Access Token"
            github_logger.warning("⚠️ Using PAT authentication (fallback)")
            return
        
        # No authentication
        self._client = Github()
        self._auth_method = "None (Public only)"
        github_logger.warning("⚠️ No authentication configured - public access only")
    
    def get_user(self, username: str):
        return self._client.get_user(username)
    
    def get_repo(self, repo_name: str):
        return self._client.get_repo(repo_name)
    
    @property
    def client(self):
        return self._client
    
    @property
    def auth_method(self):
        return self._auth_method


# Global instance
git = GitHubClient()