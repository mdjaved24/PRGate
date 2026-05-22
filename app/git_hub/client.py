from github import Github
from dotenv import load_dotenv
import os

github_token = os.getenv('GITHUB_TOKEN')

git = Github(github_token)