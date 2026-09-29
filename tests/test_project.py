import io,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd,pytest
from src.database import ROOT
from src.app import create_app
from src.scenarios import simulate
from python_pipeline.analytics import classify,baskets
from python_pipeline.models import features,metrics
from python_pipeline.quality import load
@pytest.fixture
def client(tmp_path):return create_app({'TESTING':True,'DATABASE':str(tmp_path/'app.db'),'SECRET_KEY':'test-only'}).test_client()
def token(c):
 c.get('/login')
 with c.session_transaction() as s:return s['csrf']
def login(c,u='admin'):
 t=token(c);r=c.post('/login',data={'csrf':t,'username':u,'password':'DineIQ-Demo-2026!'});assert r.status_code==302
 with c.session_transaction() as s:return s['csrf']
def test_auth_required(client):assert client.get('/api/summary').status_code==401
def test_csrf(client):assert client.post('/login',data={'username':'admin','password':'DineIQ-Demo-2026!'}).status_code==403
def test_bad_password(client):
 r=client.post('/login',data={'csrf':token(client),'username':'admin','password':'wrong'});assert b'Incorrect' in r.data;assert client.get('/api/summary').status_code==401
def test_login_security_headers(client):
 login(client);r=client.get('/api/summary');assert r.status_code==200;assert r.headers['X-Frame-Options']=='DENY';assert "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
@pytest.mark.parametrize('u',['manager','regional','analyst'])
def test_roles(client,u):
 t=login(client,u);assert client.get('/api/manage/menu').status_code==403;assert client.get('/api/audit').status_code==403;assert client.post('/api/manage/menu',json={},headers={'X-CSRF-Token':t}).status_code==403
def test_no_registration_escalation(client):
 t=token(client);assert client.post('/register',data={'csrf':t,'username':'newuser','password':'Strong-password-2026','role':'administrator'}).status_code==302;client.post('/login',data={'csrf':t,'username':'newuser','password':'Strong-password-2026'});assert client.get('/api/audit').status_code==403
def test_weak_password(client):assert client.post('/register',data={'csrf':token(client),'username':'new','password':'123'}).status_code==400
def test_export(client):
 login(client);r=client.get('/api/export/menu?item_id=1');assert r.status_code==200;d=pd.read_csv(io.BytesIO(r.data));assert len(d)==1;assert d.iloc[0].item_id==1
@pytest.mark.parametrize('path',['/api/report/unknown','/api/export/unknown'])
def test_unknown_report(client,path):login(client);assert client.get(path).status_code==404
def test_manager_no_jobs(client):
 t=login(client,'manager');assert client.post('/api/jobs',json={'kind':'generate'},headers={'X-CSRF-Token':t}).status_code==403
def test_unknown_job(client):
 t=login(client);assert client.post('/api/jobs',json={'kind':'shell'},headers={'X-CSRF-Token':t}).status_code==409
def test_bad_zip(client):
 t=login(client);assert client.post('/api/upload',data={'file':(io.BytesIO(b'not a zip'),'data.zip')},headers={'X-CSRF-Token':t}).status_code==400
def test_zip_traversal(client):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:z.writestr('../bad.csv','bad')
 b.seek(0);t=login(client);assert client.post('/api/upload',data={'file':(b,'x.zip')},headers={'X-CSRF-Token':t}).status_code==400
def test_empty_search(client):
 login(client);d=client.get('/api/report/menu?item_id=99999').get_json();assert d['total']==0;assert d['rows']==[]
def test_page(client):
 login(client);d=client.get('/api/report/customers?size=15&page=2').get_json();assert len(d['rows'])==15;assert d['page']==2
def test_filtered_totals(client):
 login(client);d=client.get('/api/explore?location_id=1&start=2025-01-01&end=2025-01-31').get_json();f=pd.read_parquet(ROOT/'processed_data/facts.parquet',filters=[('location_id','=',1),('date','>=',pd.Timestamp('2025-01-01')),('date','<=',pd.Timestamp('2025-01-31'))]);assert d['orders']>0;assert d['revenue']==pytest.approx(f.revenue.sum())
def test_bad_scenario_request(client):
 t=login(client);assert client.post('/api/scenario',json={'item_id':1,'price_change':-1},headers={'X-CSRF-Token':t}).status_code==400
