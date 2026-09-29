"""Successful output fingerprints reject stale or mixed processing results."""
import hashlib,json
from datetime import datetime,timezone
from src.database import ROOT
OUTPUTS={
 'python':['reports/python_predictions.csv','reports/python_models.json','reports/summary.json','models/python_demand.joblib'],
 'spark':['reports/spark_predictions.csv','reports/spark_models.json','reports/spark_quality.json','models/spark_demand'],
 'compare':['reports/comparison.csv','reports/comparison.json'],
 'generate':['reports/Generated_Result_Report.pdf','reports/generated_result.json']}

def digest(paths,root=ROOT):
    h=hashlib.sha256()
    for name in sorted(paths):
        p=root/name
        files=sorted(x for x in p.rglob('*') if x.is_file()) if p.is_dir() else [p]
        if not files:raise ValueError(f'Missing output: {name}')
        for f in files:
            h.update(f.relative_to(root).as_posix().encode())
            with f.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def source_digest(root=ROOT):
    from src.schema import SCHEMAS
    return digest([f'raw_data/{n}.csv' if (root/f'raw_data/{n}.csv').exists() else f'raw_data/{n}' for n in SCHEMAS],root)

def state(root=ROOT):
    p=root/'reports/workflow.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

def verify_stage(kind,root=ROOT):
    record=state(root).get(kind)
    if not record or record.get('source')!=source_digest(root):raise ValueError(f'Run {kind.title()} on the current source first')
    if record['outputs']!=digest(OUTPUTS[kind],root):raise ValueError(f'{kind.title()} outputs changed; rerun this stage')
    for dependency,fingerprint in record.get('dependencies',{}).items():
        previous=verify_stage(dependency,root)
        if previous['outputs']!=fingerprint:raise ValueError(f'{kind.title()} is stale; rerun after {dependency.title()}')
    return record

def requirements(kind,root=ROOT):
    dependencies={'python':[],'spark':[],'compare':['python','spark'],'generate':['compare']}[kind]
    return {d:verify_stage(d,root)['outputs'] for d in dependencies}

def record_stage(kind,source,dependencies,root=ROOT):
    if source!=source_digest(root):raise ValueError('Source changed during processing; rerun this stage')
    data=state(root);data[kind]={'completed_at':datetime.now(timezone.utc).isoformat(),'source':source,'outputs':digest(OUTPUTS[kind],root),'dependencies':dependencies}
    pending=root/'reports/workflow.json.tmp';pending.write_text(json.dumps(data,indent=2),encoding='utf-8');pending.replace(root/'reports/workflow.json')
