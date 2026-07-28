param(
  [Parameter(Mandatory=$true)][string]$ModuleName,
  [string]$SourceZip = ""
)

$ErrorActionPreference = "Stop"
$env:INSIGHTEC_RELEASE_MODE = "1"
$env:INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY = "1"
Write-Host "Release Mode enabled: INSIGHTEC_RELEASE_MODE=1"
Write-Host "External tool assembly enabled: INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY=1"
Set-StrictMode -Version Latest

function Write-Section([string]$Title) {
  Write-Host ""
  Write-Host ("=" * 78)
  Write-Host $Title
  Write-Host ("=" * 78)
}

function Find-ModuleDirectory([string[]]$Candidates) {
  $moduleRoot = Join-Path $env:GITHUB_WORKSPACE "Module"
  foreach ($candidate in $Candidates) {
    $exact = Join-Path $moduleRoot $candidate
    if (Test-Path -LiteralPath $exact -PathType Container) {
      return (Get-Item -LiteralPath $exact).FullName
    }
  }
  $dirs = @(Get-ChildItem -LiteralPath $moduleRoot -Directory -ErrorAction SilentlyContinue)
  foreach ($candidate in $Candidates) {
    $match = $dirs | Where-Object { $_.Name -ieq $candidate } | Select-Object -First 1
    if ($match) { return $match.FullName }
  }
  throw "Module folder was not found. Tried: $($Candidates -join ', ')"
}

