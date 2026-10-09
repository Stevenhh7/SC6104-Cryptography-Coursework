param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
& $Python -c "import Crypto, cryptography, matplotlib"
$hasPackages = ($LASTEXITCODE -eq 0)
if ($hasPackages) { & $Python -m venv --system-site-packages .venv }
else { & $Python -m venv .venv }
if ($LASTEXITCODE -ne 0) { throw "创建 Python 环境失败" }
if (Test-Path -LiteralPath "$PSScriptRoot\vendor\wheels") {
    & ".\.venv\Scripts\python.exe" -m pip install --no-index --find-links vendor/wheels -r requirements.lock.txt
} else {
    & ".\.venv\Scripts\python.exe" -m pip install --index-url https://pypi.org/simple -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw "依赖安装失败。附带离线包适用于 Windows 64 位 Python 3.10，其他版本请在线安装 requirements.txt。" }
& ".\.venv\Scripts\python.exe" -c "import Crypto, cryptography, matplotlib, gmpy2; print('Dependencies ready')"
if ($LASTEXITCODE -ne 0) { throw "依赖检查失败" }
