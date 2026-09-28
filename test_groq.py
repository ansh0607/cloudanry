from backend.core.config import get_settings
import httpx, asyncio

s = get_settings()

async def test():
    headers = {"Authorization": f"Bearer {s.groq_api_key}", "Content-Type": "application/json"}
    models = [s.groq_model_supporting, s.groq_model_vision, s.groq_model_adversarial]
    for model in models:
        payload = {"model": model, "messages": [{"role": "user", "content": "Say hello in 3 words"}], "max_tokens": 20}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{s.groq_base_url}/chat/completions", headers=headers, json=payload)
            if r.status_code == 200:
                d = r.json()
                reply = d["choices"][0]["message"]["content"]
                tokens = d["usage"]["completion_tokens"]
                print(f"  PASS [{model}] -> {repr(reply)} ({tokens} tokens)")
            else:
                err = r.json()
                msg = err.get("error", {}).get("message", r.text)[:120]
                print(f"  FAIL [{model}] -> {r.status_code}: {msg}")

asyncio.run(test())
