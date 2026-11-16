# PowerShell Windows Packaging & Installer Builder
# SRIVANI BOOKING MANAGER v7.1.0

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " SRIVANI BOOKING MANAGER - Commercial Windows Build v7.1.0" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Run Python PyInstaller build
Write-Host "`n[Step 1/3] Building Windows Executable via build_exe.py..." -ForegroundColor Green
python build_exe.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed at PyInstaller stage. Exiting." -ForegroundColor Red
    exit 1
}

# 2. Check for Inno Setup compiler (ISCC.exe)
Write-Host "`n[Step 2/3] Checking for Inno Setup Compiler (ISCC)..." -ForegroundColor Green
$innoPaths = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
)

$isccPath = $null
foreach ($p in $innoPaths) {
    if (Test-Path $p) {
        $isccPath = $p
        break
    }
}

if ($isccPath) {
    Write-Host "   Found Inno Setup at: $isccPath" -ForegroundColor Green
    Write-Host "   Compiling Windows Setup Installer (installer.iss)..." -ForegroundColor Cyan
    & $isccPath installer.iss
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   Installer generated successfully in installer_output\" -ForegroundColor Green
    } else {
        Write-Host "   Inno Setup compilation returned non-zero code." -ForegroundColor Yellow
    }
} else {
    Write-Host "   Inno Setup (ISCC.exe) not found on system path." -ForegroundColor Yellow
}

# 3. Create Portable Windows Zip Archive
Write-Host "`n[Step 3/3] Creating Production Portable Windows Zip Archive..." -ForegroundColor Green
$distFolder = "dist\SrivaniBookingManager"
$zipOutput = "dist\SrivaniBookingManager_v7.1.0_Portable.zip"
if (Test-Path $zipOutput) {
    Remove-Item $zipOutput -Force
}
Compress-Archive -Path "$distFolder\*" -DestinationPath $zipOutput -Force
Write-Host "   Portable zip package created at: $zipOutput" -ForegroundColor Green

Write-Host "`n🎉 Final Windows Release Artifacts Generated Successfully!" -ForegroundColor Cyan
