# GitHub AI Agent

Autonomous AI developer agent yang mengotomatisasi penanganan GitHub Issues dan Pull Request reviews menggunakan Gemini AI dan GitHub CLI. Agent secara otomatis memonitor dan memproses issues/PRs dari semua repositories di organization Anda.

## 🎯 Fitur Utama

- **Multi-Repository**: Otomatis detect dan process semua repos di organization
- **Parallel Scanning**: Check repos secara parallel untuk performa optimal
- **Smart Cloning**: Hanya clone repos yang memiliki issues/PRs assigned
- **Auto Issue Resolution**: Generate solusi, create branch, commit, dan buat PR otomatis
- **Auto PR Fixes**: Detect PRs dengan "changes requested", apply fixes, dan re-request review
- **Flexible Processing**: Process issues only, PRs only, atau keduanya
- **GitHub CLI Integration**: OAuth authentication, no token needed
- **Gemini CLI Support**: Support Gemini Pro untuk kualitas code generation terbaik
- **Web UI Control Panel**: Manage agents, update configurations, monitor logs, & edit workspace contexts tanpa coding.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install GitHub CLI
brew install gh        # Mac
# sudo apt install gh  # Linux
# winget install GitHub.cli  # Windows

# Install Gemini CLI
npm install -g @google/generative-ai-cli
```

### 2. Authenticate

```bash
# GitHub CLI
gh auth login

# Gemini CLI
gemini auth login
```

### 3. Configure

```bash
cp .env.example .env
nano .env
```

Edit `.env` - hanya perlu set 1 baris:

```bash
GITHUB_ORGANIZATION=your-organization-name
```

### 4. Run

**Opsi 1: Menggunakan Web UI Control Panel (Direkomendasikan)**

```bash
# Mac / Linux
chmod +x start.sh
./start.sh

# Windows
start.bat
```

Buka browser dan akses: `http://localhost:8000`.

**Opsi 2: Menggunakan CLI**

```bash
# Continuous mode (check every 5 minutes, default)
python3 -m src.main

# Custom interval (check every 10 minutes)
python3 -m src.main --interval 600

# Single run (check once and exit)
python3 -m src.main --interval 0

# Process PRs only (continuous)
python3 -m src.main --pr

# Process issues only (single run)
python3 -m src.main --issue --interval 0
```

## 📋 Prerequisites

