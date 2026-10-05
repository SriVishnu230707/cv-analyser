param([string]$AndroidSdk = '', [string]$JavaHome = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (!$AndroidSdk) { $AndroidSdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA 'Android\Sdk' } }
if (!(Test-Path -LiteralPath (Join-Path $AndroidSdk 'platforms\android-36'))) { throw 'Install Android SDK platform 36 through Android Studio SDK Manager first.' }
if (!$JavaHome) {
    foreach ($candidate in @($env:JAVA_HOME, 'C:\Program Files\Android\Android Studio\jbr', 'C:\Program Files\Android\Android Studio1\jbr')) {
        if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate 'bin\java.exe'))) {
            $version = Get-Content -LiteralPath (Join-Path $candidate 'release') -Raw
            if ($version -match 'JAVA_VERSION="21\.') { $JavaHome = $candidate; break }
        }
    }
}
if (!$JavaHome -or !(Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe'))) { throw 'Java 21 is required. Pass -JavaHome with your JDK 21 or Android Studio jbr directory.' }
if ((Get-Content -LiteralPath (Join-Path $JavaHome 'release') -Raw) -notmatch 'JAVA_VERSION="21\.') { throw 'The selected Java runtime must be JDK 21.' }
$oldJavaHome = $env:JAVA_HOME
$oldAndroidHome = $env:ANDROID_HOME
Push-Location (Join-Path $projectRoot 'frontend')
try {
    $env:JAVA_HOME = $JavaHome
    $env:ANDROID_HOME = $AndroidSdk
    & npm.cmd ci
    if ($LASTEXITCODE) { throw 'Frontend dependency installation failed.' }
    & npm.cmd run android:sync
    if ($LASTEXITCODE) { throw 'Frontend build or Android synchronization failed.' }
    & .\android\gradlew.bat -p android assembleDebug --console=plain
    if ($LASTEXITCODE) { throw 'Android APK compilation failed.' }
    $destination = Join-Path $projectRoot 'output\android'
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Copy-Item -LiteralPath 'android\app\build\outputs\apk\debug\app-debug.apk' -Destination (Join-Path $destination 'cv-analyser-debug.apk')
    Write-Output "APK ready: $(Join-Path $destination 'cv-analyser-debug.apk')"
} finally {
    Pop-Location
    $env:JAVA_HOME = $oldJavaHome
    $env:ANDROID_HOME = $oldAndroidHome
}
