import os,json,secrets,hmac,time,zipfile,tempfile,shutil
from pathlib import Path
from functools import wraps
import pandas as pd,numpy as np
from flask import Flask,session,request,jsonify,render_template,redirect,Response,send_file
from werkzeug.security import generate_password_hash,check_password_hash
from src.database import ROOT,connect,init,audit
from src.schema import SCHEMAS,PK,FK
from src.scenarios import simulate
from src.jobs import LOCK
REPORTS=['menu','location_menu','customers','baskets','pricing','promotions','anomalies','waste_risk','forecast','recommendations','locations','channels','wastage','peaks','daily','ratings','comparison'];CACHE={};ATTEMPTS={}
def frame(name):
 p=ROOT/f'reports/{name}.csv';mtime=p.stat().st_mtime
 if name not in CACHE or CACHE[name][0]!=mtime:CACHE[name]=(mtime,pd.read_csv(p,low_memory=False))
 return CACHE[name][1].copy()
def records(d):return json.loads(d.replace([np.inf,-np.inf],np.nan).to_json(orient='records',date_format='iso'))
def create_app(test_config=None):
 app=Flask(__name__,template_folder=str(ROOT/'templates'),static_folder=str(ROOT/'static'));dbdir=ROOT/'database';dbdir.mkdir(parents=True,exist_ok=True);key=dbdir/'session_secret'
 if not key.exists():key.write_text(secrets.token_hex(32), encoding='utf-8');key.chmod(0o600)
 app.config.update(SECRET_KEY=os.getenv('DINEIQ_SECRET_KEY') or key.read_text(encoding='utf-8'),MAX_CONTENT_LENGTH=250*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('DINEIQ_HTTPS')=='1',PERMANENT_SESSION_LIFETIME=3600)
 if test_config:app.config.update(test_config)
 dbpath=app.config.get('DATABASE');init(dbpath)
 def db():return connect(dbpath)
 def log(action,details=''):audit(session.get('uid'),action,details,dbpath)
 def auth(roles=None):
  def decorate(fn):
   @wraps(fn)
   def wrapped(*args,**kwargs):
    if not session.get('uid'):return (jsonify(error='Log in first'),401) if request.path.startswith('/api') else redirect('/login')
    if roles and session['role'] not in roles:return jsonify(error='Role does not have permission'),403
    return fn(*args,**kwargs)
   return wrapped
  return decorate
 @app.before_request
 def csrf():
  session.setdefault('csrf',secrets.token_hex(24))
  if request.method in ['POST','PUT','PATCH','DELETE'] and not hmac.compare_digest(request.headers.get('X-CSRF-Token') or request.form.get('csrf',''),session['csrf']):return jsonify(error='Invalid CSRF token; reload page'),403
 @app.after_request
 def headers(r):
  r.headers['X-Frame-Options']='DENY';r.headers['X-Content-Type-Options']='nosniff';r.headers['Cache-Control']='no-store';r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'";return r
 @app.errorhandler(Exception)
 def errors(e):
  from werkzeug.exceptions import HTTPException
  if isinstance(e,HTTPException):return jsonify(error=e.description),e.code
  if isinstance(e,(ValueError,TypeError)):return jsonify(error=str(e)),400
  app.logger.exception('Operation failed');return jsonify(error='Operation failed. Check input and server logs.'),500
 @app.route('/login',methods=['GET','POST'])
 def login():
  error=None
  if request.method=='POST':
   user=request.form.get('username','');key=(request.remote_addr,user);recent=[x for x in ATTEMPTS.get(key,[]) if time.time()-x<300]
   if len(recent)>=10:return render_template('login.html',error='Too many attempts; retry after five minutes'),429
   with db() as c:u=c.execute('SELECT * FROM users WHERE username=?',(user,)).fetchone()
   if u and check_password_hash(u['password'],request.form.get('password','')):session.clear();session.update(uid=u['id'],username=user,role=u['role'],csrf=secrets.token_hex(24));session.permanent=True;log('login');return redirect('/')
   ATTEMPTS[key]=recent+[time.time()];error='Incorrect username or password'
  return render_template('login.html',error=error)
 @app.post('/register')
 def register():
  u=request.form.get('username','').strip();p=request.form.get('password','')
  if not 3<=len(u)<=64 or len(p)<12:return jsonify(error='Username 3–64 characters, password at least 12'),400
  import sqlite3
  try:
   with db() as c:c.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',(u,generate_password_hash(p),'manager'))
  except sqlite3.IntegrityError:return jsonify(error='Username unavailable'),409
  return redirect('/login')
 @app.post('/logout')
 @auth()
 def logout():log('logout');session.clear();return redirect('/login')
 @app.get('/')
 @auth()
 def index():return render_template('index.html')
 @app.get('/api/options')
 @auth()
 def options():return jsonify(locations=records(pd.read_csv(ROOT/'raw_data/locations.csv')),categories=records(pd.read_csv(ROOT/'raw_data/categories.csv')),items=records(pd.read_csv(ROOT/'raw_data/menu.csv')[['item_id','name']]),role=session['role'])
 @app.get('/api/health')
 def health():
  required=[ROOT/'reports/summary.json',ROOT/'processed_data/facts.parquet',ROOT/'models/python_demand.joblib']
  return jsonify(status='ok' if all(x.exists() for x in required) else 'degraded',artifacts={x.name:x.exists() for x in required},version='TechWiz7-ready'),200 if all(x.exists() for x in required) else 503
 @app.get('/api/summary')
 @auth()
 def summary():
  if not (ROOT/'reports/summary.json').exists():return jsonify(error='Run Python pipeline first'),409
  d=json.loads((ROOT/'reports/summary.json').read_text(encoding='utf-8'));d.update(daily=records(frame('daily')),classes=frame('menu').performance_class.value_counts().to_dict(),top=records(frame('menu').nlargest(6,'contribution')),actions=records(frame('recommendations').head(5)));return jsonify(d)
 def filtered(name):
  d=frame(name)
  for col in ['location_id','item_id','category_id','channel','promotion_id','performance_class','segment','scope','entity_id']:
   v=request.args.get(col)
   if v and col in d:d=d[d[col].astype(str).str.replace(r'\.0$','',regex=True)==v]
  for col,arg,op in [('rating','rating_min','min'),('waste_pct','waste_max','max')]:
   if col in d and request.args.get(arg):d=d[d[col]>=float(request.args[arg])] if op=='min' else d[d[col]<=float(request.args[arg])]
  if 'date' in d:
   if request.args.get('start'):d=d[pd.to_datetime(d.date)>=pd.Timestamp(request.args['start'])]
   if request.args.get('end'):d=d[pd.to_datetime(d.date)<=pd.Timestamp(request.args['end'])]
  if request.args.get('q'):d=d[d.astype(str).apply(lambda s:s.str.lower().str.contains(request.args['q'].lower(),regex=False)).any(axis=1)]
  return d
 @app.get('/api/report/<name>')
 @auth()
 def report(name):
  if name not in REPORTS:return jsonify(error='Unknown report'),404
  if not (ROOT/f'reports/{name}.csv').exists():return jsonify(error='Run the matching pipeline first'),409
  d=filtered(name);page=max(1,int(request.args.get('page',1)));size=min(500,max(1,int(request.args.get('size',100))));return jsonify(rows=records(d.iloc[(page-1)*size:page*size]),total=len(d),columns=list(d),page=page,size=size)
 @app.get('/api/export/<name>')
 @auth()
 def export(name):
  if name not in REPORTS:return jsonify(error='Unknown report'),404
  d=filtered(name)
  for col in d.select_dtypes('object'):d[col]=d[col].map(lambda x:"'"+x if isinstance(x,str) and x.startswith(('=','+','-','@','\t','\r')) else x)
  log('export',f'{name}: {len(d)} rows');return Response(d.to_csv(index=False),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={name}.csv'})
 @app.get('/api/evidence')
 @auth()
 def evidence():return jsonify({n:json.loads((ROOT/f'reports/{n}.json').read_text(encoding='utf-8')) if (ROOT/f'reports/{n}.json').exists() else {'status':'Not run'} for n in ['python_models','spark_models','comparison','waste_model','python_quality','spark_quality']})
 @app.post('/api/scenario')
 @auth()
 def scenario():
  v=request.get_json() or {};item=int(v.pop('item_id'));m=frame('menu').set_index('item_id')
  if item not in m.index:return jsonify(error='Unknown item'),400
  e=frame('pricing').set_index('item_id').loc[item,'elasticity'];args={k:v[k] for k in ['price_change','discount','promotion_frequency','demand_change','preparation_change','waste_rate','remove'] if k in v};args['elasticity']=float(np.clip(e,-3,0)) if pd.notna(e) else -.5;result=simulate(m.loc[item].to_dict(),**args);log('scenario',str(item));return jsonify(result)
 @app.get('/api/predict/example')
 @auth()
 def example():
  from python_pipeline.models import FEATURES
  row=pd.read_parquet(ROOT/'processed_data/test.parquet').iloc[0];return jsonify({k:float(row[k]) for k in FEATURES})
 @app.post('/api/predict')
 @auth()
 def prediction():
  from src.inference import predict
  payload=request.get_json() or {}
  if not isinstance(payload,dict):raise ValueError('Prediction input must be a JSON object')
  mode=payload.get('mode','both');values=payload.get('features',payload)
  try:d=predict(values,mode)
  except (RuntimeError,FileNotFoundError,ImportError) as e:
   app.logger.exception('Prediction unavailable');return jsonify(error=str(e)),503
  log('prediction',json.dumps(d));return jsonify(d)
 @app.get('/api/explore')
 @auth()
 def explore():
  filters=[]
  for key in ['location_id','item_id','category_id','promotion_id']:
   if request.args.get(key):filters.append((key,'=',int(request.args[key])))
  if request.args.get('channel'):filters.append(('channel','=',request.args['channel']))
  for key,op,arg in [('date','>=','start'),('date','<=','end'),('unit_price','>=','price_min'),('unit_price','<=','price_max')]:
   if request.args.get(arg):filters.append((key,op,pd.Timestamp(request.args[arg]) if key=='date' else float(request.args[arg])))
  cols=['order_id','customer_id','item_id','item_name','quantity','revenue','contribution'];f=pd.read_parquet(ROOT/'processed_data/facts.parquet',columns=cols,filters=filters or None)
  if request.args.get('segment'):
   c=frame('customers');f=f[f.customer_id.isin(c.loc[c.segment==request.args['segment'],'customer_id'])]
  m=frame('menu')
  if request.args.get('rating_min'):m=m[m.rating>=float(request.args['rating_min'])]
  if request.args.get('waste_max'):m=m[m.waste_pct<=float(request.args['waste_max'])]
  if request.args.get('performance_class'):m=m[m.performance_class==request.args['performance_class']]
  f=f[f.item_id.isin(m.item_id)];d=f.groupby(['item_id','item_name']).agg(quantity=('quantity','sum'),revenue=('revenue','sum'),contribution=('contribution','sum')).reset_index();return jsonify(revenue=float(f.revenue.sum()),contribution=float(f.contribution.sum()),orders=int(f.order_id.nunique()),rows=records(d),note='Transaction metrics recomputed. Customer segment and item attributes use full-history snapshots.')
 @app.route('/api/jobs',methods=['GET','POST'])
 @auth()
 def jobs():
  if request.method=='GET':
   with db() as c:return jsonify([dict(x) for x in c.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 40')])
  if session['role'] not in ['administrator','analyst']:return jsonify(error='Processing permission required'),403
  from src.jobs import start
  v=request.get_json() or {};kind=v.get('kind');h=int(v.get('horizon',30))
  if kind=='regenerate' and session['role']!='administrator':return jsonify(error='Administrator only'),403
  if not 1<=h<=90:return jsonify(error='Horizon must be 1–90'),400
  try:jid=start(kind,h,dbpath)
  except ValueError as e:return jsonify(error=str(e)),409
  log('job_started',f'{kind}:{jid}');return jsonify(id=jid),202
 @app.get('/api/generated/<name>')
 @auth()
 def generated(name):
  allowed={'report':'Generated_Result_Report.pdf','json':'generated_result.json','comparison':'comparison.csv'}
  if name not in allowed:return jsonify(error='Unknown generated output'),404
  from src.workflow import verify_stage
  try:verify_stage('generate')
  except (ValueError,FileNotFoundError) as e:return jsonify(error=str(e)),409
  return send_file(ROOT/'reports'/allowed[name],as_attachment=True)
 @app.get('/api/audit')
 @auth(['administrator'])
 def audits():
  with db() as c:return jsonify([dict(x) for x in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200')])
 @app.route('/api/manage/<name>',methods=['GET','POST'])
 @auth(['administrator'])
 def manage(name):
  if name not in SCHEMAS:return jsonify(error='Unknown table'),404
  if request.method=='GET':return jsonify(rows=records(pd.read_csv(ROOT/f'raw_data/{name}.csv',nrows=100)),schema=SCHEMAS[name],primary_key=PK[name])
  v=request.get_json() or {}
  if set(v)!=set(SCHEMAS[name]):return jsonify(error='Provide all schema fields only'),400
  for c,t in SCHEMAS[name].items():
   if t in ['int','float']:
    x=float(v[c])
    if not np.isfinite(x) or (t=='int' and x%1):raise ValueError('Invalid number')
    v[c]=int(x) if t=='int' else x
   elif t=='date':
    d=pd.to_datetime(v[c],errors='coerce')
    if pd.isna(d):raise ValueError('Invalid date')
    v[c]=str(d)
   else:v[c]=str(v[c])
  if any(v[c]<0 for c in ['price','unit_price','unit_cost','quantity','opening','replenishment','prepared','consumed'] if c in v):raise ValueError('Negative amount')
  if 'rating' in v and not 1<=v['rating']<=5:raise ValueError('Invalid rating')
  if 'discount' in v and not 0<=v['discount']<=1:raise ValueError('Invalid discount')
  for c,parent in FK.get(name,{}).items():
   if v[c] not in pd.read_csv(ROOT/f'raw_data/{parent}.csv',usecols=[c])[c].values:raise ValueError('Unknown reference')
  if not LOCK.acquire(blocking=False):return jsonify(error='Processing active; retry later'),409
  try:
   path=ROOT/f'raw_data/{name}.csv';d=pd.read_csv(path);mask=d[PK[name]]==v[PK[name]]
   if mask.any():d.loc[mask,list(v)]=list(v.values())
   else:d=pd.concat([d,pd.DataFrame([v])],ignore_index=True)
   tmp=path.with_suffix('.tmp');d.to_csv(tmp,index=False);tmp.replace(path)
   if name=='menu':
    hp=ROOT/'raw_data/pricing_history.csv';hist=pd.read_csv(hp);pd.concat([hist,pd.DataFrame([{'price_id':int(hist.price_id.max())+1,'item_id':v['item_id'],'effective_date':str(pd.Timestamp.now().date()),'price':v['price']}])]).to_csv(hp,index=False)
  finally:LOCK.release()
  log('record_saved',f'{name}:{v[PK[name]]}');return jsonify(message='Saved. Rerun both pipelines to refresh reports.')
 @app.post('/api/upload')
 @auth(['administrator','analyst'])
 def upload():
  file=request.files.get('file')
  if not file:return jsonify(error='Select a ZIP of canonical CSV tables'),400
  if not LOCK.acquire(blocking=False):return jsonify(error='Wait for active processing'),409
  try:
   with zipfile.ZipFile(file.stream) as z:
    required={k+'.csv' for k in SCHEMAS};members=z.infolist()
    if len(members)>100 or sum(x.file_size for x in members)>2_000_000_000:raise ValueError('Archive exceeds limits')
    if not required.issubset(z.namelist()) or any(Path(x.filename).is_absolute() or '..' in Path(x.filename).parts for x in members):raise ValueError('All documented CSV tables required at archive root; unsafe paths rejected')
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
     for n in required:
      p=Path(tmp)/n
      with z.open(n) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst)
      if set(SCHEMAS[n[:-4]])-set(pd.read_csv(p,nrows=5)):raise ValueError(f'Missing columns in {n}')
     backup=ROOT/'raw_data_backup';backup.mkdir(exist_ok=True)
     for n in required:
      current=ROOT/'raw_data'/n
      if current.exists():shutil.copy2(current,backup/n)
      shutil.move(str(Path(tmp)/n),current)
  except zipfile.BadZipFile:return jsonify(error='Invalid ZIP archive'),400
  finally:LOCK.release()
  log('dataset_uploaded');return jsonify(message='Source loaded. Run Python, Spark and Compare. Reports remain the previous snapshot until rebuilt.')
 return app
if __name__=='__main__':create_app().run(host='127.0.0.1',port=int(os.getenv('PORT',5000)),debug=False)
