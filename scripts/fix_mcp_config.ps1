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
$ConfigFilename = 'claude_desktop_config.json'
if (-not $ConfigPath) {
    # Vi tri thong thuong.
    $Candidates = @(
        (Join-Path $env:APPDATA "Claude\$ConfigFilename"),
        (Join-Path $env:LOCALAPPDATA "Claude\$ConfigFilename"),
        (Join-Path $env:APPDATA "AnthropicClaude\$ConfigFilename"),
        (Join-Path $env:LOCALAPPDATA "AnthropicClaude\$ConfigFilename")
    )
    $ConfigPath = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $ConfigPath) {
    # Ban cai tu Microsoft Store bi "ao hoa" AppData vao %LOCALAPPDATA%\Packages\<ten-goi>\...
    # Chi do vao cac goi co ten lien quan Claude/Anthropic, khong quet toan bo Packages (rat nhieu goi khac, se cham).
    $PackagesDir = Join-Path $env:LOCALAPPDATA 'Packages'
    if (Test-Path $PackagesDir) {
        $ClaudePackages = Get-ChildItem -Path $PackagesDir -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like '*Claude*' -or $_.Name -like '*Anthropic*' }
        foreach ($pkg in $ClaudePackages) {
            $found = Get-ChildItem -Path $pkg.FullName -Filter $ConfigFilename -Recurse -Depth 6 -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { $ConfigPath = $found.FullName; break }
        }
    }
}
if (-not $ConfigPath) {
    # Tim rong o 2 goc quen thuoc, gioi han do sau de khong quet lan sang cac thu muc lon khong lien quan.
    $ConfigPath = @($env:APPDATA, $env:LOCALAPPDATA) | Where-Object { $_ } | ForEach-Object {
        Get-ChildItem -Path $_ -Filter $ConfigFilename -Recurse -Depth 3 -ErrorAction SilentlyContinue
    } | Select-Object -First 1 -ExpandProperty FullName
}

if (-not $ConfigPath -or -not (Test-Path $ConfigPath)) {
    Write-Host "`nKhong tu tim thay file cau hinh. Cac thu muc co ten chua 'claude' tim duoc:" -ForegroundColor Yellow
    $Found = @($env:APPDATA, $env:LOCALAPPDATA) | Where-Object { $_ } | ForEach-Object {
        Get-ChildItem -Path $_ -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*claude*' }
    }
    if ($Found) { $Found | ForEach-Object { Write-Host " - $($_.FullName)" } }
    else { Write-Host " (khong thay thu muc nao)" }
    Fail "Hay mo Claude Desktop > Settings > Developer > Edit config, xem duong dan file hien o dau (hoac dung danh sach thu muc in o tren), roi chay lai script nay voi: -ConfigPath 'duong dan do'."
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
