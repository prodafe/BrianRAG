@REM @echo off
@REM title BrianRAG 启动器
@REM
@REM echo ========================================
@REM echo   BrianRAG 企业级服务启动中...
@REM echo ========================================
@REM
@REM :: ---------- 1. 设置环境变量 ----------
@REM set PROJECT_DIR=C:\Users\86153\PycharmProjects\PythonProject2
@REM cd /d %PROJECT_DIR%
@REM
@REM :: ---------- 2. 启动 PostgreSQL（绿色版） ----------
@REM echo [1/5] 启动 PostgreSQL...
@REM set PGSQL_DIR=D:\Pdb\postgresql-18.3-3-windows-x64-binaries\pgsql
@REM if exist "%PGSQL_DIR%\bin\pg_ctl.exe" (
@REM     start "PostgreSQL" /MIN cmd /c "%PGSQL_DIR%\bin\pg_ctl start -D %PGSQL_DIR%\data"
@REM     echo PostgreSQL 启动中...
@REM ) else (
@REM     echo 未找到 PostgreSQL，请检查路径
@REM )
@REM
@REM timeout /t 3 /nobreak >nul
@REM
@REM :: ---------- 3. 启动 Redis ----------
@REM echo [2/5] 启动 Redis...
@REM set REDIS_DIR=C:\redis
@REM if exist "%REDIS_DIR%\redis-server.exe" (
@REM     start "Redis" /MIN cmd /c "%REDIS_DIR%\redis-server.exe"
@REM     echo Redis 启动中...
@REM ) else (
@REM     echo 未找到 Redis，请检查路径
@REM )
@REM
@REM timeout /t 2 /nobreak >nul
@REM
@REM :: ---------- 4. 启动 Celery Worker ----------
@REM echo [3/5] 启动 Celery Worker...
@REM start "Celery Worker" /MIN cmd /c "celery -A tasks worker --loglevel=info --pool=threads --concurrency=2"
@REM timeout /t 3 /nobreak >nul
@REM
@REM :: ---------- 5. 启动 FastAPI ----------
@REM echo [4/5] 启动 FastAPI...
@REM start "FastAPI" /MIN cmd /c "uvicorn api.main:app --reload --port 8000"
@REM timeout /t 2 /nobreak >nul
@REM
@REM :: ---------- 6. 启动 Streamlit（前台窗口）----------
@REM echo [5/5] 启动 Streamlit 界面...
@REM start "Streamlit" cmd /c "streamlit run webui/app.py"
@REM
@REM echo.
@REM echo 所有服务已启动！
@REM echo 浏览器将打开 Streamlit 界面（http://localhost:8501）
@REM echo 关闭 Streamlit 窗口可结束服务。
@REM pause


# 启动 Redis
redis-server

# 启动 Celery Worker（需先激活虚拟环境）
celery -A tasks worker --loglevel=info --pool=threads --concurrency=2

# 启动 FastAPI
uvicorn api.main:app --reload --port 8000

# 启动 Streamlit
streamlit run webui/app.py