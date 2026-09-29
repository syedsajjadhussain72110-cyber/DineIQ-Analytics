from pathlib import Path
import time,json,argparse
import pandas as pd
from python_pipeline.quality import load,integrate
from python_pipeline import analytics as a,models
ROOT=Path(__file__).resolve().parents[1]
def run(raw=ROOT/'raw_data',root=ROOT,horizon=30):
 from src.workflow import source_digest,record_stage
 for folder in ['reports','processed_data','models']:(root/folder).mkdir(parents=True,exist_ok=True)
 source=source_digest(root)
 start=time.perf_counter();print('Cleaning independent Python source',flush=True);t,q=load(raw,root/'processed_data');(root/'reports/python_quality.json').write_text(json.dumps(q,indent=2), encoding='utf-8');f=integrate(t)
 if f.empty or f.date.nunique()<90:raise ValueError('At least 90 days of valid data required for models')
 f.to_parquet(root/'processed_data/facts.parquet',index=False);print('Analytical features and models',flush=True);m=a.menu(f,t);local=a.menu(f,t,['item_id','location_id']);c=a.customers(f);b=a.baskets(f);pr=a.pricing(f);p=a.promotions(f,t);an=a.anomalies(f,t);models.train(f,root);risk=a.risk(t,root);fc=models.forecast(f,horizon);rec=a.recommendations(m,b,c,p,fc,an)
 loc=f.groupby(['location_id','location']).agg(revenue=('revenue','sum'),contribution=('contribution','sum'),orders=('order_id','nunique'),customers=('customer_id','nunique'),quantity=('quantity','sum')).reset_index();loc['average_order_value']=loc.revenue/loc.orders;loc=loc.merge(t['ratings'].groupby('location_id').rating.mean(),on='location_id',how='left').merge(t['wastage'].groupby('location_id').quantity.sum().rename('waste'),on='location_id',how='left');repeat=f.groupby(['location_id','customer_id']).order_id.nunique().gt(1).groupby(level=0).mean().rename('repeat_rate');loc=loc.merge(repeat,on='location_id',how='left')
 ch=f.groupby('channel').agg(revenue=('revenue','sum'),contribution=('contribution','sum'),orders=('order_id','nunique'),quantity=('quantity','sum'),discount=('discount','mean')).reset_index();ch['average_order_value']=ch.revenue/ch.orders;ch['basket_size']=ch.quantity/ch.orders;w=t['wastage'].copy();w['waste_cost']=w.quantity*w.unit_cost
 reports={'menu':m,'location_menu':local,'customers':c,'baskets':b,'pricing':pr,'promotions':p,'anomalies':an,'waste_risk':risk,'forecast':fc,'recommendations':rec,'locations':loc,'channels':ch,'wastage':w,'peaks':f.groupby(['location_id','channel','weekday','hour']).agg(orders=('order_id','nunique'),revenue=('revenue','sum')).reset_index(),'daily':f.groupby('date').agg(revenue=('revenue','sum'),contribution=('contribution','sum'),quantity=('quantity','sum'),orders=('order_id','nunique')).reset_index(),'ratings':t['ratings']}
 for name,d in reports.items():d.to_csv(root/f'reports/{name}.csv',index=False)
 summary={'revenue':float(f.revenue.sum()),'contribution':float(f.contribution.sum()),'orders':int(f.order_id.nunique()),'customers':int(f.customer_id.nunique()),'average_order_value':float(f.revenue.sum()/f.order_id.nunique()),'repeat_customers':int((c.frequency>1).sum()),'waste':float(w.quantity.sum()),'waste_cost':float(w.waste_cost.sum()),'after_waste':float(f.contribution.sum()-w.waste_cost.sum()),'anomalies':len(an),'critical_recommendations':int((rec.priority=='Critical').sum()),'fact_rows':len(f),'start_date':str(f.date.min().date()),'end_date':str(f.date.max().date()),'processing_seconds':time.perf_counter()-start,'synthetic':True,'currency':'PKR'};(root/'reports/summary.json').write_text(json.dumps(summary,indent=2), encoding='utf-8');print(json.dumps(summary,indent=2),flush=True)
 record_stage('python',source,{},root)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,default=ROOT/'raw_data');p.add_argument('--horizon',type=int,default=30);args=p.parse_args();run(args.raw,horizon=args.horizon)