"""Synthetic restaurant data, seed-controlled and intentionally imperfect."""
from pathlib import Path
import argparse,json
import numpy as np,pandas as pd
from src.schema import CHANNELS
ROOT=Path(__file__).resolve().parents[1]
def generate(lines=1050000,seed=42,out=ROOT/'raw_data'):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);r=np.random.default_rng(seed);n=max(100000,lines//4);days=400;start=pd.Timestamp('2025-01-01');t={};ni=150;nc=50000
 t['customers']=pd.DataFrame({'customer_id':np.arange(1,nc+1),'alias':[f'Guest-{i:05}' for i in range(nc)],'joined_date':str(start.date())})
 cats=['Burgers','Pizza','Rice','Grills','Pasta','Salads','Desserts','Beverages','Breakfast','Sides'];t['categories']=pd.DataFrame({'category_id':range(1,11),'name':cats})
 prices=r.integers(200,1800,ni).astype(float);costs=prices*r.uniform(.25,.7,ni);prices[0]=400;costs[0]=480;costs[1]=prices[1]*.2
 t['menu']=pd.DataFrame({'item_id':range(1,ni+1),'category_id':np.arange(ni)%10+1,'name':[f'{cats[i%10]} {i//10+1:02}' for i in range(ni)],'price':prices,'unit_cost':costs.round(2),'available':1,'introduced_date':[str(start.date())]*149+[str((start+pd.Timedelta(days=375)).date())]})
 areas=['Clifton','DHA','Gulshan','Johar','PECHS','Saddar','Malir','Korangi','Nazimabad','Bahadurabad'];t['locations']=pd.DataFrame({'location_id':range(1,21),'name':[f'{areas[i%10]} {i//10+1}' for i in range(20)],'region':['South','North']*10})
 t['promotions']=pd.DataFrame([(i,f'Campaign {i}',str((start+pd.Timedelta(days=(i-1)*30+5)).date()),str((start+pd.Timedelta(days=(i-1)*30+19)).date()),.5 if i%3==0 else .12) for i in range(1,13)],columns=['promotion_id','name','start_date','end_date','discount'])
 t['pricing_history']=pd.DataFrame([(i*5+q+1,i+1,str((start+pd.Timedelta(days=q*90)).date()),round(prices[i]*(1+.06*q),2)) for i in range(ni) for q in range(5)],columns=['price_id','item_id','effective_date','price'])
 d=np.arange(days);w=1+.3*(d%7>=5)+.2*np.sin(2*np.pi*d/365)+d*.001;day=r.choice(days,n,p=w/w.sum());hours=np.array([1]*10+[3,5,8,8,5,3,3,5,8,10,10,8,4,2]);hour=r.choice(24,n,p=hours/hours.sum());cust=r.integers(1,nc+1,n);cust[(cust<5000)&(day>260)]+=5000;cust[(cust>45000)&(day<300)]-=5000;cust[:nc]=np.arange(1,nc+1);day[:5000]=r.integers(0,200,5000);day[45000:nc]=r.integers(320,400,5000)
 loc=r.integers(1,21,n);promo=np.zeros(n,int);disc=np.zeros(n)
 for p in t['promotions'].itertuples():
  a=(pd.Timestamp(p.start_date)-start).days;b=(pd.Timestamp(p.end_date)-start).days;mask=(day>=a)&(day<=b)&(r.random(n)<.65);promo[mask]=p.promotion_id;disc[mask]=p.discount
 dates=start+pd.to_timedelta(day,unit='D')+pd.to_timedelta(hour,unit='h');t['orders']=pd.DataFrame({'order_id':range(1,n+1),'customer_id':cust,'location_id':loc,'date':dates.astype(str),'channel':r.choice(CHANNELS,n),'promotion_id':promo,'status':r.choice(['completed','cancelled'],n,p=[.985,.015])})
 oid=np.concatenate([np.arange(n),r.integers(0,n,lines-n)]);r.shuffle(oid);pop=np.ones(ni);pop[:5]=[6,.12,4,5,.15];item=r.choice(ni,lines,p=pop/pop.sum());mask=(oid%5==0)&(r.random(lines)<.65);item[mask]=r.choice([9,19,29],mask.sum());item[(loc[oid]%3==0)&(r.random(lines)<.2)]=5;item[(day[oid]%7>=5)&(r.random(lines)<.12)]=6;item[(day[oid]>300)&(r.random(lines)<.12)]=7;item[(disc[oid]>.3)&(r.random(lines)<.2)]=3;item[(item==149)&(day[oid]<375)]=8;item[(item==10)&(r.random(lines)<day[oid]/500)]=9
 qty=r.choice([1,2,3],lines,p=[.8,.16,.04]);unit=(prices[item]*(1+.06*(day[oid]//90))).round(2);t['order_items']=pd.DataFrame({'line_id':range(1,lines+1),'order_id':oid+1,'item_id':item+1,'quantity':qty,'unit_price':unit,'discount':disc[oid]})
 nr=max(100000,lines//8);idx=r.choice(lines,nr,replace=False);stars=np.clip(r.normal(4,.65,nr),1,5).round().astype(int);stars[item[idx]==4]=2;stars[(item[idx]==3)&(day[oid[idx]]>330)]=5
 t['ratings']=pd.DataFrame({'rating_id':range(1,nr+1),'order_id':oid[idx]+1,'customer_id':cust[oid[idx]],'item_id':item[idx]+1,'location_id':loc[oid[idx]],'date':dates[oid[idx]].astype(str),'rating':stars})
 daily=pd.DataFrame({'date':dates[oid].strftime('%Y-%m-%d'),'item_id':item+1,'location_id':loc[oid],'quantity':qty}).groupby(['date','item_id','location_id'],as_index=False).quantity.sum();prepared=np.ceil(daily.quantity*(1.08+r.random(len(daily))*.14)).astype(int);prepared[daily.item_id==3]=np.ceil(daily.loc[daily.item_id==3,'quantity']*1.65).astype(int);ids=np.arange(1,len(daily)+1)
 t['inventory']=pd.DataFrame({'inventory_id':ids,'date':daily.date,'item_id':daily.item_id,'location_id':daily.location_id,'opening':prepared,'replenishment':0,'prepared':prepared,'consumed':daily.quantity,'unit':'portion'})
 t['wastage']=pd.DataFrame({'wastage_id':ids,'date':daily.date,'item_id':daily.item_id,'location_id':daily.location_id,'quantity':prepared-daily.quantity,'unit_cost':costs[daily.item_id.to_numpy()-1].round(2),'reason':r.choice(['Overproduction','Spoilage','Preparation'],len(daily)),'unit':'portion'})
 for k in ['orders','order_items']:t[k]=pd.concat([t[k],t[k].head(100)],ignore_index=True)
 t['orders'].loc[100:109,'customer_id']=np.nan;t['orders'].loc[110:119,'location_id']=9999;t['orders'].loc[120:129,'date']='invalid'
 t['order_items'].loc[200:209,'quantity']=-2;t['order_items'].loc[210:219,'unit_price']=-10;t['order_items'].loc[220:229,'item_id']=9999;t['order_items'].loc[230:239,'discount']=1.2;t['ratings'].loc[:9,'rating']=7;t['wastage'].loc[:9,'quantity']=999999;t['inventory'].loc[:9,'unit']='kg'
 for k,v in t.items():v.to_csv(out/f'{k}.csv',index=False);(ROOT/'sample_data').mkdir(exist_ok=True);v.head(100).to_csv(ROOT/f'sample_data/{k}.csv',index=False)
 stats={'seed':seed,'synthetic':True,'days':400,'currency':'PKR','rows':{k:len(v) for k,v in t.items()}};(out/'manifest.json').write_text(json.dumps(stats,indent=2), encoding='utf-8');print(json.dumps(stats,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--lines',type=int,default=1050000);p.add_argument('--seed',type=int,default=42);p.add_argument('--out',type=Path,default=ROOT/'raw_data');a=p.parse_args();generate(a.lines,a.seed,a.out)
