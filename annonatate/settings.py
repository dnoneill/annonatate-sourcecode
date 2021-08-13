import os
from dotenv import load_dotenv

load_dotenv()
client_id = os.environ.get('ANNONATATE_CLIENT_ID')
client_secret = os.environ.get('ANNONATATE_CLIENT_SECRET')
print(client_id)
github_repo = "annonatate"
github_branch = "main"
uploadfolder="/tmp"
githubuserapi="https://api.github.com/user"
