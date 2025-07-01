@echo off
REM Batch file to clean LaTeX auxiliary files on Windows

echo CDMO Report Cleanup Script
echo ==========================

echo Cleaning LaTeX auxiliary files...

REM Remove auxiliary files
if exist *.aux del /q *.aux && echo Removed: *.aux
if exist *.log del /q *.log && echo Removed: *.log
if exist *.out del /q *.out && echo Removed: *.out
if exist *.toc del /q *.toc && echo Removed: *.toc
if exist *.bbl del /q *.bbl && echo Removed: *.bbl
if exist *.blg del /q *.blg && echo Removed: *.blg
if exist *.fls del /q *.fls && echo Removed: *.fls
if exist *.fdb_latexmk del /q *.fdb_latexmk && echo Removed: *.fdb_latexmk
if exist *.synctex.gz del /q *.synctex.gz && echo Removed: *.synctex.gz
if exist *.nav del /q *.nav && echo Removed: *.nav
if exist *.snm del /q *.snm && echo Removed: *.snm
if exist *.vrb del /q *.vrb && echo Removed: *.vrb
if exist *.lof del /q *.lof && echo Removed: *.lof
if exist *.lot del /q *.lot && echo Removed: *.lot

echo.
echo Auxiliary files cleaned!

REM Ask if user wants to remove PDF as well
set /p REMOVE_PDF="Remove main.pdf as well? (y/n): "
if /i "%REMOVE_PDF%"=="y" (
    if exist main.pdf (
        del main.pdf
        echo Removed: main.pdf
    ) else (
        echo main.pdf not found
    )
)

echo.
echo Cleanup completed!
pause