- **Python 3.11+**
- **GitHub CLI** (`gh`) - [Install Guide](https://cli.github.com/)
- **Gemini CLI** - [Install Guide](https://www.npmjs.com/package/@google/generative-ai-cli)
- **Git** terinstall di sistem

## 🔧 Configuration

### Required

```bash
# Organization name
GITHUB_ORGANIZATION=mycompany
```

### Optional Settings

```bash
# Check interval in seconds (default: 300 = 5 minutes)
CHECK_INTERVAL=300

# Logging level
LOG_LEVEL=INFO

# Target branch for PRs
DEFAULT_TARGET_BASE_BRANCH=main

# Directory for cloned repos
REPOSITORIES_DIR=repositories
```

## 🎮 Usage

### Web UI Control Panel

Control panel menyediakan antarmuka modern untuk mengatur agent:

- **Execution Control**: Start/stop agent dan lihat live logs.
- **Global Configuration**: Edit token API, target branch, dan konfigurasi repo.
- **Prompt Tools**: Buat dan edit template prompt custom untuk PR feedback & Issue solver.
- **Workspaces & Rules**: Edit file `.context` dan `.agents` di tiap repository menggunakan code editor.
- **Queue Observer**: Lihat riwayat aktivitas PR dan Issue execution.

Jalankan dengan: `./start.sh` (Mac/Linux) atau `start.bat` (Windows).

### Continuous Mode CLI (Default)

Agent berjalan terus menerus dan check setiap 5 menit:

```bash
# Default: Check every 5 minutes
python3 -m src.main

# Custom interval: Check every 10 minutes
python3 -m src.main --interval 600
```

### Single Run Mode

Check sekali lalu exit:

```bash
python3 -m src.main --interval 0
```

### Process Specific Types

```bash
# PRs only (continuous)
python3 -m src.main --pr

# Issues only (continuous)
python3 -m src.main --issue

# PRs only (single run)
python3 -m src.main --pr --interval 0
```

### With Debug Logging

```bash
python3 -m src.main --log-level DEBUG
```

## 📊 How It Works

### Issue Handling Flow

```
1. Issue assigned to you
   ↓
2. Agent scans and detects issue
   ↓
3. Clone repository (if not exists)
   ↓
4. Generate solution with Gemini AI
   ↓
5. Create branch: fix/issue-{number}
   ↓
6. Apply changes to files
   ↓
7. Commit & push
   ↓
8. Create Pull Request
```

### PR Review Handling Flow

```
1. PR gets "changes requested" review
   ↓
2. Agent scans and detects PR
   ↓
3. Checkout PR branch
   ↓
4. Fetch review comments
   ↓
5. Generate fixes with Gemini AI
   ↓
6. Apply fixes to files
   ↓
7. Commit & push
   ↓
8. Re-request review
```

## � Running as Service

### Systemd Service (Linux)

Create `/etc/systemd/system/github-agent.service`:

```ini
[Unit]
Description=GitHub AI Agent
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/github-ai-agent
ExecStart=/usr/bin/python3 -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable github-agent
sudo systemctl start github-agent
sudo systemctl status github-agent

# View logs
sudo journalctl -u github-agent -f
```

### Docker

Simple Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python3", "-m", "src.main"]
```

Build and run:

```bash
docker build -t github-agent .

# Run in background
docker run -d --name github-agent --env-file .env github-agent

# View logs
docker logs -f github-agent
```

Docker Compose:

```yaml
version: "3.8"
services:
  github-agent:
    build: .
    env_file: .env
    restart: unless-stopped
```

Run:

```bash
docker-compose up -d
docker-compose logs -f
```

## 🧪 Testing

### Test Issue Processing

1. Create issue di repository
2. Assign issue ke diri sendiri
3. Run: `python3 -m src.main --issue --interval 0`

**Expected output**:

```
[INFO] GitHub AI Multi-Repo Agent starting
[INFO] Organization: mycompany
[INFO] Searching for assigned issues...
[INFO] Found 1 assigned issues across 1 repositories
[INFO] Processing repository: myrepo
[INFO] Cloning repository: myrepo
[INFO] Processing issue #123: Fix login bug
[INFO] Generating solution from Gemini
[INFO] Created branch: fix/issue-123
[INFO] Applied changes to 2 files
[INFO] Created Pull Request #124
[INFO] ✓ Completed processing myrepo
```

### Test PR Review Processing

1. Create PR di repository
2. Request changes pada PR
3. Run: `python3 -m src.main --pr`

**Expected output**:

```
[INFO] GitHub AI Multi-Repo Agent starting
[INFO] Organization: mycompany
[INFO] Found 10 repositories in organization
[INFO] Checking for Issues and PRs (Parallel Scan)
[INFO] ✓ myrepo: 0 issues, 1 PRs
[INFO] Processing repository: myrepo
[INFO] Processing PR #125: Add new feature
[INFO] Checking out PR branch
[INFO] Found 3 review comments
[INFO] Generating fixes from Gemini
[INFO] Applied fixes to 3 files
[INFO] Pushed changes
[INFO] Re-requested review
[INFO] ✓ Completed processing myrepo
[INFO] Agent completed successfully
```

## 🔍 Troubleshooting

### "GitHub CLI not authenticated"

```bash
# Login
gh auth login

# Verify
gh auth status
```

### "Gemini CLI not found"

```bash
# Install
npm install -g @google/generative-ai-cli

# Login
gemini auth login

# Or specify path in .env
GEMINI_CLI_PATH=/usr/local/bin/gemini
```

### "No issues or PRs to process"

Ini normal jika:

- Tidak ada issues assigned ke Anda
- Tidak ada PRs dengan "changes requested"
- Semua work sudah diprocess

### "Permission denied" saat clone

```bash
# Check GitHub CLI authentication
gh auth status

# Re-login if needed
gh auth login

# Make sure you have access to the repositories
gh repo list YOUR_ORG
```

### "Configuration error: GITHUB_ORGANIZATION is required"

Pastikan `.env` file ada dan berisi:

```bash
GITHUB_ORGANIZATION=your-org-name
GEMINI_API_KEY=your-key
```

### Debug Mode

```bash
# Run dengan debug logging untuk detail lengkap
python3 -m src.main --log-level DEBUG

# Check specific repository
python3 -m src.main --log-level DEBUG 2>&1 | grep "repository-name"
```

## 📈 Performance

### Resource Usage

| Scenario         | CPU    | Memory | Disk               |
| ---------------- | ------ | ------ | ------------------ |
| Scanning repos   | 10-20% | ~100MB | Minimal            |
| Processing issue | 20-30% | ~200MB | ~50-200MB per repo |
| Processing PR    | 20-30% | ~200MB | ~50-200MB per repo |

### Scalability

- ✅ Tested dengan 100+ repositories
- ✅ Parallel scanning (max 10 concurrent API calls)
- ✅ Efficient cloning (hanya repos dengan work)
- ✅ Smart caching (reuse cloned repos)
- ✅ Dapat dijalankan via cron untuk continuous automation

### Performance Tips

1. **Use Gemini CLI** untuk rate limit lebih tinggi (1000 RPM vs 15 RPM)
2. **Use GitHub CLI** untuk avoid rate limiting
3. **Setup cron** dengan interval yang sesuai (5-15 menit recommended)
4. **Monitor logs** untuk identify bottlenecks
5. **Clean old repos** di `repositories/` folder jika disk space terbatas

## 🔒 Security

### Best Practices

1. **Use GitHub CLI**: OAuth app authentication (no tokens in .env)
2. **Review PRs**: Always review AI-generated code sebelum merge
3. **Rotate Credentials**: Rotate API keys secara berkala
4. **Run as Non-Root**: Jangan run agent sebagai root user
5. **Limit Permissions**: Pastikan GitHub CLI hanya punya access yang diperlukan
6. **Secure .env**: Jangan commit .env file ke repository
7. **Monitor Logs**: Regular check logs untuk suspicious activity

### GitHub CLI Permissions

Pastikan GitHub CLI punya permissions yang tepat:

```bash
# Check current permissions
gh auth status

# Refresh authentication if needed
gh auth refresh -h github.com -s repo,read:org
```

### API Key Security

```bash
# Store API key securely
chmod 600 .env

# Use environment-specific keys
# Development: GEMINI_API_KEY_DEV
# Production: GEMINI_API_KEY_PROD
```

## ❓ FAQ

**Q: Apakah perlu API keys atau tokens?**
A: Tidak! Semua authentication via CLI tools (gh dan gemini). Lebih simple dan secure.

**Q: Berapa banyak repos yang bisa di-handle?**
A: Unlimited. Agent hanya clone repos yang punya work, dan menggunakan parallel scanning untuk performa optimal.

**Q: Apakah perlu Gemini Pro account?**
A: Ya, Gemini CLI memerlukan Pro account ($20/month). Benefits: 1000 RPM, 2M tokens, kualitas lebih baik.

**Q: Apakah work untuk private repos?**
A: Ya! Pastikan `gh auth login` punya access ke private repos di organization Anda.

**Q: Bagaimana cara hanya process issues atau PRs saja?**
A: Gunakan flag `--issue` untuk issues only atau `--pr` untuk PRs only.

**Q: Bagaimana cara menjalankan secara otomatis?**
A: Setup cron job untuk menjalankan agent secara berkala. Lihat section "Automation with Cron" di atas.

**Q: Apakah agent akan process PR yang dibuat oleh agent sendiri?**
A: Tidak. Agent hanya process PRs dengan "changes requested" review status.

**Q: Bagaimana cara stop agent?**
A: Press Ctrl+C jika running di foreground. Jika via cron, comment out atau delete cron entry.

**Q: Apakah bisa customize branch naming?**
A: Ya, edit `src/handlers/issue_handler.py` dan `src/handlers/pr_handler.py` untuk customize branch naming logic.

**Q: Bagaimana cara exclude certain repositories?**
A: Saat ini belum ada built-in feature. Anda bisa modify `src/multi_repo_agent.py` untuk add exclusion list.

## 📁 Project Structure

```
github-ai-agent/
├── dashboard/                     # Web UI Control Panel
│   ├── main.py                    # FastAPI server
│   ├── database.py                # SQLite config storage
│   ├── routes/                    # API Endpoints
│   └── templates/                 # HTML UI
├── src/
│   ├── main.py                    # Entry point CLI
│   ├── config.py                  # Configuration reader
│   ├── multi_repo_agent.py        # Main orchestrator
│   ├── repository_manager.py      # Repository management
│   ├── clients/
│   │   ├── gemini_client.py       # Gemini API client
│   │   ├── gemini_cli_client.py   # Gemini CLI client
│   │   ├── github_client.py       # GitHub API client
│   │   └── github_cli_client.py   # GitHub CLI client
│   ├── git/
│   │   └── git_manager.py         # Git operations
│   ├── handlers/
│   │   ├── issue_handler.py       # Issue processing
│   │   └── pr_handler.py          # PR processing
│   ├── models/
│   │   └── data_models.py         # Data classes
│   └── utils/
│       └── errors.py              # Custom exceptions
├── repositories/                  # Auto-created, cloned repos
├── .agent_data/                   # SQLite database control panel
├── .env                           # Configuration (create dari .env.example)
├── .env.example                   # Configuration template
├── start.sh                       # Start script (Mac/Linux)
├── start.bat                      # Start script (Windows)
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 🎉 Summary

GitHub AI Agent adalah autonomous developer agent yang:

✅ **Multi-Repository**: Process semua repos di organization secara otomatis

✅ **Auto Issue Resolution**: Detect assigned issues, generate solution, create PR

✅ **Auto PR Fixes**: Detect changes requested, apply fixes, re-request review

✅ **Flexible**: Process issues only, PRs only, atau keduanya

✅ **Simple Setup**: No API keys needed, just CLI authentication

✅ **Efficient**: Parallel scanning, smart cloning, minimal resource usage

✅ **Production-Ready**: Scalable, reliable, easy to automate with cron

## 🚀 Get Started in 3 Minutes

```bash
# 1. Install & Run
# macOS / Linux
chmod +x start.sh
./start.sh

# Windows
start.bat

# 2. Control Panel
# Open http://localhost:8000 in your browser
# Setup your Gemini CLI and GitHub CLI auth
# Configure your rules and enjoy zero-code execution!

# Done! 🎉
```

## 📚 Additional Resources

- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Cron Expression Generator](https://crontab.guru/)

## 💬 Support

Untuk issues atau questions:

- Check troubleshooting section di atas
- Run dengan `--log-level DEBUG` untuk detail
- Open issue di GitHub repository

---

**Made with ❤️ using Gemini AI and GitHub CLI**
