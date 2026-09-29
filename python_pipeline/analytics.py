from pathlib import Path
import json,joblib
from collections import Counter
from itertools import combinations
import pandas as pd,numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest,RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,confusion_matrix
ROOT=Path(__file__).resolve().parents[1]
def classify(d):
 cfg=json.loads((ROOT/'config/analytics.json').read_text(encoding='utf-8'));d=d.copy();demand=d.quantity.quantile(cfg['demand_quantile']);margin=d.margin_pct.quantile(cfg['margin_quantile']);repeat=d.repeat_rate.median();good=(d.margin_pct>=margin)&(d.rating>=cfg['minimum_rating'])&(d.waste_pct<=cfg['max_waste_pct']);d['performance_class']='Low Performer';d.loc[(d.quantity<demand)&good,'performance_class']='Hidden Opportunity';d.loc[(d.quantity>=demand)&(d.contribution>0)&(d.waste_pct<=cfg['max_waste_pct'])&(d.rating>=3),'performance_class']='Volume Driver';d.loc[(d.quantity>=demand)&good&(d.repeat_rate>=repeat)&(d.promo_dependency<.65),'performance_class']='Profit Driver';d['history_status']=np.where(d.active_days<30,'Insufficient history','Established');d['slow_moving']=(d.quantity<demand*.5)&((d.repeat_rate<repeat)|(d.contribution<0)|(d.sales_trend<0));return d

def menu(f,t,keys=['item_id']):
 d=f.groupby(keys).agg(quantity=('quantity','sum'),revenue=('revenue','sum'),cost=('cost','sum'),contribution=('contribution','sum'),orders=('order_id','nunique'),active_days=('date','nunique'),first_sale=('date','min'),last_sale=('date','max'),promo_dependency=('promotion_id',lambda x:(x>0).mean()),discount=('discount','mean'),weekend_ratio=('weekend','mean')).reset_index();repeat=f.groupby(keys+['customer_id']).order_id.nunique().gt(1).groupby(level=list(range(len(keys)))).mean().rename('repeat_rate')
 for other in [t['ratings'].groupby(keys).rating.mean(),t['wastage'].groupby(keys).quantity.sum().rename('waste'),t['inventory'].groupby(keys).prepared.sum(),repeat]:d=d.merge(other,on=keys,how='left')
 now=f.date.max();recent=f[f.date>now-pd.Timedelta(days=30)].groupby(keys).quantity.sum();old=f[(f.date<=now-pd.Timedelta(days=30))&(f.date>now-pd.Timedelta(days=60))].groupby(keys).quantity.sum();d=d.merge(((recent-old)/old.replace(0,np.nan)).rename('sales_trend'),on=keys,how='left')
 ratings=t['ratings'];a=ratings[ratings.date>now-pd.Timedelta(days=30)].groupby(keys).rating.mean();b=ratings[(ratings.date<=now-pd.Timedelta(days=30))&(ratings.date>now-pd.Timedelta(days=60))].groupby(keys).rating.mean();d=d.merge((a-b).rename('rating_trend'),on=keys,how='left');d['margin_pct']=d.contribution/d.revenue.replace(0,np.nan)*100;d['waste_pct']=d.waste/d.prepared.replace(0,np.nan)*100
 universe=t['menu'][['item_id']]
 if 'location_id' in keys:universe=universe.merge(t['locations'][['location_id']],how='cross')
 d=universe.merge(d,on=keys,how='left')
 for c in d.select_dtypes('number'):d[c]=d[c].fillna(0)
 return classify(d).merge(t['menu'][['item_id','name','category_id']],on='item_id')