def test_invalid_prediction(client):
 t=login(client);assert client.post('/api/predict',json={'bad':1},headers={'X-CSRF-Token':t}).status_code==400
BASE={'quantity':100,'revenue':1000,'cost':400,'prepared':120}
def test_scenario_identity():
 d=simulate(BASE);assert d['estimated_revenue']==1000;assert d['estimated_waste']==20;assert d['estimated_after_waste']==520
def test_removal():assert simulate(BASE,remove=True)['estimated_demand']==0
@pytest.mark.parametrize('v',[{'price_change':-1},{'discount':1.2},{'waste_rate':-1},{'promotion_frequency':2},{'demand_change':float('nan')}])
def test_scenario_bounds(v):
 with pytest.raises(ValueError):simulate(BASE,**v)
def test_discount_exposure():assert simulate(BASE,discount=.2,promotion_frequency=0)['estimated_revenue']==1000;assert simulate(BASE,discount=.2,promotion_frequency=1)['estimated_demand']>100

def test_basket_metrics():
 b=baskets(pd.DataFrame({'order_id':[1,1,2,2,3,4],'item_id':[1,2,1,2,1,3]}),0);x=b[(b.antecedent==1)&(b.consequent==2)].iloc[0];assert x.support==.5;assert x.confidence==pytest.approx(2/3);assert x.lift==pytest.approx(4/3)
def test_basket_duplicates():
 b=baskets(pd.DataFrame({'order_id':[1,1,1,2],'item_id':[1,1,2,3]}),0);assert b.orders_together.max()==1

def test_contradictory_menu():
 d=pd.DataFrame({'quantity':[1000,5,1000,500,30],'margin_pct':[-20,70,60,40,20],'rating':[4,4.8,4,4,3],'waste_pct':[4,3,50,5,5],'repeat_rate':[.5,.8,.7,.6,.1],'contribution':[-20,35,400,200,10],'promo_dependency':[.2,.1,.2,.1,.9],'active_days':[300,300,300,300,5],'sales_trend':[0,0,0,0,-.4]});m=classify(d);assert m.iloc[0].performance_class=='Low Performer';assert m.iloc[1].performance_class=='Hidden Opportunity';assert m.iloc[2].performance_class=='Low Performer';assert m.iloc[4].history_status=='Insufficient history'
def test_lags_no_future_leak():
 x=pd.DataFrame({'date':pd.date_range('2025-01-01',periods=50),'entity_id':1,'actual':np.arange(50.)});a=features(x);x.loc[40:,'actual']=99999;b=features(x);pd.testing.assert_frame_equal(a[a.date<'2025-02-10'],b[b.date<'2025-02-10']);assert a.iloc[0].lag1==27;assert a.iloc[0].mean28==13.5

def test_zero_metric():assert metrics([0,0],[0,0])['mape'] is None

def test_schema_reject(tmp_path):
 pd.DataFrame({'bad':[1]}).to_csv(tmp_path/'customers.csv',index=False)
 with pytest.raises(ValueError,match='missing columns'):load(tmp_path)

@pytest.mark.parametrize('name', ['customers','categories','menu','locations','promotions','orders','order_items','pricing_history','ratings','inventory','wastage'])
def test_physical_row_counts(name):
 manifest=json.loads((ROOT/'raw_data/manifest.json').read_text(encoding='utf-8'));actual=sum(1 for _ in (ROOT/f'raw_data/{name}.csv').open())-1;assert actual==manifest['rows'][name]

def test_large_dataset():
 m=json.loads((ROOT/'raw_data/manifest.json').read_text(encoding='utf-8'));r=m['rows'];assert r['order_items']>=1000000;assert r['orders']>=100000;assert r['customers']>=50000;assert r['menu']>=150;assert r['locations']>=20;assert r['ratings']>=100000;assert r['wastage']>=50000;assert m['days']>=365

def test_clean_counts_match():
 a=json.loads((ROOT/'reports/python_quality.json').read_text(encoding='utf-8'));b=json.loads((ROOT/'reports/spark_quality.json').read_text(encoding='utf-8'));assert {x['table']:x['clean'] for x in a}=={x['table']:x['clean'] for x in b}