function Resolve-SourceZip([string]$ModuleDir, [string]$RequestedName, [string]$WorkName) {
  $files = @(Get-ChildItem -LiteralPath $ModuleDir -Recurse -File)
  $normal = @($files | Where-Object { $_.Name -match '(?i)_SOURCE\.zip$' } | Sort-Object LastWriteTimeUtc -Descending)
  $parts = @($files | Where-Object { $_.Name -match '(?i)\.zip\.part\d{3,}$' })
  $groups = @{}
  foreach ($part in $parts) {
    if ($part.Name -match '^(?<base>.+\.zip)\.part(?<number>\d{3,})$') {
      $base = $Matches.base
      if (-not $groups.ContainsKey($base)) { $groups[$base] = @() }
      $groups[$base] += $part
    }
  }

  $requested = $RequestedName.Trim()
  if ($requested) {
    $requested = [IO.Path]::GetFileName($requested) -replace '(?i)\.part\d+$',''
    if ($requested -notmatch '(?i)\.zip$') { $requested += '.zip' }
  }

  $selectedNormal = $null
  $selectedBase = $null
  $selectedParts = @()
  if ($requested) {
    $baseMatch = @($groups.Keys | Where-Object { $_ -ieq $requested } | Select-Object -First 1)
    if ($baseMatch.Count -gt 0) {
      $selectedBase = [string]$baseMatch[0]
      $selectedParts = @($groups[$selectedBase])
    } else {
      $selectedNormal = $normal | Where-Object { $_.Name -ieq $requested } | Select-Object -First 1
    }
  } else {
    $sets = @(foreach ($base in $groups.Keys) {
      $setParts = @($groups[$base])
      [pscustomobject]@{ Base=$base; Parts=$setParts; Latest=($setParts | Measure-Object LastWriteTimeUtc -Maximum).Maximum }
    })
    $newestSplit = $sets | Sort-Object Latest -Descending | Select-Object -First 1
    $newestNormal = $normal | Select-Object -First 1
    if ($newestSplit -and (-not $newestNormal -or $newestSplit.Latest -ge $newestNormal.LastWriteTimeUtc)) {
      $selectedBase = $newestSplit.Base
      $selectedParts = @($newestSplit.Parts)
    } else {
      $selectedNormal = $newestNormal
    }
  }

  if (-not $selectedNormal -and $selectedParts.Count -eq 0) {
    Write-Host ("Files under {0}:" -f $ModuleDir)
    $files | ForEach-Object { Write-Host (" - " + $_.FullName) }
    throw "No SOURCE ZIP was found in $ModuleDir"
  }

  $workDir = Join-Path $env:RUNNER_TEMP ("rc6_2_zip_" + $WorkName)
  Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $workDir -Force | Out-Null

  if ($selectedParts.Count -gt 0) {
    $selectedParts = @($selectedParts | Sort-Object { [int]([regex]::Match($_.Name,'\.part(\d+)$').Groups[1].Value) })
    $expected = 1
    foreach ($part in $selectedParts) {
      $number = [int]([regex]::Match($part.Name,'\.part(\d+)$').Groups[1].Value)
      if ($number -ne $expected) { throw "Missing split part. Expected part$('{0:D3}' -f $expected), found $($part.Name)" }
      if ($part.Length -le 0) { throw "Empty split part: $($part.FullName)" }
      if ($part.Length -ge 25MB) { throw "Split part is not below 25 MB: $($part.FullName)" }
      $expected++
    }
    $zipPath = Join-Path $workDir $selectedBase
    $outStream = [IO.File]::Open($zipPath,[IO.FileMode]::Create)
    try {
      foreach ($part in $selectedParts) {
        Write-Host ("Appending " + $part.Name)
        $inStream = [IO.File]::OpenRead($part.FullName)
        try { $inStream.CopyTo($outStream) } finally { $inStream.Dispose() }
      }
    } finally { $outStream.Dispose() }
  } else {
    $zipPath = Join-Path $workDir $selectedNormal.Name
    Copy-Item -LiteralPath $selectedNormal.FullName -Destination $zipPath -Force
  }

  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
  try {
    if ($archive.Entries.Count -eq 0) { throw "SOURCE ZIP is empty: $zipPath" }
  } finally { $archive.Dispose() }
  Write-Host ("SOURCE: " + $zipPath)
  Write-Host ("SHA256: " + (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash)
  return $zipPath
}

function Expand-Source([string]$ZipPath, [string]$WorkName) {
  $extractDir = Join-Path $env:RUNNER_TEMP ("rc6_2_extract_" + $WorkName)
  Remove-Item -LiteralPath $extractDir -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
  Expand-Archive -LiteralPath $ZipPath -DestinationPath $extractDir -Force
  $dirs = @(Get-ChildItem -LiteralPath $extractDir -Directory)
  $files = @(Get-ChildItem -LiteralPath $extractDir -File)
  if ($dirs.Count -eq 1 -and $files.Count -eq 0) { return $dirs[0].FullName }
  return $extractDir
}

function Find-Root([string]$ExtractRoot, [string[]]$Markers) {
  foreach ($marker in $Markers) {
    $direct = Join-Path $ExtractRoot $marker
    if (Test-Path -LiteralPath $direct -PathType Leaf) { return $ExtractRoot }
  }
  foreach ($marker in $Markers) {
    $found = Get-ChildItem -LiteralPath $ExtractRoot -Recurse -File -Filter ([IO.Path]::GetFileName($marker)) |
      Where-Object { $_.FullName -notmatch '(?i)[\\/](tests?|test_data|examples?|backup|old)[\\/]' } |
      Sort-Object { $_.FullName.Length } | Select-Object -First 1
    if ($found) { return $found.Directory.FullName }
  }
  throw "Application root could not be found. Markers: $($Markers -join ', ')"
}

function Assert-ReleaseModeSupport([string]$Root, [string]$ToolId) {
  $cfg = Join-Path $Root 'release_mode.json'
  if (-not (Test-Path -LiteralPath $cfg -PathType Leaf)) {
    throw "Release Mode contract missing for ${ToolId}: $cfg"
  }
  $data = Get-Content -LiteralPath $cfg -Raw | ConvertFrom-Json
  if (-not $data.release_mode_supported) { throw "Release Mode is not supported by ${ToolId}." }
  if ($data.environment_variable -ne 'INSIGHTEC_RELEASE_MODE') { throw "Unexpected Release Mode variable for ${ToolId}." }
  if ($data.release_value -ne '1') { throw "Unexpected Release Mode value for ${ToolId}." }
  if ($data.guide_tour_enabled_in_release -ne $false) { throw "Guide/Tour is enabled in Release Mode for ${ToolId}." }
  Write-Host ("[PASS] Release Mode contract: " + $ToolId)
}

function Install-Requirements([string]$Root) {
  Push-Location $Root
  try {
    if (Test-Path -LiteralPath "requirements-build.txt") { python -m pip install -r requirements-build.txt }
    if (Test-Path -LiteralPath "requirements.txt") { python -m pip install -r requirements.txt }
  } finally { Pop-Location }
}

function Select-BuildFile([string]$Root, [string[]]$PreferredBats, [string[]]$EntryCandidates) {
  foreach ($bat in $PreferredBats) {
    $path = Join-Path $Root $bat
    if (Test-Path -LiteralPath $path -PathType Leaf) {
      return [pscustomobject]@{ Mode='bat'; File=$path; Entry='' }
    }
  }
  $spec = Get-ChildItem -LiteralPath $Root -File -Filter '*.spec' | Sort-Object Name | Select-Object -First 1
  if ($spec) { return [pscustomobject]@{ Mode='spec'; File=$spec.FullName; Entry='' } }
  foreach ($entry in $EntryCandidates) {
    $path = Join-Path $Root $entry
    if (Test-Path -LiteralPath $path -PathType Leaf) {
      return [pscustomobject]@{ Mode='pyinstaller'; File=''; Entry=$path }
    }
  }
  throw "No supported build file or entry point was found in $Root"
}

function Invoke-Build([string]$Root, [object]$Plan) {
  Push-Location $Root
  try {
    $distPath = Join-Path $Root 'dist'
    Remove-Item -LiteralPath $distPath -Recurse -Force -ErrorAction SilentlyContinue

    # Do not delete a build folder that contains the selected build script.
    $buildPath = Join-Path $Root 'build'
    $planPath = if ($Plan.File) { [IO.Path]::GetFullPath($Plan.File) } else { '' }
    $buildFull = [IO.Path]::GetFullPath($buildPath).TrimEnd('\') + '\'
    $planIsInsideBuild = $planPath -and $planPath.StartsWith($buildFull,[StringComparison]::OrdinalIgnoreCase)
    if (-not $planIsInsideBuild) {
      Remove-Item -LiteralPath $buildPath -Recurse -Force -ErrorAction SilentlyContinue
    } else {
      Write-Host 'Preserving build folder because it contains the selected BAT.'
    }

    if ($Plan.Mode -eq 'bat') {
      if (-not (Test-Path -LiteralPath $Plan.File -PathType Leaf)) {
        throw "Selected build BAT disappeared before execution: $($Plan.File)"
      }
      Write-Host ("Running BAT: " + $Plan.File)
      $command = 'call "' + $Plan.File + '"'
      & cmd.exe /d /s /c $command
      if ($LASTEXITCODE -ne 0) { throw "Build BAT failed with exit code $LASTEXITCODE" }
    } elseif ($Plan.Mode -eq 'spec') {
      python -m PyInstaller --noconfirm --clean $Plan.File
      if ($LASTEXITCODE -ne 0) { throw "PyInstaller SPEC build failed with exit code $LASTEXITCODE" }
    } else {
      $name = [IO.Path]::GetFileNameWithoutExtension($Plan.Entry)
      python -m PyInstaller --noconfirm --clean --windowed --name $name $Plan.Entry
      if ($LASTEXITCODE -ne 0) { throw "PyInstaller entry build failed with exit code $LASTEXITCODE" }
    }
  } finally { Pop-Location }
}

function Find-Package([string]$Root, [string[]]$ExeHints) {
  $searchRoots = @()
  foreach ($candidate in @('dist','output','release')) {
    $path = Join-Path $Root $candidate
    if (Test-Path -LiteralPath $path -PathType Container) { $searchRoots += (Get-Item -LiteralPath $path) }
  }
  if ($searchRoots.Count -eq 0) {
    throw "No recognized build output folder was created under $Root (expected dist, output, or release)."
  }

  foreach ($hint in $ExeHints) {
    foreach ($searchRoot in $searchRoots) {
      $found = Get-ChildItem -LiteralPath $searchRoot.FullName -Recurse -File -Filter $hint -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notmatch '(?i)(debug|console|uninstall|updater|crash)' } |
        Sort-Object Length -Descending | Select-Object -First 1
      if ($found) { return [pscustomobject]@{ Exe=$found; Package=$found.Directory } }
    }
  }

  $fallbacks = @()
  foreach ($searchRoot in $searchRoots) {
    $fallbacks += @(Get-ChildItem -LiteralPath $searchRoot.FullName -Recurse -File -Filter '*.exe' -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -notmatch '(?i)(debug|console|uninstall|updater|crash)' })
  }
  $fallback = $fallbacks | Sort-Object Length -Descending | Select-Object -First 1
  if (-not $fallback) { throw "No executable was produced under the recognized output folders in $Root" }
  return [pscustomobject]@{ Exe=$fallback; Package=$fallback.Directory }
}

