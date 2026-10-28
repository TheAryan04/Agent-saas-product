import json, os, sys, time
import requests
sys.path.insert(0, "/app/backend/tests")
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
from test_frameforge_contracts import OUTPUTS

base = sys.argv[1] if len(sys.argv) > 1 else os.environ["REACT_APP_BACKEND_URL"]
bad = dict(OUTPUTS, Designer={"primaryColor": "#007BFF", "accentColor": "#FF5733", "background": "#343A40", "font": "Sora"})
t0 = time.time(); ntok = 0; first = None; last = None
with requests.post(f"{base}/api/pipeline/stream", json={"prompt": "A 10 second launch film for Nimbus, a calm note-taking app", "fast_mode": True}, stream=True, timeout=300) as r:
    print("status", r.status_code, r.headers.get("content-type"))
    try:
        for l in r.iter_lines(decode_unicode=True):
            if not l or not l.startswith("data: "):
                continue
            e = json.loads(l[6:]); t = round(time.time() - t0, 1)
            if e["type"] == "token":
                ntok += 1; first = first or t; last = t
            else:
                print(t, json.dumps(e)[:1500])
    except Exception as ex:
        print("STREAM EXC", round(time.time() - t0, 1), ex)
print("tokens", ntok, "first", first, "last", last, "total", round(time.time() - t0, 1))
