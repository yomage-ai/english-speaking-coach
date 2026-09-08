# Agent entry point. No Python, Node.js, Go, administrator rights or API key needed.
$ErrorActionPreference = 'Stop'
$coachRoot = Split-Path $PSScriptRoot -Parent
$coachVersion = (Get-Content (Join-Path $coachRoot 'runtime-version.txt') -Raw).Trim()
if ($coachVersion -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Invalid pinned runtime version' }
$coachArch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
if ($coachArch -eq 'x64') { $coachArch = 'amd64' }
if ($coachArch -notin @('amd64','arm64')) { throw 'Unsupported CPU architecture' }
$coachName = "english-coach_${coachVersion}_windows_${coachArch}"
$coachBinDir = Join-Path $coachRoot 'bin'
$coachBinary = Join-Path $coachBinDir "$coachName.exe"
if (-not (Test-Path $coachBinary)) {
    New-Item -ItemType Directory -Path $coachBinDir -Force | Out-Null
    $coachTemp = Join-Path $coachBinDir ('.download-' + [Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $coachTemp | Out-Null
    try {
        $coachBase = "https://github.com/yomage-ai/english-speaking-coach/releases/download/$coachVersion"
        $coachZip = Join-Path $coachTemp 'archive.zip'
        Invoke-WebRequest -UseBasicParsing -Uri "$coachBase/$coachName.zip" -OutFile $coachZip -TimeoutSec 180
        $coachSums = (Invoke-WebRequest -UseBasicParsing -Uri "$coachBase/SHA256SUMS" -TimeoutSec 60).Content
        if ($coachSums -is [byte[]]) { $coachSums = [System.Text.Encoding]::UTF8.GetString($coachSums) }
        $coachMatches = @($coachSums -split "`n" | Where-Object { $_.Trim() -match ('^[a-f0-9]{64}\s+' + [regex]::Escape("$coachName.zip") + '$') })
        if ($coachMatches.Count -ne 1) { throw 'Missing or duplicate release checksum' }
        $coachExpected = ($coachMatches[0].Trim() -split '\s+')[0]
        if ((Get-FileHash -Algorithm SHA256 $coachZip).Hash.ToLowerInvariant() -ne $coachExpected) { throw 'Release checksum mismatch; nothing installed' }
        Expand-Archive -LiteralPath $coachZip -DestinationPath $coachTemp
        $coachExtracted = Join-Path $coachTemp 'english-coach.exe'
        & $coachExtracted version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Downloaded executable failed its version check' }
        Move-Item -LiteralPath (Join-Path $coachTemp 'LICENSE') -Destination (Join-Path $coachBinDir "$coachName.LICENSE") -Force
        Move-Item -LiteralPath (Join-Path $coachTemp 'THIRD_PARTY_NOTICES.txt') -Destination (Join-Path $coachBinDir "$coachName.NOTICES.txt") -Force
        Move-Item -LiteralPath $coachExtracted -Destination $coachBinary
    } finally { Remove-Item -LiteralPath $coachTemp -Recurse -Force }
}
$env:ENGLISH_COACH_SKILL_ROOT = $coachRoot
& $coachBinary @args
exit $LASTEXITCODE
