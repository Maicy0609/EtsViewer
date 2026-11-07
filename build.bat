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
  --product-name=EtsViewer --file-version=1.0.0 --product-version=1.0.0 ^
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
    REM NOTE: quoted wildcards are NOT expanded by cmd's for loop, so these
    REM patterns must stay unquoted. Relative paths keep it space-safe.
    for %%f in (build\EtsViewer\EtsViewer.exe build\EtsViewer\*.dll build\EtsViewer\*.pyd build\EtsViewer\wx\*.pyd) do (
        "%UPX_BIN%" --best --lzma -q "%%f" >nul 2>&1
    )
) else (
    echo   UPX unavailable, output stays uncompressed ^(~35 MB instead of ~11 MB^).
)

rmdir /s /q "build\main.build" 2>nul
echo.
echo Done. Output folder: build\EtsViewer
exit /b 0

:err
echo.
echo BUILD FAILED.
exit /b 1