def customers(f):
 o=f.groupby(['customer_id','order_id']).agg(date=('date','first'),value=('revenue','sum'),promotion=('promotion_id','max'),channel=('channel','first'),hour=('hour','first')).reset_index();d=o.groupby('customer_id').agg(first=('date','min'),last=('date','max'),frequency=('order_id','nunique'),monetary=('value','sum'),average_order_value=('value','mean'),promotion_sensitivity=('promotion',lambda x:(x>0).mean()),channel_preference=('channel',lambda x:x.mode().iloc[0]),time_preference=('hour',lambda x:x.mode().iloc[0])).reset_index();now=f.date.max();d['recency']=(now-d['last']).dt.days;d['tenure']=(now-d['first']).dt.days;d['visit_frequency']=d.frequency/(d.tenure/30+1)
 favorite=f.groupby(['customer_id','category']).quantity.sum().reset_index().sort_values('quantity',ascending=False).drop_duplicates('customer_id').set_index('customer_id').category;d['favorite_category']=d.customer_id.map(favorite)
 for prefix,lo,hi in [('recent',0,60),('prior',60,120)]:
  x=f[(f.date>now-pd.Timedelta(days=hi))&(f.date<=now-pd.Timedelta(days=lo))].groupby('customer_id').agg(orders=('order_id','nunique'),value=('revenue','sum'),categories=('category_id','nunique'));x.columns=[prefix+'_'+c for c in x];d=d.merge(x,on='customer_id',how='left')
 d=d.fillna(0);d['churn_risk']=(d.recency>90)|((d.recent_orders<d.prior_orders*.5)&(d.recent_value<d.prior_value*.5)&(d.prior_orders>=2));cols=['recency','frequency','monetary','average_order_value','promotion_sensitivity','visit_frequency'];z=StandardScaler().fit_transform(np.log1p(d[cols]));d['cluster']=KMeans(n_clusters=min(6,len(d)),random_state=42,n_init=10).fit_predict(z);d['segment']='Occasional Customers';d.loc[d.frequency>=d.frequency.quantile(.75),'segment']='Frequent Customers';d.loc[(d.monetary>=d.monetary.quantile(.8))&(d.frequency>=3),'segment']='High-Value Loyal Customers';d.loc[d.promotion_sensitivity>.65,'segment']='Promotion-Driven Customers';d.loc[d.churn_risk,'segment']='At-Risk Customers';d.loc[d.tenure<30,'segment']='New Customers';return d

def baskets(f,min_support=.002):
 orders=f.groupby('order_id').item_id.unique();n=len(orders);single=Counter();pairs=Counter()
 for b in orders:vals=sorted(set(map(int,b)));single.update(vals);pairs.update(combinations(vals,2))
 rows=[]
 for (a,b),count in pairs.items():
  if count/n>=min_support:
   for x,y in [(a,b),(b,a)]:rows.append({'antecedent':x,'consequent':y,'support':count/n,'confidence':count/single[x],'lift':count*n/(single[x]*single[y]),'orders_together':count})
 return pd.DataFrame(rows,columns=['antecedent','consequent','support','confidence','lift','orders_together']).sort_values('lift',ascending=False)

def pricing(f):
 daily=f.groupby(['item_id','date']).agg(quantity=('quantity','sum'),price=('unit_price','mean'),discount=('discount','mean'),revenue=('revenue','sum'),contribution=('contribution','sum')).reset_index();rows=[]
 for item,d in daily.groupby('item_id'):
  e=None;label='Insufficient history or price variation'
  if len(d)>=60 and d.price.nunique()>1:
   X=pd.DataFrame({'log_price':np.log(d.price.clip(lower=.01)),'trend':(d.date-d.date.min()).dt.days,'weekend':(d.date.dt.dayofweek>=5).astype(int),'season_sin':np.sin(d.date.dt.dayofyear*2*np.pi/365),'season_cos':np.cos(d.date.dt.dayofyear*2*np.pi/365),'discount':d.discount});m=Ridge(alpha=.1).fit(X,np.log1p(d.quantity));e=float(m.coef_[0]);label='Highly Price Sensitive' if e<-1 else 'Moderately Price Sensitive' if e<-.3 else 'Low Price Sensitivity'
  rows.append({'item_id':item,'elasticity':e,'sensitivity':label,'days':len(d),'revenue':d.revenue.sum(),'contribution':d.contribution.sum(),'caveat':'Observational association controlling time and discount; not causal.'})
 return pd.DataFrame(rows)

