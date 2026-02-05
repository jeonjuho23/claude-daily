@echo off
REM Daily-Bot Windows Task Scheduler Installation
REM Requires Administrator privileges
REM Creates a task that wakes computer from sleep

setlocal enabledelayedexpansion

echo ================================================
echo Daily-Bot Task Scheduler Setup
echo ================================================

REM Check for admin privileges
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script requires Administrator privileges
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Get paths
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set PYTHON_PATH=%PROJECT_DIR%\venv\Scripts\python.exe
set MAIN_SCRIPT=%PROJECT_DIR%\main.py

REM Verify paths exist
if not exist "%PYTHON_PATH%" (
    echo ERROR: Python virtual environment not found
    echo Please run setup_windows.bat first
    pause
    exit /b 1
)

REM Get schedule time from user
set /p SCHEDULE_TIME="Enter schedule time (HH:MM, 24-hour format) [default: 07:00]: "
if "%SCHEDULE_TIME%"=="" set SCHEDULE_TIME=07:00

REM Parse time
for /f "tokens=1,2 delims=:" %%a in ("%SCHEDULE_TIME%") do (
    set HOUR=%%a
    set MINUTE=%%b
)

echo.
echo Creating scheduled task...
echo   Time: %SCHEDULE_TIME%
echo   Python: %PYTHON_PATH%
echo   Script: %MAIN_SCRIPT%
echo.

REM Create the task XML
set TASK_XML=%TEMP%\daily_bot_task.xml

(
echo ^<?xml version="1.0" encoding="UTF-16"?^>
echo ^<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
echo   ^<RegistrationInfo^>
echo     ^<Description^>Daily-Bot - Automated CS Knowledge Sharing^</Description^>
echo   ^</RegistrationInfo^>
echo   ^<Triggers^>
echo     ^<CalendarTrigger^>
echo       ^<StartBoundary^>2024-01-01T%SCHEDULE_TIME%:00^</StartBoundary^>
echo       ^<Enabled^>true^</Enabled^>
echo       ^<ScheduleByDay^>
echo         ^<DaysInterval^>1^</DaysInterval^>
echo       ^</ScheduleByDay^>
echo     ^</CalendarTrigger^>
echo   ^</Triggers^>
echo   ^<Principals^>
echo     ^<Principal id="Author"^>
echo       ^<LogonType^>InteractiveToken^</LogonType^>
echo       ^<RunLevel^>LeastPrivilege^</RunLevel^>
echo     ^</Principal^>
echo   ^</Principals^>
echo   ^<Settings^>
echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^>
echo     ^<RunOnlyIfNetworkAvailable^>true^</RunOnlyIfNetworkAvailable^>
echo     ^<IdleSettings^>
echo       ^<StopOnIdleEnd^>false^</StopOnIdleEnd^>
echo       ^<RestartOnIdle^>false^</RestartOnIdle^>
echo     ^</IdleSettings^>
echo     ^<AllowStartOnDemand^>true^</AllowStartOnDemand^>
echo     ^<Enabled^>true^</Enabled^>
echo     ^<Hidden^>false^</Hidden^>
echo     ^<RunOnlyIfIdle^>false^</RunOnlyIfIdle^>
echo     ^<WakeToRun^>true^</WakeToRun^>
echo     ^<ExecutionTimeLimit^>PT1H^</ExecutionTimeLimit^>
echo     ^<Priority^>7^</Priority^>
echo   ^</Settings^>
echo   ^<Actions Context="Author"^>
echo     ^<Exec^>
echo       ^<Command^>%PYTHON_PATH%^</Command^>
echo       ^<Arguments^>%MAIN_SCRIPT%^</Arguments^>
echo       ^<WorkingDirectory^>%PROJECT_DIR%^</WorkingDirectory^>
echo     ^</Exec^>
echo   ^</Actions^>
echo ^</Task^>
) > "%TASK_XML%"

REM Delete existing task if exists
schtasks /delete /tn "Daily-Bot" /f >nul 2>&1

REM Create the task
schtasks /create /tn "Daily-Bot" /xml "%TASK_XML%"

if errorlevel 1 (
    echo ERROR: Failed to create scheduled task
    del "%TASK_XML%"
    pause
    exit /b 1
)

del "%TASK_XML%"

echo.
echo ================================================
echo Task created successfully!
echo ================================================
echo.
echo Task Name: Daily-Bot
echo Schedule: Daily at %SCHEDULE_TIME%
echo Wake from Sleep: Enabled
echo.
echo To view/modify: Task Scheduler ^> Daily-Bot
echo To run now: schtasks /run /tn "Daily-Bot"
echo To delete: schtasks /delete /tn "Daily-Bot" /f
echo.

pause
