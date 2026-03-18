@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  PakLocres.bat — Package localization .locres files into a .pak
REM
REM  Workflow:
REM    1. Read paths from config.ini in the project root.
REM    2. Build a Paklist.txt that maps source .locres files to their
REM       in-pak mount paths.
REM    3. Invoke UnrealPak.exe to create a compressed .pak archive
REM       ready to drop into the game's mod folder.
REM
REM  The resulting pak contains:
REM    - Spanish and French .locres translation files
REM    - DefaultGameplayTags.ini (mod gameplay tag definitions)
REM ═══════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM ── Locate config.ini relative to this script's parent directory ──
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "CONFIG_FILE=%PROJECT_ROOT%\config.ini"

if not exist "%CONFIG_FILE%" (
    echo [ERROR] config.ini not found at: %CONFIG_FILE%
    echo   Create config.ini in the project root with your paths.
    exit /b 1
)

REM ── Parse ProjectRoot and UE4Root from config.ini ──
for /f "usebackq tokens=1,* delims==" %%A in ("%CONFIG_FILE%") do (
    set "KEY=%%A"
    set "VAL=%%B"
    REM Trim leading/trailing spaces
    for /f "tokens=* delims= " %%K in ("!KEY!") do set "KEY=%%K"
    for /f "tokens=* delims= " %%V in ("!VAL!") do set "VAL=%%V"

    if /i "!KEY!"=="ProjectRoot" set "PROJECT_ROOT=!VAL!"
    if /i "!KEY!"=="UE4Root"     set "UE4_ROOT=!VAL!"
    if /i "!KEY!"=="PakFileName" set "PAK_FILENAME=!VAL!"
)

REM ── Fallback defaults ──
if not defined PAK_FILENAME set "PAK_FILENAME=SecretsOfKhazadDum_Localization_P.pak"

REM ── Derived paths ──
set "UNREALPAK=%UE4_ROOT%\Engine\Binaries\Win64\UnrealPak.exe"
set "LOC_DIR=%PROJECT_ROOT%\Localization"
set "MOD_LOC=%LOC_DIR%\ModLocalization"
set "PAKLIST=%MOD_LOC%\Paklist.txt"
set "PAK_OUTPUT=%LOC_DIR%\%PAK_FILENAME%"

REM ── Validate UnrealPak exists ──
if not exist "%UNREALPAK%" (
    echo [ERROR] UnrealPak.exe not found at: %UNREALPAK%
    echo   Check UE4Root in config.ini.
    exit /b 1
)

REM ── Generate Paklist.txt with current paths ──
echo Generating Paklist.txt...
(
    echo "%MOD_LOC%\Moria\Content\Localization\Game\es\Game.locres" "../../../Moria/Content/Localization/Game/es/Game.locres"
    echo "%MOD_LOC%\Moria\Content\Localization\Game\fr\Game.locres" "../../../Moria/Content/Localization/Game/fr/Game.locres"
    echo "%PROJECT_ROOT%\modified-json\Moria\Config\DefaultGameplayTags.ini" "../../../Moria/Config/DefaultGameplayTags.ini"
) > "%PAKLIST%"

REM ── Build the pak ──
echo Packing localization into: %PAK_OUTPUT%
"%UNREALPAK%" "%PAK_OUTPUT%" -create="%PAKLIST%" -compress

if %ERRORLEVEL% neq 0 (
    echo [ERROR] UnrealPak failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo SUCCESS: %PAK_OUTPUT% created.
endlocal
