import sys,subprocess,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if sys.version_info[:2]!=(3,11):raise SystemExit('Use Python 3.11; current: '+sys.version)
print('Python',sys.version.split()[0],flush=True)
from src.spark_runtime import configure
configure()
java=str(Path(os.environ['JAVA_HOME'])/'bin'/('java.exe' if os.name=='nt' else 'java')) if os.getenv('JAVA_HOME') else 'java'
subprocess.run([java,'-version'],check=True)
import setuptools,pyspark
from pyspark.ml.regression import LinearRegressionModel
print('PySpark',pyspark.__version__,'ML import OK; setuptools',setuptools.__version__)
print('Driver and worker Python:',sys.executable)
print('Preflight passed. Run tests or Processing center for full execution.')
