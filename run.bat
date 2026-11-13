@echo off
cd /d %~dp0
echo 커리어인연 서버를 켭니다... 브라우저에서 http://localhost:8000 을 여세요.
start "" http://localhost:8000
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
