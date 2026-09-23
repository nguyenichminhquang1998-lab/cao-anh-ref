param([string]$ProjectDir)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Branch = 'claude/loving-babbage-1g7ghe'
$ZipUrl = "https://github.com/nguyenichminhquang1998-lab/cao-anh-ref/archive/refs/heads/$Branch.zip"

function Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
# throw thay vi exit: khi chay bang lenh dan vao PowerShell, exit se dong luon cua so truoc khi kip doc loi.
function Fail($msg) { Write-Host "`nLOI: $msg" -ForegroundColor Red; throw 'Dung cap nhat.' }
function Remove-Dir($path) {
    if ([IO.Directory]::Exists($path)) { [IO.Directory]::Delete($path, $true) }
}

if (-not $ProjectDir) { $ProjectDir = Split-Path -Parent $PSScriptRoot }
$Python = Join-Path $ProjectDir '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    Fail "Khong thay $Python. Kiem tra lai duong dan thu muc du an: $ProjectDir"
}

Step "1/5 Tai ban code moi tu GitHub..."
# Thu muc tam nam trong du an, khong dung %TEMP%: ten user co dau cach nen %TEMP% bi rut gon
# kieu C:\Users\MYPC~1, va Remove-Item cua PowerShell 5.1 loi voi duong dan rut gon do.
$Tmp = Join-Path $ProjectDir '.update-tmp'
try {
    Remove-Dir $Tmp
    [IO.Directory]::CreateDirectory($Tmp) | Out-Null
} catch { Fail "Khong tao duoc thu muc tam $Tmp. Chi tiet: $_" }
$Zip = Join-Path $Tmp 'code.zip'
try { Invoke-WebRequest -Uri $ZipUrl -OutFile $Zip -UseBasicParsing }
catch { Fail "Khong tai duoc file tu GitHub (kiem tra mang internet). Chi tiet: $_" }

Step "2/5 Giai nen va kiem tra..."
try { Expand-Archive -Path $Zip -DestinationPath $Tmp -Force }
catch { Fail "Giai nen that bai. Chi tiet: $_" }
$Extracted = Get-ChildItem -LiteralPath $Tmp -Directory | Select-Object -First 1
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
    Write-Host "Claude Desktop co the chua tat het. Neu cua so Claude van con: chuot phai icon Claude o goc phai taskbar -> Quit. Xong (hoac neu Claude da tat roi) thi nhan Enter de chay tiep." -ForegroundColor Yellow
    Read-Host | Out-Null
}

Step "4/5 Chep code moi de len code cu (giu nguyen .venv va .env)..."
robocopy $Extracted.FullName $ProjectDir /E /XD .venv .update-tmp /XF .env /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Fail "Chep file that bai (robocopy ma loi $LASTEXITCODE)." }

Step "5/5 Cap nhat thu vien (neu co thu vien moi)..."
# pip in canh bao ra stderr; khong de canh bao do bi coi la loi chet.
$ErrorActionPreference = 'Continue'
& $Python -m pip install -e $ProjectDir --quiet --disable-pip-version-check
$PipExit = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($PipExit -ne 0) { Fail "Code moi da chep xong nhung cai thu vien that bai. Chup man hinh cua so nay gui lai." }

try { Remove-Dir $Tmp } catch { }

Write-Host "`nCAP NHAT XONG." -ForegroundColor Green
if ($ClaudeExe) {
    try {
        Start-Process $ClaudeExe
        Write-Host "Da mo lai Claude Desktop." -ForegroundColor Green
    } catch {
        Write-Host "Hay tu mo lai Claude Desktop bang tay." -ForegroundColor Yellow
    }
} else {
    Write-Host "Hay tu mo lai Claude Desktop bang tay." -ForegroundColor Yellow
}
