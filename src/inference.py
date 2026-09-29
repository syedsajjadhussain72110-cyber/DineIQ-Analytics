"""Real independently loaded Python and Spark demand inference."""
import json,time,threading
import joblib
import numpy as np
import pandas as pd
from src.database import ROOT
from python_pipeline.models import FEATURES
LOCK=threading.RLock()
_spark=_sm=_pm=None
_stamps={}

def close_spark():
    global _spark,_sm
    with LOCK:
        if _spark is not None:_spark.stop()
        _spark=_sm=None
        _stamps.pop('spark',None)

def validate(values):
    if not isinstance(values,dict) or set(values)!=set(FEATURES):raise ValueError('All canonical demand features required')
    if any(isinstance(x,bool) for x in values.values()):raise ValueError('Features must be numeric, not boolean')
    v={k:float(values[k]) for k in FEATURES}
    if not all(np.isfinite(x) for x in v.values()) or any(v[k]<0 for k in ['entity_id','lag1','lag7','mean7','mean28']):raise ValueError('Use finite features and non-negative demand')
    if v['entity_id']%1 or v['day_index']%1:raise ValueError('Entity ID and day index must be integers')
    if any(abs(v[k])>1 for k in ['dow_sin','dow_cos','year_sin','year_cos']):raise ValueError('Cyclical features must be between -1 and 1')
    return v

def predict(values,mode='both'):
    global _spark,_sm,_pm
    if mode not in ('python','spark','both'):raise ValueError('Model must be python, spark or both')
    v=validate(values)
    from src.jobs import LOCK as processing_lock
    if not processing_lock.acquire(blocking=False):raise RuntimeError('Processing is running. Wait for completion before live prediction.')
    try:
        with LOCK:
            start=time.perf_counter();out={'mode':mode,'unit':'portions per location-day','features':v}
            if mode in ('python','both'):
                model=ROOT/'models/python_demand.joblib';stamp=model.stat().st_mtime_ns
                cold=_pm is None or _stamps.get('python')!=stamp
                if cold:
                    loaded=joblib.load(model);_pm,_stamps['python']=loaded,stamp
                raw=float(_pm.predict(pd.DataFrame([v],columns=FEATURES))[0])
                if not np.isfinite(raw):raise RuntimeError('Python produced a non-finite prediction')
                out.update(python_prediction=max(0.,raw),python_cold_start=cold,python_version='python-demand-v1')
            if mode in ('spark','both'):
                from src.spark_runtime import configure
                configure()
                from pyspark.sql import SparkSession,types as T
                from pyspark.ml.feature import VectorAssembler
                from pyspark.ml.regression import LinearRegressionModel,RandomForestRegressionModel,GBTRegressionModel
                info=json.loads((ROOT/'reports/spark_models.json').read_text(encoding='utf-8'))
                stamp=(ROOT/'reports/spark_models.json').stat().st_mtime_ns
                cold=_sm is None or _stamps.get('spark')!=stamp
                if cold:
                    try:
                        if _spark is None:
                            _spark=SparkSession.builder.master('local[2]').appName('DineIQ-Inference').config('spark.driver.memory','512m').config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','2').getOrCreate()
                            _spark.sparkContext.setLogLevel('WARN')
                        loaded={'LinearRegression':LinearRegressionModel,'RandomForest':RandomForestRegressionModel,'GradientBoostedTrees':GBTRegressionModel}[info['selected']].load(str(ROOT/'models/spark_demand'))
                        _sm,_stamps['spark']=loaded,stamp
                    except Exception:
                        close_spark();raise
                schema=T.StructType([T.StructField(k,T.DoubleType(),False) for k in FEATURES])
                frame=_spark.createDataFrame([tuple(v[k] for k in FEATURES)],schema)
                assembled=VectorAssembler(inputCols=FEATURES,outputCol='features').transform(frame)
                raw=float(_sm.transform(assembled).select('prediction').first()[0])
                if not np.isfinite(raw):raise RuntimeError('Spark produced a non-finite prediction')
                out.update(spark_prediction=max(0.,raw),spark_cold_start=cold,spark_version='spark-demand-v1',spark_runtime=_spark.version)
            if mode=='both':
                out['difference']=out['spark_prediction']-out['python_prediction']
                out['absolute_difference']=abs(out['difference'])
                out['difference_percent_of_python']=100*abs(out['difference'])/max(out['python_prediction'],1.)
                out['comparison_note']='Same input, independent models. Difference is not accuracy; no actual outcome is supplied.'
            out['elapsed_seconds']=time.perf_counter()-start
            return out
    finally:processing_lock.release()