function Copy-ToolPackage([object]$Package, [string]$Destination) {
  Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $Destination -Force | Out-Null
  Copy-Item -Path (Join-Path $Package.Package.FullName '*') -Destination $Destination -Recurse -Force
  $copiedExe = Join-Path $Destination $Package.Exe.Name
  if (-not (Test-Path -LiteralPath $copiedExe -PathType Leaf)) {
    throw "Tool executable was not copied: $copiedExe"
  }
  return $copiedExe
}

$selectedModule = $ModuleName
$requestedZip = $SourceZip

Write-Section "BUILD SELECTED MODULE: $selectedModule"
$selectedDir = Find-ModuleDirectory @($selectedModule)
$selectedZip = Resolve-SourceZip $selectedDir $requestedZip 'selected'
$selectedExtract = Expand-Source $selectedZip 'selected'

if ($selectedModule -ine 'InSightec_Service_hub') {
  $root = Find-Root $selectedExtract @('01_BUILD_EXE.bat','main.py','launcher.py','VIMeasureAnalyzer.py')
  Assert-ReleaseModeSupport $root $selectedModule
  Install-Requirements $root
  $plan = Select-BuildFile $root @('01_BUILD_EXE.bat','01_BUILD_EXE_NUITKA.bat','02_BUILD_EXE_NUITKA.bat','build_exe.bat') @('main.py','launcher.py','VIMeasureAnalyzer.py')
  Invoke-Build $root $plan
  $package = Find-Package $root @('*.exe')
  $finalDir = $package.Package.FullName
  $startupExe = $package.Exe.FullName
} else {
  $hubRoot = Find-Root $selectedExtract @('InSightecServiceHub.py','01_BUILD_EXE.bat')
  $hubBuilder = Join-Path $hubRoot 'Build_Hub_EXE.py'
  if (-not (Test-Path -LiteralPath $hubBuilder -PathType Leaf)) { throw 'Build_Hub_EXE.py is missing from Hub source.' }
  $hubBuilderText = Get-Content -LiteralPath $hubBuilder -Raw
  if ($hubBuilderText -notmatch 'INSIGHTEC_EXTERNAL_TOOL_ASSEMBLY') { throw 'Hub source does not support external tool assembly. Upload Commit 0018 parts.' }
  Write-Host '[PASS] Hub external-tool assembly contract detected.'
  Assert-ReleaseModeSupport $hubRoot 'Hub'
  Install-Requirements $hubRoot
  $hubPlan = Select-BuildFile $hubRoot @('01_BUILD_EXE.bat') @('InSightecServiceHub.py')
  Invoke-Build $hubRoot $hubPlan
  $hubPackage = Find-Package $hubRoot @('InSightecServiceHub.exe','InSightec_APAC_Service_Hub.exe')
  $finalDir = $hubPackage.Package.FullName
  $startupExe = $hubPackage.Exe.FullName
  $toolsRoot = Join-Path $finalDir 'tools'
  New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null

  $toolDefinitions = @(
    [pscustomobject]@{ Id='DOanalysis'; Modules=@('DO_Analysis'); Markers=@('build_exe.bat','DO_Analysis_Qt.py','main.py'); Bats=@('build_exe.bat','01_BUILD_EXE.bat','build_pyinstaller_fallback.bat'); Entries=@('DO_Analysis_Qt.py','main.py'); Exes=@('*DO*Analysis*.exe','*Water*System*.exe') },
    [pscustomobject]@{ Id='TrackerSNR'; Modules=@('trackerSNR'); Markers=@('build_TrackerSNR_CLEAN_EXE_NUITKA.bat','tracker_snr_app.py','main.py'); Bats=@('build_TrackerSNR_CLEAN_EXE_NUITKA.bat','00_BUILD_EXE_RECOMMENDED_PYINSTALLER.bat','00_BUILD_EXE_ONEDIR_FALLBACK.bat'); Entries=@('tracker_snr_app.py','main.py'); Exes=@('*Tracker*SNR*.exe') },
    [pscustomobject]@{ Id='LogExplorer'; Modules=@('Log_explorer'); Markers=@('LogMergeTool_NoExcel_Main.py','01_BUILD_EXE_NUITKA.bat'); Bats=@('01_BUILD_EXE_NUITKA.bat'); Entries=@('LogMergeTool_NoExcel_Main.py'); Exes=@('*LogMerge*.exe','*Log*Explorer*.exe') },
    [pscustomobject]@{ Id='SonicationAnalysis'; Modules=@('Soni'); Markers=@('main.py','01_BUILD_EXE_NUITKA.bat'); Bats=@('build\01_BUILD_EXE.bat','01_BUILD_EXE_NUITKA.bat'); Entries=@('main.py'); Exes=@('*Sonication*Replay*.exe','*Soni*.exe') },
    [pscustomobject]@{ Id='FUSImageExplore'; Modules=@('FFT'); Markers=@('launcher.py','02_BUILD_EXE_NUITKA.bat'); Bats=@('02_BUILD_EXE_NUITKA.bat','02_BUILD_FAST_STANDALONE.bat'); Entries=@('launcher.py'); Exes=@('MR_Image_Explorer_RC1.exe','*Image*Explorer*.exe') },
    [pscustomobject]@{ Id='VIMeasure'; Modules=@('VIMeasure'); Markers=@('VIMeasureAnalyzer.py','01_BUILD_EXE_NUITKA.bat'); Bats=@('01_BUILD_EXE_NUITKA.bat'); Entries=@('VIMeasureAnalyzer.py'); Exes=@('*VIMeasure*.exe') }
  )

  $status = @()
  foreach ($tool in $toolDefinitions) {
    Write-Section ("BUILD TOOL FROM REPOSITORY MODULE: " + $tool.Id)
    $moduleDir = Find-ModuleDirectory $tool.Modules
    $zip = Resolve-SourceZip $moduleDir '' $tool.Id
    $extract = Expand-Source $zip $tool.Id
    $root = Find-Root $extract $tool.Markers
    Assert-ReleaseModeSupport $root $tool.Id
    Install-Requirements $root
    $plan = Select-BuildFile $root $tool.Bats $tool.Entries
    Write-Host ('Selected build mode: ' + $plan.Mode)
    if ($plan.File) { Write-Host ('Selected build file: ' + $plan.File) }
    if ($tool.Id -eq 'LogExplorer' -and $plan.File -match '(?i)GITHUB|test') { throw 'Unsafe Log Explorer test build BAT was selected.' }
    Invoke-Build $root $plan
    $package = Find-Package $root $tool.Exes
    $destination = Join-Path $toolsRoot $tool.Id
    $copiedExe = Copy-ToolPackage $package $destination
    Write-Host ("[PASS] " + $tool.Id + " => " + $copiedExe)
    $status += [pscustomobject]@{
      tool_id = $tool.Id
      module_directory = $moduleDir
      source_sha256 = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
      executable = [IO.Path]::GetRelativePath($finalDir,$copiedExe)
      ready = $true
    }
  }

  [pscustomobject]@{
    generated_utc = [DateTime]::UtcNow.ToString('o')
    source = 'repository_modules'
    all_ready = ($status.Count -eq 6 -and @($status | Where-Object { -not $_.ready }).Count -eq 0)
    tools = $status
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $finalDir 'tool_build_status.json') -Encoding UTF8

  if (-not (Test-Path -LiteralPath (Join-Path $finalDir 'tool_build_status.json'))) {
    throw 'tool_build_status.json was not created.'
  }
}

$launcher = Join-Path $finalDir 'RUN_APPLICATION.bat'
$relativeExe = [IO.Path]::GetRelativePath($finalDir,$startupExe)
@('@echo off','cd /d %~dp0',('start "" "' + $relativeExe + '"')) | Set-Content -LiteralPath $launcher -Encoding ASCII

Write-Host ("FINAL DIRECTORY: " + $finalDir)
Write-Host ("STARTUP EXE   : " + $startupExe)
"package_dir=$finalDir" >> $env:GITHUB_OUTPUT
"startup_exe=$startupExe" >> $env:GITHUB_OUTPUT

