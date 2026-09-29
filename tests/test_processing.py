"""Real integration tests. Rebuilds the supplied dataset; no mocked Spark results."""
import json,time,sys
import numpy as np
import pandas as pd
import pytest
from src.app import create_app
from src.database import ROOT

@pytest.fixture(scope='module')
def pipeline(tmp_path_factory):
    assert sys.version_info[:2]==(3,12),'Validate using Python 3.12'
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path_factory.mktemp('pipeline')/'jobs.db'),'SECRET_KEY':'test-only'})
    client=app.test_client();client.get('/login')
    with client.session_transaction() as s:csrf=s['csrf']
    assert client.post('/login',data={'csrf':csrf,'username':'admin','password':'DineIQ-Demo-2026!'}).status_code==302
    with client.session_transaction() as s:csrf=s['csrf']
    headers={'X-CSRF-Token':csrf};results={}
    for kind in ['python','spark','compare','generate']:
        response=client.post('/api/jobs',json={'kind':kind,'horizon':30},headers=headers)
        assert response.status_code==202,response.get_json()
        job_id=response.get_json()['id'];deadline=time.monotonic()+1800
        while True:
            job=next(x for x in client.get('/api/jobs').get_json() if x['id']==job_id)
            if job['status']!='running':break
            assert time.monotonic()<deadline,f'{kind} timed out'
            time.sleep(.5)
        assert job['status']=='completed',job
        assert job['finished_at'] and 'exit 0' in job['details'];results[kind]=job
    yield client,headers,results
    from src.inference import close_spark
    close_spark()

@pytest.mark.parametrize('kind',['python','spark','compare','generate'])
def test_processing_center_real_execution(pipeline,kind):
    from src.workflow import verify_stage
    assert pipeline[2][kind]['status']=='completed';assert len(verify_stage(kind)['outputs'])==64

def test_generated_report_download(pipeline):
    client=pipeline[0];pdf=client.get('/api/generated/report')
    assert pdf.status_code==200;assert pdf.data.startswith(b'%PDF-');assert len(pdf.data)>2000
    result=client.get('/api/generated/json').get_json();assert result['comparison']['cases']>=100;assert result['summary']['orders']>100000
    assert client.get('/api/generated/comparison').status_code==200;assert client.get('/api/generated/not-a-file').status_code==404

@pytest.mark.parametrize('mode',['python','spark','both'])
def test_real_live_prediction(pipeline,mode):
    client,headers,_=pipeline;v=client.get('/api/predict/example').get_json()
    response=client.post('/api/predict',json={'mode':mode,'features':v},headers=headers)
    assert response.status_code==200,response.get_json()
    data=response.get_json();assert data['mode']==mode
    for name in ['python','spark']:
        if mode in (name,'both'):
            assert np.isfinite(data[name+'_prediction']);assert data[name+'_prediction']>=0
            predictions=pd.read_csv(ROOT/f'reports/{name}_predictions.csv')
            date=(pd.Timestamp('2025-01-01')+pd.Timedelta(days=v['day_index'])).date().isoformat()
            expected=predictions[(predictions.entity_id==v['entity_id'])&(predictions.date==date)].iloc[0][name+'_prediction']
            assert data[name+'_prediction']==pytest.approx(expected,rel=1e-7)
        else:assert name+'_prediction' not in data
    if mode=='both':
        assert data['difference']==pytest.approx(data['spark_prediction']-data['python_prediction'])
        assert data['absolute_difference']==pytest.approx(abs(data['difference']))
    if mode!='python':assert data['spark_runtime']=='3.5.3'

def test_comparison_complete_and_equivalent(pipeline):
    d=pd.read_csv(ROOT/'reports/comparison.csv');a=pd.read_csv(ROOT/'reports/python_predictions.csv');b=pd.read_csv(ROOT/'reports/spark_predictions.csv')
    assert len(d)==len(a)==len(b);assert np.allclose(d.actual_python,d.actual_spark);assert np.allclose(d.difference,d.spark_prediction-d.python_prediction)
    assert d.match.equals(d.relative_difference<=json.loads((ROOT/'reports/comparison.json').read_text(encoding='utf-8'))['tolerance'])

@pytest.mark.parametrize('payload',[[],{'mode':'invalid','features':{}},{'mode':'both','features':{'bad':1}}])
def test_prediction_invalid_payload(pipeline,payload):
    assert pipeline[0].post('/api/predict',json=payload,headers=pipeline[1]).status_code==400

def test_prediction_busy_is_meaningful(pipeline):
    from src.jobs import LOCK
    client,headers,_=pipeline;v=client.get('/api/predict/example').get_json()
    with LOCK:response=client.post('/api/predict',json={'features':v,'mode':'both'},headers=headers)
    assert response.status_code==503;assert 'Processing is running' in response.get_json()['error']

def test_missing_prerequisites_cannot_complete(tmp_path):
    from src.workflow import requirements
    with pytest.raises(ValueError,match='Run Python'):requirements('compare',tmp_path)
    with pytest.raises(ValueError,match='Run Compare'):requirements('generate',tmp_path)

def test_unknown_job_rejected(tmp_path):
    from src.jobs import start
    with pytest.raises(ValueError,match='Unknown named job'):start('shell',dbpath=tmp_path/'jobs.db')

def test_utf8_and_controls_preserved():
    js=(ROOT/'static/app.js').read_text(encoding='utf-8')
    for control in ['predict-python','predict-spark','predict-now','data-job','workspace-btn','notification-btn','setupGlobalSearch']:assert control in js