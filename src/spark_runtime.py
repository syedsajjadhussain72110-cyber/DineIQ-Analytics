"""Configure the active Python 3.11 environment for Spark workers."""
import os, sys, shutil
from pathlib import Path

def configure():
    os.environ.setdefault('SPARK_LOCAL_IP','127.0.0.1')
    os.environ['PYSPARK_PYTHON']=sys.executable
    os.environ['PYSPARK_DRIVER_PYTHON']=sys.executable
    java=Path(os.environ['JAVA_HOME'])/'bin'/('java.exe' if os.name=='nt' else 'java') if os.getenv('JAVA_HOME') else shutil.which('java')
    if not java or not Path(java).exists():
        raise RuntimeError('Java unavailable. Install JDK 17 and set JAVA_HOME; see documentation/WINDOWS_SPARK_SETUP.md.')
