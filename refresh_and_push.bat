@echo off
cd /d "C:\Users\Anurag Kumar\Downloads\router-collection-dashboard"

echo [%date% %time%] Starting daily refresh... >> refresh.log

python refresh_data.py >> refresh.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERROR: refresh_data.py failed >> refresh.log
    exit /b 1
)

git add docs/index.html
git diff --staged --quiet && (
    echo [%date% %time%] No changes, skipping push >> refresh.log
) || (
    git commit -m "chore: auto-refresh %date%"
    git push origin master >> refresh.log 2>&1
    echo [%date% %time%] Pushed to GitHub >> refresh.log
)

echo [%date% %time%] Done >> refresh.log
