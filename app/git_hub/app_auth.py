"""
GitHub App Authentication for PRGate
"""

import os
from github import Github, GithubIntegration
from github import Auth
from dotenv import load_dotenv
from utils.logger import get_logger

load_dotenv()

github_logger = get_logger("github")


class GitHubAppAuth:
    """Handle GitHub App authentication"""
    
    def __init__(self):
        self.app_id = os.getenv('GITHUB_APP_ID')
        self.webhook_secret = os.getenv('GITHUB_WEBHOOK_SECRET')
        self.fallback_token = os.getenv('GITHUB_TOKEN')
        self.private_key_path = os.getenv('GITHUB_PRIVATE_KEY_PATH', './private-key.pem')
        
        self.app = None
        self.installation_id = None
        self._initialized = False
    
    def initialize(self):
        """Initialize GitHub App connection"""
        if not self.app_id:
            github_logger.warning("GitHub App ID not configured, falling back to PAT")
            return self._init_fallback()
        
        try:
            # Check if private key file exists
            if not os.path.exists(self.private_key_path):
                github_logger.warning(f"Private key file not found: {self.private_key_path}")
                return self._init_fallback()
            
            # Read private key from file
            with open(self.private_key_path, 'r') as f:
                private_key = f.read()
            
            # Create integration
            self.app = GithubIntegration(
                int(self.app_id),
                private_key
            )
            
            # Get installation
            installations = list(self.app.get_installations())
            if installations:
                self.installation_id = installations[0].id
                github_logger.info(f"✅ GitHub App initialized (App ID: {self.app_id}, Installation: {self.installation_id})")
            else:
                github_logger.warning("No GitHub App installations found")
                return self._init_fallback()
            
            self._initialized = True
            return True
            
        except Exception as e:
            github_logger.error(f"Failed to initialize GitHub App: {e}")
            return self._init_fallback()
    
    def _init_fallback(self):
        """Fallback to Personal Access Token"""
        if self.fallback_token:
            github_logger.warning("⚠️ Using fallback authentication (PAT)")
            self._initialized = True
            return True
        else:
            github_logger.error("❌ No authentication method available")
            return False
    
    def get_installation_token(self, repo_full_name: str = None):
        """Get installation access token for a repository"""
        if not self._initialized:
            self.initialize()
        
        if not self.app or not self.installation_id:
            return self.fallback_token
        
        try:
            # Get token for the installation
            token = self.app.get_access_token(self.installation_id)
            github_logger.info(f"✅ Got installation token for ID: {self.installation_id}")
            return token.token
        except Exception as e:
            github_logger.error(f"Failed to get installation token: {e}")
            return self.fallback_token
    
    def get_github_client(self, repo_full_name: str = None):
        """Get authenticated GitHub client"""
        token = self.get_installation_token(repo_full_name)
        if token:
            github_logger.debug(f"Creating GitHub client with token")
            return Github(token)
        return None
    
    def verify_webhook_signature(self, request_body: bytes, signature_header: str) -> bool:
        """Verify webhook signature"""
        if not self.webhook_secret:
            return True
        
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            msg=request_body,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        expected = f"sha256={expected_signature}"
        return hmac.compare_digest(expected, signature_header or "")


# Global instance
github_app = GitHubAppAuth()