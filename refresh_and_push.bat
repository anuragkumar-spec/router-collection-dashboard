@echo off
cd /d "C:\Users\Anurag Kumar\Downloads\ameo\dashboard_app"

echo [%date% %time%] Starting daily refresh...

:: Fetch fresh data from Metabase (reads key from C:\credentials\.env)
python refresh_data.py >> refresh.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: refresh_data.py failed >> refresh.log
    exit /b 1
)

:: Commit and push to GitHub (Railway auto-deploys on push)
git add static/data.json
git diff --staged --quiet && (
    echo [%date% %time%] No data changes, skipping push >> refresh.log
) || (
    git commit -m "chore: auto-refresh %date%"
    git push origin master >> refresh.log 2>&1
    echo [%date% %time%] Pushed to GitHub >> refresh.log
)

echo [%date% %time%] Done >> refresh.log