def promotions(f,t):
 o=f.groupby('order_id').agg(date=('date','first'),customer_id=('customer_id','first'),promotion_id=('promotion_id','first'),revenue=('revenue','sum'),contribution=('contribution','sum')).reset_index();first=o.groupby('customer_id').date.min();rows=[]
 for p in t['promotions'].itertuples():
  start=p.start_date;end=p.end_date;days=(end-start).days+1;during=o[o.date.between(start,end)&(o.promotion_id==p.promotion_id)];before=o[(o.date<start)&(o.date>=start-pd.Timedelta(days=days))];post=o[(o.date>end)&(o.date<=end+pd.Timedelta(days=30))];ids=set(during.customer_id);margin=during.contribution.sum()/max(1,during.revenue.sum());base_margin=before.contribution.sum()/max(1,before.revenue.sum());repeat=len(ids&set(post.customer_id))/max(1,len(ids));w=t['wastage'];waste=w[w.date.between(start,end)].quantity.sum();old_waste=w[w.date.between(start-pd.Timedelta(days=days),start-pd.Timedelta(days=1))].quantity.sum();traps=[]
  if len(during)>len(before) and during.contribution.sum()<before.contribution.sum():traps.append('Volume rises while contribution falls')
  if margin<base_margin*.65:traps.append('Margin compression')
  if waste>old_waste*1.2:traps.append('Wastage increased')
  if repeat<.1:traps.append('Weak post-promotion retention')
  # A substitution signal, explicitly not proof of cannibalization.
  bf=f[(f.date<start)&(f.date>=start-pd.Timedelta(days=days))].groupby('item_id').agg(q=('quantity','sum'),c=('contribution','sum'));du=f[f.date.between(start,end)].groupby('item_id').quantity.sum();lost=((du.reindex(bf.index).fillna(0)<bf.q*.7)&(bf.c>bf.c.median())).sum()
  if lost>=3:traps.append('Possible displacement of profitable items')
  rows.append({'promotion_id':p.promotion_id,'name':p.name,'orders':len(during),'revenue':during.revenue.sum(),'contribution':during.contribution.sum(),'margin_pct':100*margin,'average_order_value':during.revenue.sum()/max(1,len(during)),'customers':len(ids),'new_customers':sum(start<=first[c]<=end for c in ids),'post_repeat_rate':repeat,'baseline_orders':len(before),'baseline_contribution':before.contribution.sum(),'waste':waste,'baseline_waste':old_waste,'trap':'; '.join(traps) or 'No rule triggered','caveat':'Campaign participants vs prior equal-length window; confounded observational comparison.'})
 return pd.DataFrame(rows)

def anomalies(f,t):
 rows=[];daily=f.groupby(['location_id','date']).revenue.sum().reset_index()
 for loc,d in daily.groupby('location_id'):
  d=d.sort_values('date');mean=d.revenue.shift().rolling(28,min_periods=7).mean();sd=d.revenue.shift().rolling(28,min_periods=7).std().replace(0,np.nan);z=(d.revenue-mean)/sd
  for i in d.index[z.abs()>3]:rows.append({'type':'Sales spike' if z[i]>0 else 'Sales drop','entity':str(loc),'date':str(d.loc[i,'date'].date()),'value':d.loc[i,'revenue'],'evidence':f'Prior 28-day z score {z[i]:.2f}'})
 o=f.groupby('order_id').agg(value=('revenue','sum'),quantity=('quantity','sum'),discount=('discount','max'));pred=IsolationForest(n_estimators=60,contamination=.003,random_state=42,n_jobs=2).fit_predict(o)
 for i in o.index[pred==-1]:rows.append({'type':'Unusual order','entity':str(i),'date':'','value':o.loc[i,'value'],'evidence':'Isolation Forest over order value, quantity and discount. Investigate, not fraud proof.'})
 r=t['ratings'].copy();r['date']=r.date.dt.normalize();rd=r.groupby(['item_id','date']).rating.agg(['mean','count','nunique']).reset_index()
 for item,d in rd.groupby('item_id'):
  d=d.sort_values('date');avg=d['mean'].shift().rolling(14,min_periods=7).mean();n=d['count'].shift().rolling(14,min_periods=7).mean();mask=((d['mean']-avg).abs()>1)|((d['nunique']==1)&(d['count']>=10))|(d['count']>n*4)
  for x in d[mask].itertuples():rows.append({'type':'Rating anomaly','entity':str(item),'date':str(x.date.date()),'value':x.mean,'evidence':f'{x.count} ratings; sharp change, repeated ratings or volume spike'})
 return pd.DataFrame(rows,columns=['type','entity','date','value','evidence'])

