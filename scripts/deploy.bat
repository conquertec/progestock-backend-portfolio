@echo off
REM Safe deployment script for Windows
REM Usage: scripts\deploy.bat [staging|production]

setlocal enabledelayedexpansion

set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=staging

echo.
echo ================================
echo ProGestock Deployment Script
echo ================================
echo.
echo Target environment: %ENVIRONMENT%
echo.

REM Get current branch
for /f "tokens=*" %%a in ('git branch --show-current') do set CURRENT_BRANCH=%%a

REM Check if on correct branch
if "%ENVIRONMENT%"=="production" (
    if not "%CURRENT_BRANCH%"=="main" (
        echo [ERROR] Must be on 'main' branch to deploy to production
        echo Current branch: %CURRENT_BRANCH%
        exit /b 1
    )
)

if "%ENVIRONMENT%"=="staging" (
    if not "%CURRENT_BRANCH%"=="staging" (
        echo [ERROR] Must be on 'staging' branch to deploy to staging
        echo Current branch: %CURRENT_BRANCH%
        exit /b 1
    )
)

echo [OK] Branch check passed: %CURRENT_BRANCH%
echo.

REM Check for uncommitted changes
git diff-index --quiet HEAD --
if %errorlevel% neq 0 (
    echo [ERROR] You have uncommitted changes
    echo Please commit or stash your changes before deploying.
    exit /b 1
)
echo [OK] No uncommitted changes
echo.

REM Run tests
echo Running tests...
python manage.py test --verbosity=2
if %errorlevel% neq 0 (
    echo [ERROR] Tests failed! Deployment aborted.
    exit /b 1
)
echo [OK] All tests passed
echo.

REM Check migrations
echo Checking for migration issues...
python manage.py makemigrations --check --dry-run >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] There may be new migrations
    set /p CONTINUE="Have you tested migrations on staging? (y/N): "
    if /i not "!CONTINUE!"=="y" (
        echo Deployment aborted.
        exit /b 1
    )
) else (
    echo [OK] No migration issues detected
)
echo.

REM Confirm production deployment
if "%ENVIRONMENT%"=="production" (
    echo ==========================================
    echo   PRODUCTION DEPLOYMENT WARNING
    echo ==========================================
    echo.
    echo This will deploy to production and affect your 4 active users!
    echo.
    echo Pre-deployment checklist:
    echo   - Have you tested on staging?
    echo   - Are all tests passing?
    echo   - Have you checked the Railway staging logs?
    echo   - Are there any breaking changes?
    echo   - Is the team aware of this deployment?
    echo.
    set /p CONFIRM="Type 'yes' to deploy to PRODUCTION: "
    if /i not "!CONFIRM!"=="yes" (
        echo Deployment aborted.
        exit /b 1
    )
)

REM Deploy
echo.
echo Deploying to %ENVIRONMENT%...
echo.

git pull origin %CURRENT_BRANCH%
git push origin %CURRENT_BRANCH%

echo.
echo ================================
echo Deployment initiated!
echo ================================
echo.

if "%ENVIRONMENT%"=="staging" (
    echo Next steps:
    echo 1. Wait 3-5 minutes for deployment to complete
    echo 2. Check staging environment
    echo 3. Review Railway staging logs: railway logs
    echo 4. Test all critical features
    echo 5. If good, deploy to production: scripts\deploy.bat production
) else (
    echo Next steps:
    echo 1. Wait 3-5 minutes for deployment to complete
    echo 2. Check production environment
    echo 3. Review Railway logs: railway logs
    echo 4. Monitor for errors for 10 minutes
    echo 5. Test critical paths: login, invoice, email
    echo 6. Have rollback plan ready
)

echo.
pause
