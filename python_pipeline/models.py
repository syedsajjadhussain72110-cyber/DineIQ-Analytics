from pathlib import Path
import pandas as pd,numpy as np,json,joblib
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
FEATURES=['entity_id','day_index','dow_sin','dow_cos','year_sin','year_cos','lag1','lag7','mean7','mean28']
def series(f,key):
 wide=f.groupby(['date',key]).quantity.sum().unstack(fill_value=0).reindex(pd.date_range(f.date.min(),f.date.max()),fill_value=0)
 return wide.rename_axis('date').stack().rename('actual').reset_index().rename(columns={key:'entity_id'})
def features(x):
 x=x.sort_values(['entity_id','date']).copy();g=x.groupby('entity_id').actual;x['lag1']=g.shift(1);x['lag7']=g.shift(7)
 for n in [7,28]:x[f'mean{n}']=g.transform(lambda s:s.shift(1).rolling(n).mean())
 x['day_index']=(x.date-pd.Timestamp('2025-01-01')).dt.days;x['dow_sin']=np.sin(x.date.dt.dayofweek*2*np.pi/7);x['dow_cos']=np.cos(x.date.dt.dayofweek*2*np.pi/7);x['year_sin']=np.sin(x.date.dt.dayofyear*2*np.pi/365);x['year_cos']=np.cos(x.date.dt.dayofyear*2*np.pi/365);return x.dropna()
def metrics(y,p):
 y=np.asarray(y);p=np.maximum(0,p);mask=y!=0;return {'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))),'r2':float(r2_score(y,p)),'mape':float(np.mean(np.abs((y[mask]-p[mask])/y[mask]))*100) if mask.any() else None}
def train(f,root):
 x=features(series(f,'location_id'));dates=sorted(x.date.unique());a=dates[int(len(dates)*.7)];b=dates[int(len(dates)*.85)];splits={'train':x[x.date<a],'validation':x[(x.date>=a)&(x.date<b)],'test':x[x.date>=b]};candidates={'Ridge':Ridge(alpha=20),'RandomForest':RandomForestRegressor(n_estimators=40,max_depth=12,min_samples_leaf=4,n_jobs=2,random_state=42),'GradientBoosting':GradientBoostingRegressor(n_estimators=80,max_depth=3,random_state=42)};scores={}
 for name,m in candidates.items():
  m.fit(splits['train'][FEATURES],splits['train'].actual);scores[name]={k:metrics(d.actual,m.predict(d[FEATURES])) for k,d in splits.items()};scores[name]['parameters']=m.get_params()
 best=min(scores,key=lambda n:scores[n]['validation']['rmse']);m=candidates[best];test=splits['test'];pred=test[['date','entity_id','actual']].copy();pred['python_prediction']=np.maximum(0,m.predict(test[FEATURES]));pred['model_version']='python-demand-v1';pred.to_csv(root/'reports/python_predictions.csv',index=False);joblib.dump(m,root/'models/python_demand.joblib');base=metrics(test.actual,test.lag7)
 report={'selected':best,'models':scores,'baseline':base,'beats_baseline':scores[best]['test']['rmse']<base['rmse'],'features':FEATURES,'validation_start':str(a),'test_start':str(b),'evaluation':'Chronological split; rolling one-day-ahead predictions. Validation-only model selection.'};(root/'reports/python_models.json').write_text(json.dumps(report,indent=2), encoding='utf-8')
 for k,d in splits.items():d.to_parquet(root/f'processed_data/{k}.parquet',index=False)
 return report

def forecast(f,horizon=30):
 rows=[]
 for scope,key in [('item','item_id'),('category','category_id'),('location','location_id')]:
  raw=series(f,key);x=features(raw);last=raw.date.max();cols=FEATURES[1:]
  for entity,d in x.groupby('entity_id'):
   tr=d.iloc[:-30];te=d.iloc[-30:]
   if len(tr)<30:continue
   m=Ridge(alpha=10).fit(tr[cols],tr.actual);rmse=metrics(te.actual,m.predict(te[cols]))['rmse'];base=metrics(te.actual,te.lag7)['rmse'];selected='Ridge' if rmse<base else 'Seasonal baseline';m.fit(d[cols],d.actual);hist=raw[raw.entity_id==entity].actual.to_list();err=min(rmse,base)
   for h in range(1,horizon+1):
    date=last+pd.Timedelta(days=h);v=[(date-pd.Timestamp('2025-01-01')).days,np.sin(date.dayofweek*2*np.pi/7),np.cos(date.dayofweek*2*np.pi/7),np.sin(date.dayofyear*2*np.pi/365),np.cos(date.dayofyear*2*np.pi/365),hist[-1],hist[-7],np.mean(hist[-7:]),np.mean(hist[-28:])];y=max(0,float(m.predict(pd.DataFrame([v],columns=cols))[0])) if selected=='Ridge' else hist[-7];hist.append(y);rows.append({'scope':scope,'entity_id':int(entity),'date':str(date.date()),'forecast':y,'lower_estimate':max(0,y-1.96*err*np.sqrt(h)),'upper_estimate':y+1.96*err*np.sqrt(h),'model':selected,'holdout_rmse':err,'baseline_rmse':base,'interval_note':'Heuristic, uncalibrated band'})
 return pd.DataFrame(rows)