def risk(t,root):
 w=t['wastage'].groupby(['date','item_id','location_id']).quantity.sum().rename('waste').reset_index();d=t['inventory'].merge(w,on=['date','item_id','location_id'],how='left').fillna({'waste':0}).sort_values(['item_id','location_id','date']);g=d.groupby(['item_id','location_id']);d['lag_waste']=g.waste.shift();d['lag_demand']=g.consumed.shift();d['dow']=d.date.dt.dayofweek;d['risk']=(d.waste/d.prepared.replace(0,np.nan)>.25).astype(int);d=d.dropna();cols=['item_id','location_id','prepared','lag_waste','lag_demand','dow'];dates=sorted(d.date.unique());a=dates[int(len(dates)*.65)];b=dates[int(len(dates)*.8)];tr=d[d.date<a];va=d[(d.date>=a)&(d.date<b)];te=d[d.date>=b];m=RandomForestClassifier(n_estimators=35,max_depth=9,min_samples_leaf=10,n_jobs=2,random_state=42).fit(tr[cols],tr.risk);scores={}
 for name,data in [('train',tr),('validation',va),('test',te)]:
  pred=m.predict(data[cols]);p,r,f1,_=precision_recall_fscore_support(data.risk,pred,average='macro',zero_division=0);scores[name]={'accuracy':float(accuracy_score(data.risk,pred)),'precision_macro':float(p),'recall_macro':float(r),'f1_macro':float(f1),'confusion_matrix':confusion_matrix(data.risk,pred).tolist(),'rows':len(data)}
 (root/'reports/waste_model.json').write_text(json.dumps({'scores':scores,'features':cols,'version':'waste-risk-v1','test_start':str(b),'note':'Synthetic-data validation; next observation risk using known preparation and prior observations.'},indent=2), encoding='utf-8');joblib.dump(m,root/'models/waste_risk.joblib');last=d.groupby(['item_id','location_id']).tail(1).copy();last['lag_waste']=last.waste;last['lag_demand']=last.consumed;last['dow']=(last.dow+1)%7;last['risk_prediction']=m.predict(last[cols]);last['risk_probability']=m.predict_proba(last[cols])[:,list(m.classes_).index(1)] if 1 in m.classes_ else 0;return last[['item_id','location_id','prepared','lag_demand','risk_prediction','risk_probability']]

def recommendations(m,b,c,p,fc,a):
 rows=[]
 def add(action,entity,priority,evidence):rows.append({'action':action,'entity':str(entity),'priority':priority,'evidence':evidence})
 for x in m.itertuples():
  why=f'Margin {x.margin_pct:.1f}%; rating {x.rating:.2f}; waste {x.waste_pct:.1f}%; repeat {x.repeat_rate:.1%}; units {x.quantity:.0f}'
  if x.contribution<0:add('Review recipe cost and net price',x.item_id,'Critical',why)
  elif x.waste_pct>25:add('Reduce preparation and review stock',x.item_id,'High',why)
  elif x.performance_class=='Hidden Opportunity':add('Promote high-margin item',x.item_id,'Medium',why)
  elif x.slow_moving:add('Review or redesign slow-moving item',x.item_id,'Medium',why)
 for x in b[b.lift>1.2].head(8).itertuples():add('Test combo and cross-sell',f'{x.antecedent}+{x.consequent}','Medium',f'Support {x.support:.2%}; confidence {x.confidence:.2%}; lift {x.lift:.2f}')
 for x in p[p.trap!='No rule triggered'].itertuples():add('Review promotion economics',x.name,'High',f'{x.trap}; margin {x.margin_pct:.1f}%; repeat {x.post_repeat_rate:.1%}')
 add('Test targeted win-back campaign','At-Risk Customers','Medium',f'{int(c.churn_risk.sum())} customers show stale or declining activity')
 for x in fc[fc.scope=='item'].nlargest(3,'forecast').itertuples():add('Plan stock against forecast',x.entity_id,'High',f'{x.date}: {x.forecast:.0f} portions; heuristic range {x.lower_estimate:.0f}–{x.upper_estimate:.0f}')
 if len(a):add('Investigate anomalies','All restaurants','High',f'{len(a)} analytical flags; inspect underlying records')
 return pd.DataFrame(rows)