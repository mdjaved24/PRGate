<div align="center">

# 🔒 PRGate

### Automated Security Review Bot for GitHub Pull Requests

[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green.svg)](https://www.mongodb.com/)
[![Groq](https://img.shields.io/badge/Groq-LLM-orange.svg)](https://groq.com/)

**AI-powered GitHub bot that automatically reviews PRs for security vulnerabilities and blocks merges if critical issues are found.**

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI-Powered Analysis** | Uses Groq Llama 3.3 70B to detect 20+ vulnerability types |
| 🚫 **Merge Blocking** | Automatically blocks PRs with critical/high severity issues |
| 💬 **Smart Comments** | Posts detailed findings with CWE references and actionable fixes |
| 🏷️ **Auto-Labeling** | Adds severity labels like `security-critical` and `needs-security-review` |
| 📊 **Analytics** | Tracks developer patterns, repository risk scores, and historical trends |
| ⚡ **Performance** | Parallel reviews, intelligent caching, and rate limiting |

---

## 🛠️ Technologies Used

| 🏷️ Component | 🔧 Technology | 📝 Description |
|--------------|---------------|----------------|
| ⚡ Web Framework | FastAPI + Uvicorn | High-performance async API server |
| 🤖 AI/LLM | Groq (Llama 3.3 70B) | Security vulnerability detection |
| 📦 GitHub | PyGithub | PR, comment, and status management |
| 🗄️ Database | MongoDB + Motor | Async document storage |
| ✅ Validation | Pydantic | Type-safe data validation |
| 🔗 Tunneling | ngrok | Local webhook testing |
| 🐍 Language | Python 3.13+ | Core programming language |
| 💾 Caching | In-Memory Dictionary | Review result caching |
| ⏱️ Rate Limiting | Custom Implementation | API request throttling |
| 🔄 Async | asyncio + ThreadPool | Parallel file processing |

---

## 🏗️ Architecture

```mermaid
graph TD
    A[GitHub PR] -->|Webhook| B[ngrok Tunnel]
    B -->|HTTP POST| C[FastAPI Server]
    C -->|Validate| D[Filter Files]
    D -->|Parallel| E[Review Files]
    
    E -->|Check| F{In Cache?}
    F -->|Yes| G[Return Cached]
    F -->|No| H[Groq LLM]
    
    H -->|JSON| I[Parse Response]
    I -->|Findings| J[Create Status Check]
    
    J -->|Success/Failure| K{Block Merge?}
    K -->|Critical/High| L[❌ Block Merge]
    K -->|Pass| M[✅ Allow Merge]
    
    I --> N[Post PR Comment]
    I --> O[Add Labels]
    I --> P[Save to MongoDB]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style L fill:#ff6b6b,stroke:#333,stroke-width:2px
    style M fill:#51cf66,stroke:#333,stroke-width:2px
    style P fill:#4dabf7,stroke:#333,stroke-width:2px
```
### Component Details

- **Webhook Receiver** → FastAPI → Incoming GitHub events
- **LLM Processor** → Groq Llama 3.3 70B → Security analysis
- **Cache** → In-Memory Dictionary → Repeated code review caching
- **Database** → MongoDB → Persistent storage
- **Queue** → Async ThreadPool → Parallel file processing
- **Rate Limiter** → Custom → API abuse prevention

---

## 🔍 Detected Vulnerabilities

### 🔴 CRITICAL
- SQL Injection (CWE-89)
- Hardcoded Secrets (CWE-798)
- Command Injection (CWE-78)
- XXE Injection (CWE-611)
- Insecure Deserialization (CWE-502)

### 🟠 HIGH
- Path Traversal (CWE-22)
- Weak Cryptography (CWE-327)
- LDAP Injection (CWE-90)
- Open Redirect (CWE-601)

### 🟡 MEDIUM
- XSS (CWE-79)
- CSRF (CWE-352)
- Insecure CORS

## 📦 Installation

### Prerequisites

- Python 3.13+
- MongoDB
- Groq API Key
- GitHub Personal Access Token

---

### 1. Clone Repository

```bash
git clone https://github.com/mdjaved24/prgate.git
cd prgate
- Missing Rate Limiting
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment
- Create a .env file:
```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxx
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=pr_gate
MONGODB_ENABLED=true
```

### 5. Start MongoDB

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 6. Run Application

```bash
cd app
python main.py
```

### 7. Expose with ngrok (Development)

```bash
ngrok http 8000
```

**Note:** The virtual environment activation command shown is for **Windows**. For **Linux/Mac**, use:

```bash
python3 -m venv venv
source venv/bin/activate
```
---

## 🔧 GitHub Configuration

### 1. Create Personal Access Token

```bash
Settings → Developer settings → Personal access tokens → Fine-grained tokens
```

### Required Permissions

| Permission | Access Level |
|------------|--------------|
| Pull requests | Read and write |
| Issues | Read and write |
| Commit statuses | Read and write |
| Contents | Read-only |
| Metadata | Read-only |

---

### 2. Configure Webhook

| Setting | Value |
|---------|-------|
| Payload URL | `https://your-domain.com/git/webhook` |
| Content type | `application/json` |
| Events | Pull requests, Ping |

---

### 3. Set Branch Protection

Navigate to: `Settings → Branches → Add branch protection rule`

**Enable these options:**

- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
- ✅ Select `PRGate Security Review`

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/git/health` | GET | Service status |
| `/git/webhook` | POST | GitHub webhook receiver |
| `/git/git_user/{username}` | GET | Get GitHub user information |
| `/git/cache/stats` | GET | Cache statistics |
| `/git/cache/clear` | POST | Clear all cache |
| `/git/stats/developer/{username}` | GET | Developer analytics |
| `/git/stats/repository/{repository}` | GET | Repository analytics |
| `/git/review/{review_id}` | GET | Get review details |

---

## ⚡ Performance Metrics

| Metric | Value |
|--------|-------|
| First review time | 2-5 seconds per file |
| Cached review time | <0.1 second |
| Cache TTL | 1 hour |
| Max concurrent reviews | 3 files |
| Rate limit | 10 requests per minute per repository |

---
## 📁 Project Structure

```
prgate/
├── main.py
├── requirements.txt
├── .env
├── git_hub/
│   ├── __init__.py
│   ├── client.py
│   ├── pr_fetcher.py
│   ├── status_checks.py
│   └── pr_comment.py
├── llm/
│   ├── __init__.py
│   ├── prompts.py
│   ├── parser.py
│   └── reviewer.py
├── models/
│   ├── __init__.py
│   └── findings.py
├── utils/
│   ├── __init__.py
│   ├── rate_limiter.py
│   └── cache.py
└── database/
    ├── __init__.py
    ├── mongodb_client.py
    └── repository.py
```

### File Descriptions

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application entry point |
| `requirements.txt` | Python package dependencies |
| `.env` | Environment variables configuration |
| `git_hub/client.py` | GitHub API client wrapper |
| `git_hub/pr_fetcher.py` | Webhook request handlers |
| `git_hub/status_checks.py` | Commit status & label management |
| `git_hub/pr_comment.py` | PR comment formatting |
| `llm/prompts.py` | AI prompt templates |
| `llm/parser.py` | JSON response parsing |
| `llm/reviewer.py` | Groq LLM integration |
| `models/findings.py` | Pydantic data models |
| `utils/rate_limiter.py` | API rate limiting |
| `utils/cache.py` | Review result caching |
| `database/mongodb_client.py` | MongoDB connection manager |
| `database/repository.py` | Database operations |

---

## 📝 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ Yes | - | Groq API key for LLM access |
| `GITHUB_TOKEN` | ✅ Yes | - | GitHub Personal Access Token |
| `MONGODB_URL` | ❌ No | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | ❌ No | `pr_gate` | Database name |
| `MONGODB_ENABLED` | ❌ No | `true` | Enable/disable database logging |
| `CACHE_MAX_SIZE` | ❌ No | `100` | Maximum cache entries |
| `CACHE_TTL_SECONDS` | ❌ No | `3600` | Cache time-to-live in seconds |
| `RATE_LIMIT_MAX_REQUESTS` | ❌ No | `10` | Maximum requests per time window |
| `RATE_LIMIT_TIME_WINDOW` | ❌ No | `60` | Rate limit time window in seconds |

---

### Sample `.env` File

```env
# Required
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
GITHUB_TOKEN=github_pat_xxxxxxxxxxxxx

# Optional - MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=pr_gate
MONGODB_ENABLED=true

# Optional - Cache
CACHE_MAX_SIZE=100
CACHE_TTL_SECONDS=3600

# Optional - Rate Limiting
RATE_LIMIT_MAX_REQUESTS=10
RATE_LIMIT_TIME_WINDOW=60
```

## 🐛 Troubleshooting

### Webhook not received?

| Issue | Solution |
|-------|----------|
| ngrok URL incorrect | Verify ngrok is running and URL is correct |
| Webhook inactive | Check GitHub webhook settings, ensure it's enabled |
| Server not running | Run `python main.py` and check for errors |
| Network issues | Check firewall and internet connection |

### MongoDB connection failed?

| Issue | Solution |
|-------|----------|
| MongoDB not running | Run `docker ps` to check container status |
| Wrong connection string | Verify `MONGODB_URL` in `.env` file |
| Port conflict | Ensure port 27017 is not in use |
| Database disabled | Set `MONGODB_ENABLED=true` in `.env` |

### GitHub token errors?

| Issue | Solution |
|-------|----------|
| Invalid token | Regenerate token in GitHub settings |
| Expired token | Check token expiration date |
| Missing permissions | Verify all required permissions are granted |
| Wrong repository | Ensure token has access to the repository |

### LLM review failing?

| Issue | Solution |
|-------|----------|
| Invalid API key | Verify `GROQ_API_KEY` in `.env` |
| Rate limit exceeded | Wait and retry, or upgrade Groq plan |
| Network timeout | Check internet connection |
| Invalid code format | Ensure code patch is valid |

---

## 👥 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 .
```
---


## 📧 Contact & Support

| Platform | Link |
|----------|------|
| 📧 Email | mdjav077@gmail.com |
| 🐙 GitHub | [@mdjaved24](https://github.com/mdjaved24) |
| 📝 Issues | [Report Bug](https://github.com/mdjaved24/prgate/issues) |
| 💡 Feature Request | [Request Feature](https://github.com/mdjaved24/prgate/issues/new) |

---

### 🙏 Acknowledgments

- [Groq](https://groq.com/) for providing the LLM API
- [FastAPI](https://fastapi.tiangolo.com/) for the amazing web framework
- [PyGithub](https://pygithub.readthedocs.io/) for GitHub API integration
- [MongoDB](https://www.mongodb.com/) for database services

---

### ⭐ Show Your Support

If you found this project helpful, please give it a ⭐ on GitHub!

---

**Built to make code safer 🔒**
