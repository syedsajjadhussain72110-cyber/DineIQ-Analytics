"""Independent Spark source-to-model pipeline. Never consumes Pandas predictions/features."""
from pathlib import Path
import os,time,json,shutil,tempfile
from pyspark.sql import SparkSession,functions as F,Window,types as T
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression,RandomForestRegressor,GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark import StorageLevel
from src.schema import SCHEMAS,PK,FK,CHANNELS
ROOT=Path(__file__).resolve().parents[1]
FEATURES=['entity_id','day_index','dow_sin','dow_cos','year_sin','year_cos','lag1','lag7','mean7','mean28']
def run(raw=ROOT/'raw_data',root=ROOT):
 from src.spark_runtime import configure
 from src.workflow import source_digest,record_stage
 configure()
 for folder in ['reports','parquet_data','models']:(root/folder).mkdir(parents=True,exist_ok=True)
 source=source_digest(root)
 stage=Path(tempfile.mkdtemp(prefix='spark-stage-',dir=root))
 (stage/'parquet_data').mkdir();(stage/'models').mkdir()
 start=time.perf_counter();os.environ.setdefault('SPARK_LOCAL_IP','127.0.0.1');spark=SparkSession.builder.master(os.getenv('SPARK_MASTER','local[2]')).appName('DineIQ-independent-Spark').config('spark.driver.memory','3g').config('spark.sql.shuffle.partitions','8').config('spark.ui.enabled','false').config('spark.sql.session.timeZone','UTC').getOrCreate();spark.sparkContext.setLogLevel('WARN');tables={};quality=[]
 try:
  for name,cols in SCHEMAS.items():
   path=Path(raw)/(name+'.csv');path=path if path.exists() else Path(raw)/name;inferred=spark.read.option('header',True).option('inferSchema',True).csv(str(path))
   if set(cols)-set(inferred.columns):raise ValueError(f'{name}: missing required columns')
   schema=T.StructType([T.StructField(c,T.StringType(),True) for c in inferred.columns]);d=spark.read.option('header',True).schema(schema).csv(str(path)).select(*cols);bad=F.lit(False)
   for c,typ in cols.items():
    if typ=='date':d=d.withColumn(c,F.to_timestamp(c))
    elif typ in ['int','float']:
     numeric=F.col(c).cast('double');invalid=numeric.isNull()|F.isnan(numeric)|(F.abs(numeric)>1e308)
     if typ=='int':invalid=invalid|(numeric%1!=0)
     flag='_invalid_'+c;d=d.withColumn(flag,invalid);bad=bad|F.col(flag);d=d.withColumn(c,F.col(c).cast('long' if typ=='int' else 'double'))
    bad=bad|F.col(c).isNull()
   for c in ['price','unit_price','unit_cost','quantity','opening','replenishment','prepared','consumed']:
    if c in cols:bad=bad|(F.col(c)<0)
   if name=='order_items':bad=bad|(F.col('quantity')<=0)
   if 'discount' in cols:bad=bad|~F.col('discount').between(0,1)
   if name=='ratings':bad=bad|~F.col('rating').between(1,5)
   if name=='orders':bad=bad|(F.col('status')!='completed')|~F.col('channel').isin(CHANNELS)
   if name in ['inventory','wastage']:bad=bad|(F.col('unit')!='portion')
   if name=='inventory':bad=bad|(F.col('consumed')>F.col('prepared'))|(F.col('prepared')>F.col('opening')+F.col('replenishment'))
   before=d.count();clean=d.filter(~bad).select(*cols).dropDuplicates([PK[name]])
   for c,parent in FK.get(name,{}).items():clean=clean.join(tables[parent].select(c),c,'left_semi')
   if name=='orders':clean=clean.join(tables['promotions'].select('promotion_id').union(spark.createDataFrame([(0,)],['promotion_id'])),'promotion_id','left_semi')
   if name=='wastage':clean=clean.join(tables['inventory'].groupBy('date','item_id','location_id').agg(F.sum('prepared').alias('_limit')),['date','item_id','location_id'],'inner').filter(F.col('quantity')<=F.col('_limit')).drop('_limit')
   clean=clean.persist(StorageLevel.MEMORY_AND_DISK);after=clean.count();tables[name]=clean;clean.createOrReplaceTempView(name);quality.append({'table':name,'raw':before,'clean':after,'rejected':before-after,'inferred_schema':inferred.schema.simpleString()});d.select(*cols).join(clean.select(PK[name]),PK[name],'left_anti').write.mode('overwrite').parquet(str(stage/f'parquet_data/quarantine_{name}'));print(name,before,after,flush=True)
  fact=spark.sql('''SELECT l.line_id,l.order_id,l.item_id,l.quantity,l.unit_price,l.discount,o.customer_id,o.location_id,o.channel,o.promotion_id,m.category_id,m.unit_cost,to_date(o.date) date,date_format(o.date,'yyyy-MM') month,l.quantity*l.unit_price*(1-l.discount) revenue,l.quantity*m.unit_cost cost,l.quantity*(l.unit_price*(1-l.discount)-m.unit_cost) contribution FROM order_items l JOIN orders o ON l.order_id=o.order_id JOIN menu m ON l.item_id=m.item_id JOIN customers c ON c.customer_id=o.customer_id JOIN categories k ON k.category_id=m.category_id JOIN locations r ON r.location_id=o.location_id''').persist(StorageLevel.MEMORY_AND_DISK);fact.createOrReplaceTempView('facts');fact.repartition('month').write.mode('overwrite').partitionBy('month').parquet(str(stage/'parquet_data/order_facts'))
  spark.sql('''SELECT m.item_id,m.name,p.latest_price,r.rating,i.prepared,w.waste FROM menu m LEFT JOIN (SELECT item_id,max_by(price,effective_date) latest_price FROM pricing_history GROUP BY item_id) p ON m.item_id=p.item_id LEFT JOIN (SELECT item_id,avg(rating) rating FROM ratings GROUP BY item_id) r ON m.item_id=r.item_id LEFT JOIN (SELECT item_id,sum(prepared) prepared FROM inventory GROUP BY item_id) i ON m.item_id=i.item_id LEFT JOIN (SELECT item_id,sum(quantity) waste FROM wastage GROUP BY item_id) w ON m.item_id=w.item_id''').write.mode('overwrite').parquet(str(stage/'parquet_data/menu_features'))
  for sql in (root/'spark_sql').glob('*.sql'):spark.sql(sql.read_text(encoding='utf-8')).toPandas().to_csv(root/f'reports/spark_{sql.stem}.csv',index=False)
  bounds=fact.agg(F.min('date'),F.max('date')).first();cal=spark.sql(f"SELECT explode(sequence(date'{bounds[0]}',date'{bounds[1]}',interval 1 day)) date");entities=fact.select(F.col('location_id').alias('entity_id')).distinct();daily=fact.groupBy('date','location_id').agg(F.sum('quantity').alias('actual')).withColumnRenamed('location_id','entity_id');x=cal.crossJoin(entities).join(daily,['date','entity_id'],'left').fillna(0,subset=['actual']);win=Window.partitionBy('entity_id').orderBy('date');x=x.withColumn('lag1',F.lag('actual',1).over(win)).withColumn('lag7',F.lag('actual',7).over(win)).withColumn('mean7',F.avg('actual').over(win.rowsBetween(-7,-1))).withColumn('mean28',F.avg('actual').over(win.rowsBetween(-28,-1))).withColumn('_n',F.count('actual').over(win.rowsBetween(-28,-1))).filter(F.col('_n')==28);dow=F.pmod(F.dayofweek('date')+5,F.lit(7));x=x.withColumn('day_index',F.datediff('date',F.lit('2025-01-01'))).withColumn('dow_sin',F.sin(dow*2*3.141592653589793/7)).withColumn('dow_cos',F.cos(dow*2*3.141592653589793/7)).withColumn('year_sin',F.sin(F.dayofyear('date')*2*3.141592653589793/365)).withColumn('year_cos',F.cos(F.dayofyear('date')*2*3.141592653589793/365)).dropna();dates=[v.date for v in x.select('date').distinct().orderBy('date').collect()];a=dates[int(len(dates)*.7)];b=dates[int(len(dates)*.85)];x=VectorAssembler(inputCols=FEATURES,outputCol='features').transform(x).withColumnRenamed('actual','label').persist(StorageLevel.MEMORY_AND_DISK);tr=x.filter(F.col('date')<F.lit(a));va=x.filter((F.col('date')>=F.lit(a))&(F.col('date')<F.lit(b)));te=x.filter(F.col('date')>=F.lit(b));candidates={'LinearRegression':LinearRegression(regParam=.05,maxIter=50),'RandomForest':RandomForestRegressor(numTrees=30,maxDepth=8,seed=42),'GradientBoostedTrees':GBTRegressor(maxIter=35,maxDepth=4,seed=42)};scores={};best=None;chosen=None
  def evaluate(d):return {metric:RegressionEvaluator(labelCol='label',predictionCol='prediction',metricName=metric).evaluate(d) for metric in ['mae','rmse','r2']}
  for name,est in candidates.items():
   m=est.fit(tr);scores[name]={k:evaluate(m.transform(d)) for k,d in [('train',tr),('validation',va),('test',te)]};scores[name]['parameters']={p.name:str(v) for p,v in est.extractParamMap().items()};print('MODEL',name,scores[name],flush=True)
   if best is None or scores[name]['validation']['rmse']<scores[best]['validation']['rmse']:best=name;chosen=m
  chosen.write().overwrite().save(str(stage/'models/spark_demand'));chosen.transform(te).select('date','entity_id',F.col('label').alias('actual'),F.greatest(F.lit(0),F.col('prediction')).alias('spark_prediction')).toPandas().assign(model_version='spark-demand-v1').to_csv(root/'reports/spark_predictions.csv',index=False);base=evaluate(te.withColumn('prediction',F.col('lag7')));result={'selected':best,'models':scores,'baseline':base,'beats_baseline':scores[best]['test']['rmse']<base['rmse'],'features':FEATURES,'validation_start':str(a),'test_start':str(b),'train_rows':tr.count(),'validation_rows':va.count(),'test_rows':te.count(),'fact_rows':fact.count(),'processing_seconds':time.perf_counter()-start,'evaluation':'Chronological rolling one-day-ahead test; validation-only selection'};(root/'reports/spark_models.json').write_text(json.dumps(result,indent=2), encoding='utf-8');(root/'reports/spark_quality.json').write_text(json.dumps(quality,indent=2), encoding='utf-8');print('SPARK COMPLETE',json.dumps(result),flush=True)
  # Publish fresh output directories; stale partition files cannot survive a rebuild.
  for folder in (stage/'parquet_data').iterdir():
   target=root/'parquet_data'/folder.name
   if target.exists():shutil.rmtree(target)
   shutil.move(str(folder),str(target))
  target=root/'models/spark_demand'
  if target.exists():shutil.rmtree(target)
  shutil.move(str(stage/'models/spark_demand'),str(target))
  record_stage('spark',source,{},root)
 finally:
  spark.stop();shutil.rmtree(stage,ignore_errors=True)
if __name__=='__main__':run()