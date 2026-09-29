$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host "DineIQ Analytics - Windows Setup" -ForegroundColor Cyan
Write-Host "Team Vision AI | Python 3.11 + Java 17 + PySpark 3.5.3" -ForegroundColor DarkCyan

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}
function Need-Winget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'Windows Package Manager (winget) is required for automatic prerequisite installation. Install App Installer from Microsoft Store, then rerun SETUP_DINEIQ.bat.'
  }
}
function Get-Python311 {
  try { $p = (& py -3.11 -c "import sys;print(sys.executable)" 2>$null); if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() } } catch {}
  $candidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:ProgramFiles\Python311\python.exe"
  )
  foreach($p in $candidates){ if(Test-Path $p){ return $p } }
  return $null
}
function Get-JavaHome17 {
  if ($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\java.exe")) {
    $v = & "$env:JAVA_HOME\bin\java.exe" -version 2>&1 | Select-Object -First 1
    if ($v -match '17\.') { return $env:JAVA_HOME }
  }
  $roots = @("$env:ProgramFiles\Eclipse Adoptium", "$env:ProgramFiles\Java")
  foreach($r in $roots){
    if(Test-Path $r){
      $j = Get-ChildItem $r -Directory -ErrorAction SilentlyContinue | Where-Object {$_.Name -match '17'} | Sort-Object Name -Descending | Select-Object -First 1
      if($j -and (Test-Path "$($j.FullName)\bin\java.exe")){ return $j.FullName }
    }
  }
  return $null
}
$drive = (Get-Item $PSScriptRoot).PSDrive
if ($drive.Free -lt 8GB) { throw ('At least 8 GB free space is recommended. Free now: {0:N1} GB' -f ($drive.Free/1GB)) }

$python = Get-Python311
if (-not $python) {
  Need-Winget
  Write-Host 'Python 3.11 not found. Installing automatically...' -ForegroundColor Yellow
  winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
  Refresh-Path
  $python = Get-Python311
  if (-not $python) { throw 'Python 3.11 installation completed but python.exe could not be located. Reopen the terminal and rerun setup.' }
}
Write-Host "Python: $python" -ForegroundColor Green

$javaHome = Get-JavaHome17
if (-not $javaHome) {
  Need-Winget
  Write-Host 'Java 17 not found. Installing Temurin JDK 17 automatically...' -ForegroundColor Yellow
  winget install -e --id EclipseAdoptium.Temurin.17.JDK --silent --accept-package-agreements --accept-source-agreements
  Refresh-Path
  $javaHome = Get-JavaHome17
  if (-not $javaHome) { throw 'Java 17 installation completed but JAVA_HOME could not be resolved. Reopen the terminal and rerun setup.' }
}
$env:JAVA_HOME = $javaHome
[Environment]::SetEnvironmentVariable('JAVA_HOME',$javaHome,'User')
Write-Host "Java 17: $javaHome" -ForegroundColor Green

$hadoopHome = Join-Path $PSScriptRoot 'runtime\hadoop'
$hadoopBin = Join-Path $hadoopHome 'bin'
New-Item -ItemType Directory -Force -Path $hadoopBin | Out-Null
$winutils = Join-Path $hadoopBin 'winutils.exe'
$hadoopDll = Join-Path $hadoopBin 'hadoop.dll'
if (-not (Test-Path $winutils)) {
  Write-Host 'Downloading winutils.exe for Hadoop 3.3.5...' -ForegroundColor Yellow
  Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.5/bin/winutils.exe' -OutFile $winutils
}
if (-not (Test-Path $hadoopDll)) {
  Write-Host 'Downloading hadoop.dll for Hadoop 3.3.5...' -ForegroundColor Yellow
  Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.5/bin/hadoop.dll' -OutFile $hadoopDll
}
if (-not (Test-Path $winutils) -or -not (Test-Path $hadoopDll)) { throw 'Hadoop Windows helper setup failed.' }
$env:HADOOP_HOME = $hadoopHome
$env:Path = "$hadoopBin;$env:Path"
[Environment]::SetEnvironmentVariable('DINEIQ_HADOOP_HOME',$hadoopHome,'User')
Write-Host "Hadoop helper: $hadoopHome" -ForegroundColor Green

$venv = Join-Path $PSScriptRoot '.venv-spark'
$venvPython = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
  Write-Host 'Creating .venv-spark with Python 3.11...' -ForegroundColor Yellow
  & $python -m venv $venv
}
& $venvPython -m pip install --upgrade pip setuptools wheel
& $venvPython -m pip install --no-cache-dir -r requirements.txt

$env:PYSPARK_PYTHON = $venvPython
$env:PYSPARK_DRIVER_PYTHON = $venvPython
$env:SPARK_LOCAL_IP = '127.0.0.1'

Write-Host 'Running runtime checks...' -ForegroundColor Yellow
& $venvPython -c "import sys,pandas,numpy,pyspark,flask; assert sys.version_info[:2]==(3,11); print('Python',sys.version.split()[0]); print('pandas',pandas.__version__); print('numpy',numpy.__version__); print('PySpark',pyspark.__version__); print('Flask',flask.__version__ if hasattr(flask,'__version__') else 'installed')"
& "$javaHome\bin\java.exe" -version
& $winutils ls . 2>$null | Out-Null

Write-Host ''
Write-Host 'SETUP COMPLETE.' -ForegroundColor Green
Write-Host 'Next time, double-click START_DINEIQ.bat.' -ForegroundColor Cyan
