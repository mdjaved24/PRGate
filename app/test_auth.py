# test_auth.py
from git_hub.client import git

print(f"Auth Method: {git.auth_method}")

# Test API call
user = git.get_user("mdjaved24")
print(f"✅ User: {user.login}")