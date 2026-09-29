import os, glob, json, base64, re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# ---- Load GROQ_API_KEY from anywhere Render provides it ----
GROQ_KEY = None
_candidates = []
# 1) Environment variable
if os.environ.get("GROQ_API_KEY"):
    GROQ_KEY = os.environ["GROQ_API_KEY"]
    _candidates.append("env:GROQ_API_KEY")
# 2) Render secret files — check EVERY file in /etc/secrets/ for a key starting with gsk_
if not GROQ_KEY:
    try:
        for sfp in sorted(glob.glob("/etc/secrets/*")):
            try:
                with open(sfp, "r") as f:
                    content = f.read().strip().strip('"').strip("'").strip()
                if content.startswith("gsk_") and len(content) > 20:
                    GROQ_KEY = content
                    _candidates.append(f"file:{sfp}")
                    break
                # also parse as .env style KEY=VALUE
                for line in content.splitlines():
                    m = re.match(r'^\s*(?:GROQ_API_KEY|groq_api_key)\s*=\s*["\']?(gsk_[A-Za-z0-9_\-]+)["\']?\s*$', line.strip())
                    if m:
                        GROQ_KEY = m.group(1)
                        _candidates.append(f"env-in-file:{sfp}")
                        break
            except Exception:
                continue
    except Exception:
        pass
# 3) Local dev fallbacks (workspace)
for lp in ("./groq_key", "../groq_key", ".env", "../.env"):
    if GROQ_KEY: break
    try:
        with open(lp) as f:
            for line in f:
                m = re.match(r'^\s*GROQ_API_KEY\s*=\s*["\']?(gsk_[A-Za-z0-9_\-]+)["\']?\s*$', line.strip())
                if m:
                    GROQ_KEY = m.group(1); _candidates.append(f"local:{lp}"); break
    except Exception:
        pass

AI = bool(GROQ_KEY)

import urllib.request
def groq_chat(system, user, image_b64=None, mime=None, json_mode=False):
    if not GROQ_KEY: return None
    content = [{"type":"text","text":user}]
    if image_b64:
        content.insert(0,{"type":"image_url","image_url":{"url":f"data:{mime or 'image/png'};base64,{image_b64}"}})
    body = {"model":"llama-3.2-11b-vision-preview" if image_b64 else "llama-3.1-8b-instant",
            "messages":[{"role":"system","content":system},{"role":"user","content":content}],
            "temperature":0.2,"max_tokens":2048}
    if json_mode and not image_b64: body["response_format"]={"type":"json_object"}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Authorization":f"Bearer {GROQ_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d=json.loads(r.read())
            return d["choices"][0]["message"]["content"]
    except Exception as e:
        return f"__ERROR__:{e}"

@app.route("/api/health")
def health():
    return jsonify({"status":"ok","ai":AI,"platform":"CyberAce by Ace Dharap",
                    "key_found":AI,"key_source":_candidates[0] if _candidates else None})

@app.route("/api/analyze", methods=["POST"])
def analyze():
    d=request.json or {}
    out=groq_chat(d.get("system","You are a helpful security analyst."),
                  d.get("prompt",""), d.get("image"), d.get("mime"), bool(d.get("json")))
    if out is None: return jsonify({"error":"Groq API not configured. Set GROQ_API_KEY env var or add Render Secret File with key starting gsk_.","result":""})
    if out.startswith("__ERROR__"): return jsonify({"error":out[10:],"result":""})
    return jsonify({"result":out})

# ---- Serve static frontend ----
@app.route("/")
def index(): return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    # security: never serve dotfiles or python source
    if path.startswith(".") or path.endswith(".py"): return ("Not found", 404)
    full = os.path.join(app.static_folder, path)
    if os.path.isfile(full): return send_from_directory(app.static_folder, path)
    # SPA-style fallback for pages/*
    for candidate in (path, f"pages/{path}.html", f"pages/{path}"):
        c = os.path.join(app.static_folder, candidate)
        if os.path.isfile(c): return send_from_directory(app.static_folder, candidate)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"CyberAce starting · AI={'ON' if AI else 'OFF (no key found)'} · sources_tried={_candidates}")
    app.run(host="0.0.0.0", port=port, debug=False)
