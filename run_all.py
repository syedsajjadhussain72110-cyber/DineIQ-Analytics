import argparse,subprocess,sys,os
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');p.add_argument('--lines',type=int,default=1050000);p.add_argument('--horizon',type=int,default=30);args=p.parse_args();commands=[]
if args.generate:commands.append([sys.executable,'-m','data_generator.generate','--lines',str(args.lines)])
commands += [[sys.executable,'-m','python_pipeline.run','--horizon',str(args.horizon)],[sys.executable,'-m','spark_jobs.pipeline'],[sys.executable,'-m','src.compare'],[sys.executable,'-m','src.generate_report'],[sys.executable,'-m','src.database']]
for cmd in commands:
 print('Running',' '.join(cmd),flush=True);subprocess.run(cmd,cwd=root,check=True,env={**os.environ,'SPARK_LOCAL_IP':'127.0.0.1','OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2'})
