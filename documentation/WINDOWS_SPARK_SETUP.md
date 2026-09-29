# DineIQ Windows Setup - Final Verified Runtime

## Recommended method

Run `SETUP_DINEIQ.bat` from the project root. The script automates the environment that was successfully verified on Windows.

### Runtime
- Python 3.11 in `.venv-spark`
- Java / OpenJDK 17
- PySpark 3.5.3
- pandas 2.2.3
- numpy 2.3.5
- Windows Hadoop helper (`winutils.exe` and `hadoop.dll`)
- `SPARK_LOCAL_IP=127.0.0.1`

### Start
After setup, double-click `START_DINEIQ.bat`. It configures all process environment variables and opens `http://127.0.0.1:5000` when Flask is ready.

### Manual PowerShell launch
```powershell
$env:PYSPARK_PYTHON = (Resolve-Path ".\.venv-spark\Scripts\python.exe").Path
$env:PYSPARK_DRIVER_PYTHON = $env:PYSPARK_PYTHON
$env:HADOOP_HOME = (Resolve-Path ".\runtime\hadoop").Path
$env:PATH = "$env:HADOOP_HOME\bin;$env:PATH"
$env:SPARK_LOCAL_IP = "127.0.0.1"
.\.venv-spark\Scripts\python.exe -m src.app
```

### Final functional check
1. Login.
2. Live Prediction -> Run Python Model.
3. Live Prediction -> Run Spark Model.
4. Live Prediction -> Run Both Models.
5. Processing Center -> Python -> Spark -> Compare -> Generate.
6. Confirm each job is `Completed` only after backend output exists.
7. Download generated PDF, JSON, and comparison CSV.

### Notes
`SETUP_DINEIQ.ps1` can automatically install Python 3.11 and Temurin JDK 17 through `winget` when missing. It downloads the Windows Hadoop helper into the project-local `runtime\hadoop` folder so the user does not need to configure `C:\hadoop` manually. Internet access is required only when prerequisites or Python packages are not already available.
