@echo off
REM Activate Python virtual environment
call .venv\Scripts\activate.bat

REM Load azd environment variables
for /f "tokens=*" %%a in ('azd env get-values 2^>nul') do set %%a

echo Environment activated. AZURE_AI_PROJECT_ENDPOINT=%AZURE_AI_PROJECT_ENDPOINT%