"""Controlled local comparisons; these are not historic production measurements."""
import argparse
import json
import platform
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx
import numpy as np
from backend.app.model import ModelService
from backend.app.schema import Transaction
from backend.ml.train import ARTIFACT_DIR, generate_data


def summary(values):
    return {"median_ms":float(np.median(values)), "p95_ms":float(np.percentile(values,95)), "samples":len(values)}


def timed(fn):
    start=time.perf_counter(); result=fn()
    return (time.perf_counter()-start)*1000, result


def main(url=None):
    frame,_ = generate_data(100, seed=77)
    txs = [Transaction.model_validate(row) for row in frame.to_dict('records')]
    service = ModelService(ARTIFACT_DIR)
    service.predict(txs)
    cold, warm, preprocessing, inference = [], [], [], []
    for i in range(150):
        tx=txs[i%len(txs)]
        elapsed, baseline = timed(lambda: ModelService(ARTIFACT_DIR).predict([tx]))
        cold.append(elapsed)
        elapsed, current = timed(lambda: service.predict([tx]))
        warm.append(elapsed)
        assert np.allclose([r['risk_score'] for r in baseline['results']],[r['risk_score'] for r in current['results']],rtol=0,atol=1e-12)
        preprocessing.append(current['timings']['preprocessing_ms'])
        inference.append(current['timings']['inference_ms'])
    per_row, vectorized = [], []
    for _ in range(15):
        elapsed, row_results = timed(lambda: [service.predict([tx])['results'][0] for tx in txs])
        per_row.append(elapsed)
        elapsed, batch = timed(lambda: service.predict(txs))
        vectorized.append(elapsed)
        assert np.allclose([r['risk_score'] for r in row_results],[r['risk_score'] for r in batch['results']],rtol=0,atol=1e-12)
    report={"conditions":{"platform":platform.platform(),"python":platform.python_version(),"model_version":service.metadata['model_version'],"transport":"in-process unless http_local included", "note":"Controlled baseline comparisons, not measurements of an earlier application. OS file cache is warm; no deployed cold start measured."},
            "reload_each_call":summary(cold), "startup_cached":summary(warm), "preprocessing":summary(preprocessing), "inference":summary(inference),
            "100_individual_calls":summary(per_row), "100_vectorized":summary(vectorized)}
    if url:
        with httpx.Client(base_url=url,timeout=60) as client:
            client.post('/api/predict',json=txs[0].model_dump()).raise_for_status()
            rounds, server, overhead = [], [], []
            for tx in txs[:50]:
                elapsed,response=timed(lambda: client.post('/api/predict',json=tx.model_dump()))
                response.raise_for_status()
                duration=float(response.headers['x-request-time-ms'])
                rounds.append(elapsed);server.append(duration);overhead.append(max(0,elapsed-duration))
            report['http_local']={"client_round_trip":summary(rounds),"server_processing":summary(server),"transport_client_overhead":summary(overhead)}
            def one(tx):
                elapsed,response=timed(lambda:client.post('/api/predict',json=tx.model_dump()))
                response.raise_for_status()
                return elapsed
            with ThreadPoolExecutor(max_workers=4) as pool:
                report['http_concurrent_4_workers']=summary(list(pool.map(one,txs[:16])))
    Path('reports').mkdir(exist_ok=True)
    Path('reports/benchmark.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url');args=parser.parse_args();main(args.url)