def test_quality_defects():
 d={x['table']:x for x in json.loads((ROOT/'reports/python_quality.json').read_text(encoding='utf-8'))};assert d['orders']['rejected']>100;assert d['order_items']['rejected']>100;assert 'duplicate_primary_key' in d['order_items']['reasons'];assert d['wastage']['rejected']>=10

def test_spark_parquet_reconciliation():
 p=ROOT/'parquet_data/order_facts';assert len(list(p.glob('month=*')))>=12;d=pd.read_parquet(p,columns=['line_id','revenue']);s=json.loads((ROOT/'reports/summary.json').read_text(encoding='utf-8'));assert len(d)==s['fact_rows'];assert d.line_id.is_unique;assert d.revenue.sum()==pytest.approx(s['revenue'])

def test_equivalent_unseen_comparison():
 d=pd.read_csv(ROOT/'reports/comparison.csv');assert len(d)>=100;assert np.allclose(d.actual_spark,d.actual_python);assert not np.allclose(d.spark_prediction,d.python_prediction);assert d.record_id.is_unique;assert (~d.match).any()
def test_three_models():
 m=json.loads((ROOT/'reports/spark_models.json').read_text(encoding='utf-8'));assert len(m['models'])>=3;assert m['validation_start']<m['test_start'];assert m['beats_baseline']
def test_chronological_split():
 a=pd.read_parquet(ROOT/'processed_data/train.parquet');b=pd.read_parquet(ROOT/'processed_data/validation.parquet');c=pd.read_parquet(ROOT/'processed_data/test.parquet');assert a.date.max()<b.date.min();assert b.date.max()<c.date.min()
def test_forecast_scopes():
 d=pd.read_csv(ROOT/'reports/forecast.csv');assert set(d.scope)=={'item','category','location'};assert (d.forecast>=0).all();assert (d.upper_estimate>=d.lower_estimate).all();assert d.date.nunique()==30

def test_recommendations():
 d=pd.read_csv(ROOT/'reports/recommendations.csv');assert d.evidence.notna().all();assert (d.priority=='Critical').any()
def test_location_difference():
 d=pd.read_csv(ROOT/'reports/location_menu.csv');assert (d.groupby('item_id').performance_class.nunique()>1).any()
def test_business_signals():
 assert 'Highly Price Sensitive' in set(pd.read_csv(ROOT/'reports/pricing.csv').sensitivity);assert (pd.read_csv(ROOT/'reports/promotions.csv').trap!='No rule triggered').any();assert pd.read_csv(ROOT/'reports/customers.csv').churn_risk.any();a=pd.read_csv(ROOT/'reports/anomalies.csv');assert {'Rating anomaly','Unusual order'}<=set(a.type)


def test_health_endpoint(client):
 d=client.get('/api/health');assert d.status_code in (200,503);j=d.get_json();assert j['status'] in ('ok','degraded');assert 'artifacts' in j

def test_search_ui_is_wired():
 js=(ROOT/'static/app.js').read_text(encoding='utf-8');html=(ROOT/'templates/index.html').read_text(encoding='utf-8');assert 'setupGlobalSearch' in js;assert 'global-search-btn' in html;assert 'global-search-input' in html;assert 'ctrlKey' in js or 'metaKey' in js

def test_database_autocreate_present():
 src=(ROOT/'src/app.py').read_text(encoding='utf-8');assert "dbdir.mkdir(parents=True,exist_ok=True)" in src

def test_shell_controls_are_wired():
 html=(ROOT/'templates/index.html').read_text(encoding='utf-8');js=(ROOT/'static/app.js').read_text(encoding='utf-8')
 assert 'workspace-btn' in html and 'workspace-panel' in html and 'openWorkspace' in js
 assert 'notification-btn' in html and 'notification-panel' in html and 'openNotifications' in js
 assert "navigate(b.dataset.workspaceView)" in js and "navigate('recommendations')" in js

def test_dark_mode_native_lists_are_styled():
 css=(ROOT/'static/style.css').read_text(encoding='utf-8')
 assert 'html[data-theme="dark"]{color-scheme:dark}' in css
 assert '[data-theme="dark"] option' in css
 assert 'background-color:#1c1611' in css