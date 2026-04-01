@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  BizPA Setup Script for Windows
echo ============================================
echo.

:: Check for Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js 18+ from https://nodejs.org
    exit /b 1
)

:: Check Node version
for /f "tokens=1 delims=v" %%i in ('node -v') do set NODE_VER=%%i
echo [OK] Node.js found: %NODE_VER%

:: Check for PostgreSQL psql
where psql >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARN] psql not found in PATH. Database setup will be skipped.
    echo        Install PostgreSQL or add psql to PATH to enable database setup.
    set SKIP_DB=1
) else (
    echo [OK] PostgreSQL psql found
    set SKIP_DB=0
)

:: Navigate to backend directory
cd /d "%~dp0solution\backend"
if %errorlevel% neq 0 (
    echo [ERROR] Could not find solution\backend directory
    exit /b 1
)

:: Create .env if not exists
if not exist ".env" (
    echo [INFO] Creating .env from .env.example...
    if exist "..\..\..\.env.example" (
        copy "..\..\..\.env.example" ".env" >nul
    ) else (
        echo [INFO] Creating default .env file...
        (
            echo PORT=5055
            echo DB_HOST=localhost
            echo DB_PORT=5432
            echo DB_NAME=bizpa
            echo DB_USER=postgres
            echo DB_PASSWORD=admin6093
            echo SUPABASE_URL=http://localhost:54321
            echo SUPABASE_ANON_KEY=your-anon-key
            echo SUPABASE_SERVICE_KEY=your-service-key
            echo JWT_SECRET=your-jwt-secret-change-in-production
        ) > ".env"
    )
    echo [OK] .env file created
) else (
    echo [OK] .env file exists
)

:: Install npm dependencies
echo.
echo [INFO] Installing npm dependencies...
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed
    exit /b 1
)
echo [OK] Dependencies installed

:: Database setup
if "%SKIP_DB%"=="0" (
    echo.
    echo [INFO] Setting up database...

    :: Load env vars
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if "%%a"=="DB_HOST" set DB_HOST=%%b
        if "%%a"=="DB_PORT" set DB_PORT=%%b
        if "%%a"=="DB_NAME" set DB_NAME=%%b
        if "%%a"=="DB_USER" set DB_USER=%%b
        if "%%a"=="DB_PASSWORD" set PGPASSWORD=%%b
    )

    :: Set defaults if not found
    if not defined DB_HOST set DB_HOST=localhost
    if not defined DB_PORT set DB_PORT=5432
    if not defined DB_NAME set DB_NAME=bizpa
    if not defined DB_USER set DB_USER=postgres

    :: Check if database exists
    psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -lqt 2>nul | findstr /c:"%DB_NAME%" >nul
    if %errorlevel% neq 0 (
        echo [INFO] Creating database %DB_NAME%...
        psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -c "CREATE DATABASE %DB_NAME%;" 2>nul
        if %errorlevel% neq 0 (
            echo [WARN] Could not create database. It may already exist or require manual creation.
        ) else (
            echo [OK] Database created
        )
    ) else (
        echo [OK] Database %DB_NAME% exists
    )

    :: Apply schema
    echo [INFO] Applying database schema...
    psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f "src\models\schema.sql" 2>nul
    if %errorlevel% neq 0 (
        echo [WARN] Schema application had warnings. Check database manually.
    ) else (
        echo [OK] Schema applied
    )

    :: Apply migrations
    echo [INFO] Applying migrations...
    for %%f in (src\models\*_migration.sql) do (
        echo   - Applying %%~nxf
        psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f "%%f" 2>nul
    )
    echo [OK] Migrations applied
)

:: Final status
echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo To start the server:
echo   cd solution\backend
echo   npm start
echo.
echo API will be available at:
echo   http://127.0.0.1:5055
echo   http://127.0.0.1:5055/api/v1
echo   http://127.0.0.1:5055/health
echo.

endlocal
