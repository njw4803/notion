# Notion 경력기술서 자동화

**설치·사용 방법은 [CAREER_AUTOMATION_GUIDE.md](./CAREER_AUTOMATION_GUIDE.md) 하나만 읽으면 됩니다.**

동료에게 전달할 때:

- **문서:** `CAREER_AUTOMATION_GUIDE.md` (이 파일)
- **도구:** 스크립트, `content/` 기본 틀, `config.example.env`, `git_projects.example.yaml`, `githooks/`, `launchd/`, `requirements.txt`
- **제외:** `.env`, **채워진** `content/`, `git_projects.yaml`, `.*.json`, `.venv/`

```bash
./notion/setup.sh
cp notion/config.example.env notion/.env
cp notion/git_projects.example.yaml notion/git_projects.yaml
```
# notion
# notion
