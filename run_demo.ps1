param([string]$Python = "")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not $Python) {
    if (Test-Path -LiteralPath "$PSScriptRoot\.venv\Scripts\python.exe") { $Python = "$PSScriptRoot\.venv\Scripts\python.exe" }
    elseif (Test-Path -LiteralPath "$PSScriptRoot\..\.venv\Scripts\python.exe") { $Python = "$PSScriptRoot\..\.venv\Scripts\python.exe" }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
& $Python -X utf8 -m rsa_lab demo
if ($LASTEXITCODE -ne 0) { throw "演示运行失败，请查看上面的错误" }
