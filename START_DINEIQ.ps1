$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv-spark\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'DineIQ is not set up yet. Run SETUP_DINEIQ.bat first.' }

$javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME','User')
if (-not $javaHome) { $javaHome = $env:JAVA_HOME }
if (-not $javaHome -or -not (Test-Path "$javaHome\bin\java.exe")) { throw 'Java 17 not found. Run SETUP_DINEIQ.bat again.' }
$hadoopHome = [Environment]::GetEnvironmentVariable('DINEIQ_HADOOP_HOME','User')
if (-not $hadoopHome) { $hadoopHome = Join-Path $PSScriptRoot 'runtime\hadoop' }
if (-not (Test-Path "$hadoopHome\bin\winutils.exe")) { throw 'Windows Hadoop helper not found. Run SETUP_DINEIQ.bat again.' }

$env:JAVA_HOME = $javaHome
$env:HADOOP_HOME = $hadoopHome
$env:Path = "$hadoopHome\bin;$javaHome\bin;$env:Path"
$env:PYSPARK_PYTHON = $python
$env:PYSPARK_DRIVER_PYTHON = $python
$env:SPARK_LOCAL_IP = '127.0.0.1'
$env:PYTHONUTF8 = '1'

Write-Host 'Starting DineIQ Analytics...' -ForegroundColor Cyan
$proc = Start-Process -FilePath $python -ArgumentList @('-m','src.app') -WorkingDirectory $PSScriptRoot -PassThru
$ready = $false
for($i=0;$i -lt 30;$i++){
  Start-Sleep -Seconds 1
  if($proc.HasExited){ throw "DineIQ server exited with code $($proc.ExitCode). Open PowerShell here and run .\.venv-spark\Scripts\python.exe -m src.app for the full error." }
  try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5000/login' -TimeoutSec 2; if($r.StatusCode -eq 200){$ready=$true;break} } catch {}
}
if(-not $ready){ throw 'DineIQ did not become ready within 30 seconds.' }
Start-Process 'http://127.0.0.1:5000'
Write-Host "DineIQ is running at http://127.0.0.1:5000 (PID $($proc.Id))" -ForegroundColor Green
Write-Host 'Close the server process from Task Manager or run STOP_DINEIQ.bat.'
