import csv
import io
from concurrent.futures import ThreadPoolExecutor
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.model import ModelService
from backend.app.schema import FEATURES, Transaction
from backend.ml.train import train

LOW = {"amount": 15.0, "hour": 14, "transactions_24h": 1, "distance_km": 1.0,
       "account_age_days": 1000, "international": False, "new_device": False, "merchant_category": "grocery"}
HIGH = {**LOW, "amount": 5000.0, "hour": 2, "transactions_24h": 18, "distance_km": 2000.0, "account_age_days": 10, "international": True, "new_device": True, "merchant_category": "transfer"}


@pytest.fixture(scope="session")
def artifacts(tmp_path_factory):
    directory = tmp_path_factory.mktemp("trained")
    train(directory, rows=8000)
    return directory


@pytest.fixture
def client(artifacts):
    with TestClient(create_app(artifacts, rate_limit=10000)) as client:
        yield client


def csv_body(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FEATURES)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: str(v).lower() if isinstance(v, bool) else v for k,v in row.items()})
    return stream.getvalue()


def test_health_metadata_and_schema(client):
    assert client.get("/health").json() == {"status":"ready", "model_ready":True}
    meta = client.get("/api/model").json()
    assert meta["features"] == FEATURES
    assert list(meta["input_schema"]["properties"]) == FEATURES
    assert sum(meta["split"].values()) == 8000
    assert set(meta["metrics"]) == {"precision","recall","f1","roc_auc","average_precision","confusion_matrix"}


def test_real_prediction_matches_saved_pipeline(client, artifacts):
    service = ModelService(artifacts)
    response = client.post("/api/predict", json=LOW)
    assert response.status_code == 200
    data = response.json()
    actual = service.pipeline.predict_proba(pd.DataFrame([LOW], columns=FEATURES))[0,1]
    assert data["result"]["risk_score"] == pytest.approx(actual, abs=1e-12)
    assert data["result"]["prediction"] == ("fraud" if actual >= service.metadata["threshold"] else "legitimate")
    assert data["result"]["dataset_kind"] == "synthetic"
    assert all(x >= 0 for x in data["timings"].values())
    assert "x-request-time-ms" in response.headers
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_synthetic_risk_order_and_batch_consistency(client):
    low = client.post("/api/predict", json=LOW).json()["result"]
    high = client.post("/api/predict", json=HIGH).json()["result"]
    assert low["risk_score"] < high["risk_score"]
    batch = client.post("/api/predict/batch", json={"transactions":[LOW,HIGH]})
    assert batch.status_code == 200
    assert [r["risk_score"] for r in batch.json()["results"]] == pytest.approx([low["risk_score"], high["risk_score"]], abs=1e-12)


@pytest.mark.parametrize("change", [{"amount":-1}, {"amount":1_000_001}, {"hour":24}, {"hour":2.5}, {"hour":"2"}, {"transactions_24h":0}, {"distance_km":20001}, {"account_age_days":-1}, {"international":"false"}, {"new_device":1}, {"merchant_category":"unknown"}, {"extra":"sensitive-value"}, {"amount":None}])
def test_invalid_fields(client, change):
    response = client.post("/api/predict", json={**LOW, **change})
    assert response.status_code == 422
    assert "sensitive-value" not in response.text
    assert response.json()["error"]["code"] == "invalid_input"


def test_missing_fields_and_malformed_json(client):
    assert client.post("/api/predict",json={}).status_code == 422
    assert client.post("/api/predict",content='{bad',headers={"Content-Type":"application/json"}).status_code == 422


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_numbers(client,value):
    import json
    payload = json.dumps(LOW).replace('15.0',value)
    assert client.post("/api/predict",content=payload,headers={"Content-Type":"application/json"}).status_code == 422


@pytest.mark.parametrize("rows", [[], [LOW]*101])
def test_batch_bounds(client,rows):
    assert client.post("/api/predict/batch",json={"transactions":rows}).status_code == 422


def test_csv_matches_json(client):
    csv_response = client.post("/api/predict/csv",content=csv_body([LOW,HIGH]),headers={"Content-Type":"text/csv"})
    assert csv_response.status_code == 200
    expected = client.post("/api/predict/batch",json={"transactions":[LOW,HIGH]}).json()
    assert csv_response.json()["results"] == expected["results"]


