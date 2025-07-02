@echo off
REM Batch file to compile the CDMO report on Windows

echo CDMO Report Compilation Script
echo ==============================

REM Check if pdflatex is available
where pdflatex >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pdflatex not found in PATH
    echo Please install a LaTeX distribution like MiKTeX or TeX Live
    echo and ensure pdflatex is in your system PATH
    pause
    exit /b 1
)

echo Found pdflatex, proceeding with compilation...
echo.

REM First pass
echo [1/3] First compilation pass...
pdflatex -interaction=nonstopmode -halt-on-error main.tex
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: First compilation pass failed
    echo Check main.log for details
    pause
    exit /b 1
)

REM Second pass (for cross-references)
echo [2/3] Second compilation pass...
pdflatex -interaction=nonstopmode -halt-on-error main.tex
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Second compilation pass failed
    echo Check main.log for details
    pause
    exit /b 1
)

REM Third pass (to ensure everything is updated)
echo [3/3] Third compilation pass...
pdflatex -interaction=nonstopmode -halt-on-error main.tex
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Third compilation pass failed
    echo Check main.log for details
    pause
    exit /b 1
)

echo.
echo ==============================
echo Compilation completed successfully!
echo Generated: main.pdf

REM Check if PDF was created
if exist main.pdf (
    echo PDF file size: 
    for %%A in (main.pdf) do echo %%~zA bytes
    echo.
    
    REM Ask if user wants to open the PDF
    set /p OPEN="Open the PDF now? (y/n): "
    if /i "%OPEN%"=="y" (
        echo Opening main.pdf...
        start main.pdf
    )
) else (
    echo WARNING: main.pdf was not generated
    echo Check the compilation log for errors
)

echo.
echo To clean auxiliary files, run: clean.bat
echo To rebuild from scratch, delete main.pdf and run this script again
pause
