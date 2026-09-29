from pathlib import Path
import pandas as pd,numpy as np,json
ROOT=Path(__file__).resolve().parents[1]
def compare(root=ROOT,tolerance=None):
 from src.workflow import source_digest,requirements,record_stage
 source=source_digest(root);dependencies=requirements('compare',root)
 if tolerance is None:tolerance=json.loads((root/'config/analytics.json').read_text(encoding='utf-8'))['comparison_tolerance']
 a=pd.read_csv(root/'reports/spark_predictions.csv');b=pd.read_csv(root/'reports/python_predictions.csv');d=a.merge(b,on=['date','entity_id'],suffixes=('_spark','_python'),validate='one_to_one',how='outer',indicator=True)
 if not d['_merge'].eq('both').all():raise ValueError('Python and Spark test cases differ; rerun both pipelines on the same source')
 if not np.isfinite(d[['actual_spark','actual_python','spark_prediction','python_prediction']].to_numpy()).all():raise ValueError('Comparison contains non-finite values')
 d=d.drop(columns='_merge')
 if len(d)<100:raise ValueError('At least 100 equivalent unseen cases required')
 if not np.allclose(d.actual_spark,d.actual_python):raise ValueError('Actual values differ: reconcile source processing first')
 d['record_id']=d.entity_id.astype(str)+'/'+d.date;d['actual']=d.actual_spark;d['difference']=d.spark_prediction-d.python_prediction;d['relative_difference']=d.difference.abs()/d.actual.clip(lower=1);d['match']=d.relative_difference<=tolerance;d['spark_error']=(d.spark_prediction-d.actual).abs();d['python_error']=(d.python_prediction-d.actual).abs();d['status']=np.where(d.match,'Within tolerance','Review');d['explanation']=np.where(d.match,'Within declared tolerance','Independent algorithms and regularization produce different fits; inspect both errors against actual.');d.to_csv(root/'reports/comparison.csv',index=False);r={'cases':len(d),'agreement_pct':float(d.match.mean()*100),'disagreements':int((~d.match).sum()),'tolerance':tolerance,'mean_absolute_difference':float(d.difference.abs().mean()),'definition':'Absolute prediction difference / max(actual,1) <= tolerance. Agreement is not accuracy.','confidence':'Regression probabilities not applicable.'};(root/'reports/comparison.json').write_text(json.dumps(r,indent=2), encoding='utf-8');record_stage('compare',source,dependencies,root);print(json.dumps(r,indent=2));return r
if __name__=='__main__':compare()
