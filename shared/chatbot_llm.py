"""Optional, bounded paraphrasing via a configured Chat Completions endpoint."""
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

PROMPT_PATH = Path(__file__).resolve().parents[1] / "chatbot-service/prompts/system_prompt.txt"


def configuration():
    """Missing/invalid settings leave the deterministic assistant available."""
    endpoint = os.getenv("LLM_API_URL", "").strip()
    key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    if not (endpoint and key and model):
        return None
    try:
        url = urlparse(endpoint)
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.port not in (None, 443)
                or any(char.isspace() for char in endpoint)
                or not math.isfinite(timeout) or not 1 <= timeout <= 15):
            return None
    except ValueError:
        return None
    return endpoint, key, model, timeout


def numeric_facts(value):
    # Normalize separators but do not accept shorthand such as 100k for 100.000.
    return {re.sub(r"\D", "", token) for token in re.findall(r"\d+(?:[.,:/-]\d+)*", value)}


def rewrite_answer(question, matches):
    """Return a validated paraphrase or None; never change business state."""
    settings = configuration()
    if not settings or not matches:
        return None
    endpoint, key, model, timeout = settings
    effort = os.getenv("LLM_REASONING_EFFORT", "").strip()
    if effort and effort not in {"none", "minimal", "low", "medium", "high", "xhigh", "max"}:
        return None
    sources = [{"id": f"{item['source']}:{item['source_id']}",
                "source": item["source"], "source_title": item["source_title"],
                "answer": item["answer"]} for item in matches[:5]]
    # Avoid truncating away an exception/condition halfway through a source.
    if any(len(item["answer"]) > 6000 for item in sources):
        return None
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8").format(
            today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat())
        payload = {"model": model, "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(
                    {"question": question, "sources": sources}, ensure_ascii=False)}],
                   "response_format": {"type": "json_object"}, "max_completion_tokens": 800}
        if effort:
            payload["reasoning_effort"] = effort
        response = requests.post(
            endpoint, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, json=payload,
            timeout=(3, timeout), allow_redirects=False)
        if response.status_code != 200:
            return None
        result = response.json()
        choice = result["choices"][0]
        if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
            return None
        content = choice["message"]["content"]
        if not isinstance(content, str) or len(content) > 12000:
            return None
        parsed = json.loads(content)
        answer, citations = parsed["answer"], parsed["source_ids"]
        if (not isinstance(answer, str) or not answer.strip() or len(answer) > 6000
                or not isinstance(citations, list) or not citations
                or any(not isinstance(item, str) for item in citations)):
            return None
        known = {item["id"]: item for item in sources}
        if any(item not in known for item in citations):
            return None
        grounding = "\n".join(known[item]["answer"] for item in citations)
        if not numeric_facts(answer).issubset(numeric_facts(grounding)):
            return None
        # The UI is plain text; links or tags are never needed for paraphrasing.
        if re.search(r"https?://|www\.|<[^>]+>", answer, re.I) or key in answer:
            return None
        return {"answer": answer.strip(), "source_ids": list(dict.fromkeys(citations))}
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, OSError):
        # Do not log provider bodies, question text, authorization or keys.
        return None
