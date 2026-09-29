import subprocess,sys,os,threading
from src.database import ROOT,connect,sync
LOCK=threading.Lock()

def start(kind,horizon=30,dbpath=None):
    commands={'python':[sys.executable,'-m','python_pipeline.run','--horizon',str(horizon)],'spark':[sys.executable,'-m','spark_jobs.pipeline'],'compare':[sys.executable,'-m','src.compare'],'generate':[sys.executable,'-m','src.generate_report'],'regenerate':[sys.executable,'-m','data_generator.generate']}
    if kind not in commands:raise ValueError('Unknown named job')
    if not LOCK.acquire(blocking=False):raise ValueError('A job, prediction or source update is running')
    try:
        with connect(dbpath) as c:jid=c.execute('INSERT INTO jobs(kind,status,details) VALUES(?,?,?)',(kind,'running','Starting backend process')).lastrowid
    except Exception:LOCK.release();raise
    def work():
        log=ROOT/f'reports/job_{jid}_{kind}.log';status='failed';details='Backend process did not complete'
        try:
            from src.inference import close_spark
            close_spark()
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run(commands[kind],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','PYSPARK_PYTHON':sys.executable,'PYSPARK_DRIVER_PYTHON':sys.executable,'SPARK_LOCAL_IP':'127.0.0.1','OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2'},timeout=7200)
            if result.returncode:raise RuntimeError(f'{log.name}: exit {result.returncode}. '+log.read_text(encoding='utf-8',errors='replace')[-2500:])
            if kind!='regenerate':
                from src.workflow import verify_stage
                verify_stage(kind)
            sync(dbpath);status='completed';details=f'{log.name}: exit 0; backend outputs verified'
        except Exception as e:details=str(e)
        finally:
            try:
                with connect(dbpath) as c:c.execute('UPDATE jobs SET status=?,details=?,finished_at=CURRENT_TIMESTAMP WHERE id=?',(status,details,jid))
            finally:LOCK.release()
    try:threading.Thread(target=work,daemon=True).start()
    except Exception:LOCK.release();raise
    return jid
