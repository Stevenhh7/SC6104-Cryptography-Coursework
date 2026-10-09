param([string]$Python = "", [string]$Sizes = "100,300,1000,3000", [int]$Repeats = 3, [double]$Timeout = 45)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not $Python) {
    if (Test-Path -LiteralPath "$PSScriptRoot\.venv\Scripts\python.exe") { $Python = "$PSScriptRoot\.venv\Scripts\python.exe" }
    elseif (Test-Path -LiteralPath "$PSScriptRoot\..\.venv\Scripts\python.exe") { $Python = "$PSScriptRoot\..\.venv\Scripts\python.exe" }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
& $Python -X utf8 -m rsa_lab prepare-bench --sizes $Sizes
if ($LASTEXITCODE -ne 0) { throw "数据准备失败" }
& $Python -X utf8 -m rsa_lab benchmark --sizes $Sizes --repeats $Repeats --timeout $Timeout
if ($LASTEXITCODE -ne 0) { throw "性能实验失败" }
& $Python -X utf8 -m rsa_lab plot
if ($LASTEXITCODE -ne 0) { throw "绘图失败" }
