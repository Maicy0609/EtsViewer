@echo off
REM ---------------------------------------------------------------
REM  EtsViewer standalone build (Nuitka, onedir, no single-file)
REM  Usage:  build.bat
REM  Output: build\EtsViewer\EtsViewer.exe
REM ---------------------------------------------------------------
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"
set "ZIG=%CD%\%VENV%\Lib\site-packages\ziglang\zig.exe"
REM Do NOT name this variable UPX: upx.exe itself reads an environment
REM variable called UPX and would try to parse the path as options.
set "UPX_BIN=tools\upx-4.2.4-win64\upx.exe"
set "UPX_URL=https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip"

REM Refuse to build while the app is running: a live process keeps
REM wxmsw334u_core_*.dll / wx\_core.pyd mapped, so UPX silently fails with
REM "Permission denied" and you end up with a half-compressed output.
REM Full paths are used because a Git-for-Windows `find.exe` on PATH would
REM otherwise shadow the Windows one and break the check.
"%SystemRoot%\System32\tasklist.exe" /fi "IMAGENAME eq EtsViewer.exe" /nh 2>nul | "%SystemRoot%\System32\findstr.exe" /i /c:"EtsViewer.exe" >nul
if not errorlevel 1 (
    echo ERROR: EtsViewer.exe is running. Close it, then run build.bat again.
    goto :err
)

if not exist "%PY%" (
    echo [1/3] Creating venv and installing dependencies ...
    python -m venv "%VENV%" || goto :err
    "%PY%" -m pip install --upgrade pip || goto :err
    "%PY%" -m pip install nuitka wxPython ziglang || goto :err
) else (
    echo [1/3] Reusing existing venv.
)

echo [2/3] Compiling with Nuitka ...
if not exist "%ZIG%" (
    echo ERROR: zig not found at "%ZIG%".
    echo Run: %PY% -m pip install ziglang
    goto :err
)

REM MSVC without the Windows SDK cannot be used, and --mingw64 is rejected on
REM Python 3.13+, so point CC at the zig shipped inside the venv.
set "CC=%ZIG%"

"%PY%" -m nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --output-dir=build ^
  --output-filename=EtsViewer.exe ^
  --nofollow-import-to=numpy,scipy,pandas,matplotlib,PIL,Pillow,tkinter,unittest,pydoc,doctest,setuptools,pip,wheel,wx.adv,wx.html,wx.html2,wx.net,wx.xml,wx.xrc,wx.media,wx.richtext,wx.stc,wx.aui,wx.propgrid,wx.ribbon,wx.dataview,wx.grid,wx.glcanvas ^
  --python-flag=no_docstrings,no_asserts,no_site ^
  --product-name=EtsViewer --file-version=1.0.1 --product-version=1.0.1 ^
  main.py || goto :err

if exist "build\EtsViewer" rmdir /s /q "build\EtsViewer"
if exist "build\EtsViewer" (
    echo ERROR: cannot remove build\EtsViewer
    echo        Is EtsViewer.exe still running? Close it and retry.
    goto :err
)
move "build\main.dist" "build\EtsViewer" >nul || goto :err

echo [3/3] Compressing ...
if not exist "%UPX_BIN%" (
    if not exist "tools" mkdir "tools"
    echo   UPX not found, downloading ...
    curl -sL --max-time 180 -o "tools\upx.zip" "%UPX_URL%"
    if exist "tools\upx.zip" (
        powershell -NoProfile -Command "Expand-Archive -Path 'tools\upx.zip' -DestinationPath 'tools' -Force" >nul 2>&1
        del "tools\upx.zip" >nul 2>&1
    )
)

if exist "%UPX_BIN%" (
    set "UPX_FAIL=0"
    REM NOTE: quoted wildcards are NOT expanded by cmd's for loop, so these
    REM patterns must stay unquoted. Relative paths keep it space-safe.
    for %%f in (build\EtsViewer\EtsViewer.exe build\EtsViewer\*.dll build\EtsViewer\*.pyd build\EtsViewer\wx\*.pyd) do (
        call :pack "%%f"
    )
    if not "!UPX_FAIL!"=="0" (
        echo.
        echo ERROR: !UPX_FAIL! file^(s^) could not be compressed.
        echo        Output is larger than expected; check for a running EtsViewer.exe.
        goto :err
    )
) else (
    echo   UPX unavailable, output stays uncompressed ^(~35 MB instead of ~11 MB^).
)

rmdir /s /q "build\main.build" 2>nul
echo.
echo Done. Output folder: build\EtsViewer
exit /b 0

:pack
REM %1 = file to compress. Known-unpackable Microsoft runtime DLLs are skipped
REM because they are built with Control Flow Guard and UPX rejects them.
for %%s in (msvcp140.dll vcruntime140.dll vcruntime140_1.dll) do (
    if /i "%~nx1"=="%%s" exit /b 0
)
"%UPX_BIN%" --best --lzma -q "%~1" >nul 2>&1
if not errorlevel 1 exit /b 0
REM one retry covers a transient antivirus lock
"%UPX_BIN%" --best --lzma -q "%~1" >nul 2>&1
if not errorlevel 1 exit /b 0
echo   ! failed: %~1
set /a UPX_FAIL+=1
exit /b 0

:err
echo.
echo BUILD FAILED.
exit /b 1
