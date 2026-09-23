param([string]$ProjectDir)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Branch = 'claude/loving-babbage-1g7ghe'
$ZipUrl = "https://github.com/nguyenichminhquang1998-lab/cao-anh-ref/archive/refs/heads/$Branch.zip"

function Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
# throw thay vi exit: khi chay bang lenh dan vao PowerShell, exit se dong luon cua so truoc khi kip doc loi.
function Fail($msg) { Write-Host "`nLOI: $msg" -ForegroundColor Red; throw 'Dung cap nhat.' }

if (-not $ProjectDir) { $ProjectDir = Split-Path -Parent $PSScriptRoot }
$Python = Join-Path $ProjectDir '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    Fail "Khong thay $Python. Kiem tra lai duong dan thu muc du an: $ProjectDir"
}

Step "1/5 Tai ban code moi tu GitHub..."
$Tmp = Join-Path $env:TEMP 'cao-anh-ref-update'
if (Test-Path $Tmp) { Remove-Item $Tmp -Recurse -Force }
New-Item -ItemType Directory -Path $Tmp | Out-Null
$Zip = Join-Path $Tmp 'code.zip'
try { Invoke-WebRequest -Uri $ZipUrl -OutFile $Zip -UseBasicParsing }
catch { Fail "Khong tai duoc file tu GitHub (kiem tra mang internet). Chi tiet: $_" }

Step "2/5 Giai nen va kiem tra..."
Expand-Archive -Path $Zip -DestinationPath $Tmp -Force
$Extracted = Get-ChildItem $Tmp -Directory | Select-Object -First 1
if (-not $Extracted -or -not (Test-Path (Join-Path $Extracted.FullName 'src\cao_anh_ref\server.py'))) {
    Fail "File tai ve khong dung cau truc code. Khong thay doi gi tren may."
}

Step "3/5 Tat Claude Desktop va server cu..."
$ClaudeExe = (Get-Process -Name claude -ErrorAction SilentlyContinue | Where-Object Path | Select-Object -First 1).Path
# Co tien trinh "claude" chay quyen he thong (Access denied) - khong can tat, bo qua.
Get-Process -Name claude -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# python.exe cua venv chi la launcher; tien trinh that nam o thu muc Python goc, nen loc theo dong lenh.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*cao_anh_ref*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
if (Get-Process -Name claude -ErrorAction SilentlyContinue | Where-Object Path) {
    Write-Host "Claude Desktop chua tat duoc tu dong. Hay tat Claude bang tay (chuot phai icon Claude o goc phai taskbar -> Quit, hoac Task Manager), roi quay lai day nhan Enter." -ForegroundColor Yellow
    Read-Host | Out-Null
}

Step "4/5 Chep code moi de len code cu (giu nguyen .venv va .env)..."
robocopy $Extracted.FullName $ProjectDir /E /XD .venv /XF .env /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Fail "Chep file that bai (robocopy ma loi $LASTEXITCODE)." }

Step "5/5 Cap nhat thu vien (neu co thu vien moi)..."
& $Python -m pip install -e $ProjectDir --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Fail "Cai thu vien that bai. Chup man hinh cua so nay gui lai." }

Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`nCAP NHAT XONG." -ForegroundColor Green
if ($ClaudeExe) {
    try {
        Start-Process $ClaudeExe
        Write-Host "Da mo lai Claude Desktop." -ForegroundColor Green
    } catch {
        Write-Host "Hay tu mo lai Claude Desktop bang tay." -ForegroundColor Yellow
    }
} else {
    Write-Host "Claude Desktop chua chay luc cap nhat - hay tu mo lai." -ForegroundColor Yellow
}
