@echo off
setlocal enabledelayedexpansion

REM Check if a file is dragged and dropped onto the script
if "%~1"=="" (
    echo No file dragged onto the script. Exiting.
    exit /b 1
)

set "hf_token_file=hf"

REM Read the access token from the file
set /p hf_token=<"%hf_token_file%"

REM Get the filename from the dragged file
set "filename=%~1"

REM Get the directory of the batch script
set "scriptdir=%~dp0"

REM Change the current directory to the script directory
cd /d "!scriptdir!"
echo "!scriptdir!out"   !filename!

whisperx "!filename!" --model large-v2 --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --batch_size 6 --diarize --hf_token !hf_token! --output_format vtt --language en --print_progress True --output_dir out
py split.py "!scriptdir!out" "!filename!"
pause