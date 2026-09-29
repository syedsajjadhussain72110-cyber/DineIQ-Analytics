from pathlib import Path
import pandas as pd,numpy as np
from src.schema import SCHEMAS,PK,FK,CHANNELS

def load(raw,output=None):
 tables={};reports=[]
 for name,cols in SCHEMAS.items():
  files=sorted(Path(raw).glob(name+'.csv')) or sorted((Path(raw)/name).glob('*.csv'))
  if not files:raise ValueError(f'Missing {name}.csv')
  d=pd.concat([pd.read_csv(x,low_memory=False) for x in files],ignore_index=True)
  if set(cols)-set(d):raise ValueError(f'{name}: missing columns {set(cols)-set(d)}')
  reasons=pd.Series('',index=d.index)
  def flag(mask,reason):
   nonlocal reasons
   reasons.loc[pd.Series(mask,index=d.index).fillna(True)]+=reason+';'
  for c,t in cols.items():
   if t in ['int','float']:
    d[c]=pd.to_numeric(d[c],errors='coerce');flag(~np.isfinite(d[c]),'invalid_'+c)
    if t=='int':flag(d[c]%1!=0,'noninteger_'+c)
   elif t=='date':d[c]=pd.to_datetime(d[c],errors='coerce');flag(d[c].isna(),'invalid_'+c)
   else:flag(d[c].isna(),'missing_'+c)
  flag(d.duplicated(PK[name]),'duplicate_primary_key')
  for c,parent in FK.get(name,{}).items():flag(~d[c].isin(tables[parent][c]),'invalid_reference_'+c)
  if name=='orders':flag(d.status!='completed','cancelled_or_invalid_status');flag(~d.channel.isin(CHANNELS),'invalid_channel');flag((d.promotion_id!=0)&~d.promotion_id.isin(tables['promotions'].promotion_id),'invalid_promotion')
  for c in ['price','unit_price','unit_cost','quantity','opening','replenishment','prepared','consumed']:
   if c in d:flag(d[c]<0,'negative_'+c)
  if name=='order_items':flag(d.quantity<=0,'nonpositive_quantity')
  if 'discount' in d:flag(~d.discount.between(0,1),'invalid_discount')
  if name=='ratings':flag(~d.rating.between(1,5),'invalid_rating')
  if name in ['inventory','wastage']:flag(d.unit!='portion','inconsistent_unit')
  if name=='inventory':flag((d.consumed>d.prepared)|(d.prepared>d.opening+d.replenishment),'impossible_inventory')
  if name=='wastage':
   prep=tables['inventory'].groupby(['date','item_id','location_id']).prepared.sum();limit=pd.MultiIndex.from_frame(d[['date','item_id','location_id']]).map(prep);flag(d.quantity.to_numpy()>pd.Series(limit).fillna(-1).to_numpy(),'impossible_waste')
  bad=reasons!='';reject=d[bad].copy();reject['reason']=reasons[bad];clean=d[~bad].copy();tables[name]=clean;reports.append({'table':name,'raw':len(d),'clean':len(clean),'rejected':len(reject),'reasons':reasons[bad].str.split(';').explode().value_counts().drop('',errors='ignore').to_dict()})
  if output:
   out=Path(output);out.mkdir(parents=True,exist_ok=True);clean.to_parquet(out/f'{name}.parquet',index=False);reject.to_csv(out/f'{name}_quarantine.csv',index=False)
 return tables,reports

def integrate(t):
 f=t['order_items'].merge(t['orders'],on='order_id',validate='many_to_one').merge(t['menu'].rename(columns={'name':'item_name','price':'menu_price'}),on='item_id',validate='many_to_one').merge(t['categories'].rename(columns={'name':'category'}),on='category_id',validate='many_to_one').merge(t['locations'].rename(columns={'name':'location'}),on='location_id',validate='many_to_one')
 f['hour']=f.date.dt.hour;f['weekday']=f.date.dt.dayofweek;f['weekend']=(f.weekday>=5).astype(int);f['date']=f.date.dt.normalize();f['revenue']=f.quantity*f.unit_price*(1-f.discount);f['cost']=f.quantity*f.unit_cost;f['contribution']=f.revenue-f.cost
 return f