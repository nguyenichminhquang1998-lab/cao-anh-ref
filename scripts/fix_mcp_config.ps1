param([string]$ConfigPath, [string]$ProjectDir)

$ErrorActionPreference = 'Stop'

function Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "`nLOI: $msg" -ForegroundColor Red; throw 'Dung sua config.' }

# Uu tien -ProjectDir neu XQuang truyen thang (vd dan lenh vao PowerShell -
# luc do script chay tu bo nho, khong co file that nen khong tu do duoc).
# Neu khong truyen, thu tu do vi tri that cua chinh script nay ($PSScriptRoot)
# - dung khi script nam san trong thu muc du an (vd update_windows.ps1 goi no
# o buoc cuoi): du sau nay thu muc bi doi ten/di chuyen di dau, chi can chay
# lai la config luon dung.
if (-not $ProjectDir) {
    if (-not $PSScriptRoot) {
        Fail "Khong tu xac dinh duoc thu muc du an (script dang chay truc tiep tu bo nho, khong phai tu file). Hay them '-ProjectDir ''duong dan toi thu muc cao-anh-ref-...''' vao cuoi lenh roi chay lai."
    }
    $ProjectDir = Split-Path -Parent $PSScriptRoot
}
$Python = Join-Path $ProjectDir '.venv\Scripts\python.exe'

Step "1/3 Kiem tra python.exe cua du an..."
if (-not (Test-Path $Python)) {
    Fail "Khong thay $Python. Thu muc .venv co the da bi xoa - can cai lai tu dau, khong chi sua duong dan."
}
Write-Host "Dung: $Python" -ForegroundColor Green

Step "2/3 Tim file cau hinh Claude Desktop..."
if (-not $ConfigPath) {
    $Candidates = @(
        (Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'),
        (Join-Path $env:APPDATA 'Claude\config.json')
    )
    $ConfigPath = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $ConfigPath -or -not (Test-Path $ConfigPath)) {
    Fail "Khong tu tim thay file cau hinh Claude Desktop. Hay mo Claude Desktop > Settings > Developer > Edit config, xem duong dan file hien o dau, roi chay lai script nay voi: -ConfigPath 'duong dan do'."
}
Write-Host "Dung: $ConfigPath" -ForegroundColor Green

Step "3/3 Cap nhat muc cao-anh-ref (giu nguyen cac MCP server khac)..."
$Backup = "$ConfigPath.bak"
Copy-Item -LiteralPath $ConfigPath -Destination $Backup -Force

$Raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
try { $Json = $Raw | ConvertFrom-Json } catch { Fail "File cau hinh khong dung dinh dang JSON. Chi tiet: $_" }

if (-not $Json.mcpServers) {
    $Json | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
}

$Entry = [pscustomobject]@{
    command = $Python
    args    = @('-m', 'cao_anh_ref.server')
}
if ($Json.mcpServers.PSObject.Properties.Name -contains 'cao-anh-ref') {
    $Json.mcpServers.'cao-anh-ref' = $Entry
} else {
    $Json.mcpServers | Add-Member -NotePropertyName 'cao-anh-ref' -NotePropertyValue $Entry
}

$Output = $Json | ConvertTo-Json -Depth 20
[IO.File]::WriteAllText($ConfigPath, $Output, [Text.UTF8Encoding]::new($false))

Write-Host "`nDA SUA XONG." -ForegroundColor Green
Write-Host "Duong dan moi: $Python"
Write-Host "Ban sao file cu (phong khi can khoi phuc): $Backup"
Write-Host "`nHay tat han Claude Desktop qua Task Manager roi mo lai de nap cau hinh moi." -ForegroundColor Yellow
