param([string]$Python = "")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
if (-not $Python) {
    if (Test-Path -LiteralPath "$PSScriptRoot\.venv\Scripts\python.exe") { $Python = "$PSScriptRoot\.venv\Scripts\python.exe" }
    elseif (Test-Path -LiteralPath "$PSScriptRoot\..\.venv\Scripts\python.exe") { $Python = "$PSScriptRoot\..\.venv\Scripts\python.exe" }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
& $Python -X utf8 -c "import subprocess,sys; from pathlib import Path; p=subprocess.run([sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-v'],capture_output=True,text=True,encoding='utf-8'); Path('results').mkdir(exist_ok=True); Path('results/test_log.txt').write_text(p.stdout+p.stderr,encoding='utf-8'); print(p.stdout+p.stderr); sys.exit(p.returncode)"
if ($LASTEXITCODE -ne 0) { throw "测试失败" }
