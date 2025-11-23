from flask import Flask, request, jsonify
import os
import time
import logging

try:
    from google import genai
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
DEV_MOCK = os.environ.get("DEV_MOCK", "0") == "1"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.0")
MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "3"))


@app.route("/health", methods=["GET"])
def health():
    mode = 'mock'
    if not DEV_MOCK and HAS_GENAI and GOOGLE_API_KEY:
        mode = 'gemini'
    return jsonify({"status": "ok", "mode": mode})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "'prompt' field required"}), 400

    max_tokens = int(data.get("max_tokens", 512))
    temperature = float(data.get("temperature", 0.2))

    # Fast path: mock mode
    if DEV_MOCK or not (HAS_GENAI and GOOGLE_API_KEY):
        logger.info("Returning MOCK analysis (DEV_MOCK or Gemini not available)")
        short = prompt[:200].replace('\n', ' ')
        return jsonify({"analysis": f"MOCK ANALYSIS: resumen breve para prompt: {short}"})

    # Configure client (best-effort; actual SDK usage may vary)
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.debug("genai.configure() failed (continuing): %s", e)

    attempts = 0
    last_exc = None
    while attempts < MAX_RETRIES:
        attempts += 1
        try:
            # Attempt a generation call. SDKs differ; we try a common pattern and fall back gracefully.
            resp = genai.generate_text(model=MODEL, prompt=prompt, max_output_tokens=max_tokens, temperature=temperature)

            # Extract text from different possible response shapes
            text = None
            if hasattr(resp, 'text'):
                text = resp.text
            elif isinstance(resp, dict):
                # new-style responses sometimes contain 'candidates' or 'output'
                if 'candidates' in resp and resp['candidates']:
                    text = resp['candidates'][0].get('content')
                elif 'output' in resp:
                    out = resp['output']
                    if isinstance(out, list) and out:
                        # list of items with 'content'
                        for item in out:
                            if isinstance(item, dict) and 'content' in item:
                                text = item['content']
                                break
                    else:
                        text = str(out)
            else:
                text = str(resp)

            text = (text or '').strip()
            if not text:
                raise ValueError('Empty response from Gemini')

            return jsonify({"analysis": text, "model": MODEL})
        except Exception as e:
            logger.warning("Gemini call failed (attempt %d/%d): %s", attempts, MAX_RETRIES, e)
            last_exc = e
            time.sleep(2 ** attempts)

    logger.error("Gemini unavailable after %d attempts: %s", MAX_RETRIES, last_exc)
    return jsonify({"error": "gemini_unavailable", "details": str(last_exc)}), 503


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))
    app.run(host='0.0.0.0', port=port)