@pytest.mark.parametrize("body", ["", ",".join(FEATURES), "amount,hour\n1,2", "amount,amount\n1,2", csv_body([LOW]*101), csv_body([{**LOW,"amount":"=1+1"}]), csv_body([{**LOW,"new_device":"yes"}]), csv_body([LOW]).replace(',14,',',14.5,'), csv_body([LOW]).replace(',grocery',',grocery,extra'), '\xff'])
def test_invalid_csv(client,body):
    assert client.post("/api/predict/csv",content=body,headers={"Content-Type":"text/csv"}).status_code == 422


def test_upload_limits_and_content_type(client):
    oversized = client.post("/api/predict/csv",content='x'*131073,headers={"Content-Type":"text/csv"})
    assert oversized.status_code == 413
    assert oversized.headers['x-content-type-options'] == 'nosniff'
    assert 'x-request-time-ms' in oversized.headers
    assert client.post("/api/predict/csv",content=csv_body([LOW]),headers={"Content-Type":"application/octet-stream"}).status_code == 415
    # No Content-Length: limits must also apply to chunked bodies.
    response = client.post("/api/predict/csv",content=iter([b'x'*70000,b'x'*70000]),headers={"Content-Type":"text/csv"})
    assert response.status_code == 413


def test_missing_model_degrades_without_training(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/health").status_code == 503
        response = client.post("/api/predict",json=LOW)
        assert response.status_code == 503
        assert str(tmp_path) not in response.text
        assert not list(tmp_path.iterdir())


def test_corrupt_and_incompatible_model(tmp_path,artifacts):
    (tmp_path/'model.joblib').write_bytes(b'invalid')
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/health').status_code == 503
    artifact = joblib.load(artifacts/'model.joblib')
    artifact['metadata']['features'] = list(reversed(FEATURES))
    joblib.dump(artifact,tmp_path/'model.joblib')
    with pytest.raises(ValueError,match='schema mismatch'):
        ModelService(tmp_path)


def test_model_loaded_once(artifacts,monkeypatch):
    import backend.app.main as main
    original = main.ModelService
    calls = []
    def factory(directory):
        calls.append(directory)
        return original(directory)
    monkeypatch.setattr(main,'ModelService',factory)
    with TestClient(main.create_app(artifacts)) as client:
        for _ in range(3):
            assert client.post('/api/predict',json=LOW).status_code == 200
    assert len(calls) == 1


def test_cors(client):
    headers = {'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
    assert client.options('/api/predict',headers=headers).headers['access-control-allow-origin'] == 'http://localhost:5173'
    headers['Origin'] = 'https://untrusted.example'
    assert client.options('/api/predict',headers=headers).status_code == 400
    response = client.post('/api/predict',json=LOW,headers={'Origin':headers['Origin']})
    assert 'access-control-allow-origin' not in response.headers


def test_production_cors_explicit_origin(artifacts,monkeypatch):
    monkeypatch.setenv('CORS_ORIGINS','https://safepay.example')
    with TestClient(create_app(artifacts)) as client:
        response = client.get('/health',headers={'Origin':'https://safepay.example'})
        assert response.headers['access-control-allow-origin'] == 'https://safepay.example'
    monkeypatch.setenv('CORS_ORIGINS','*')
    with pytest.raises(ValueError,match='explicit origins'):
        create_app(artifacts)


def test_rate_limit(artifacts):
    with TestClient(create_app(artifacts,rate_limit=2)) as client:
        for _ in range(2):
            assert client.post('/api/predict',json=LOW).status_code == 200
        assert client.post('/api/predict',json=LOW).status_code == 429
        assert client.get('/health').status_code == 200


def test_concurrent_inference(client):
    def one(_):
        response = client.post('/api/predict',json=HIGH)
        assert response.status_code == 200
        return response.json()['result']['risk_score']
    with ThreadPoolExecutor(max_workers=4) as pool:
        scores = list(pool.map(one, range(16)))
    assert np.allclose(scores,scores[0],rtol=0,atol=1e-12)


def test_unexpected_inference_error_is_sanitized(client,monkeypatch):
    def fail(transactions):
        raise RuntimeError('private-artifact-path-and-payload')
    monkeypatch.setattr(client.app.state.model,'predict',fail)
    response=client.post('/api/predict',json=LOW)
    assert response.status_code == 500
    assert 'private-artifact-path-and-payload' not in response.text
    assert response.json()['error']['code'] == 'internal_error'
