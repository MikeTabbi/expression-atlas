"""
inference_provider.py — SCAFFOLD (built by Mike, filled in by Zion)

WHY THIS FILE EXISTS
--------------------
Everything in Stage 3 (the narrator, the self-consistency scoring) talks to an
AI model. Today that model runs locally through Ollama. Later, if AWS access
lands, it runs on Amazon Bedrock instead.

If we hardcode Ollama calls all over the codebase, that swap becomes a rewrite.
So: ONE interface, TWO implementations, and nothing else in the project ever
knows which one is running.

    narrator.py  ->  provider.generate(prompt)  ->  [Ollama | Bedrock]

That's the whole idea. The narrator never imports `requests`, never imports
`boto3`, never knows a URL. It just calls .generate().

RULE: no code outside this file should ever mention Ollama or Bedrock.
      If you find yourself importing requests in narrator.py, stop.

SETUP
-----
    ollama pull qwen2.5:7b        # or qwen2.5:3b if RAM is tight
    ollama serve                  # usually already running
    pip install requests

USAGE (once you've filled in the TODOs)
---------------------------------------
    from inference_provider import get_provider

    provider = get_provider()                 # reads config, returns the right one
    text = provider.generate("Say hello.")
    print(text)
"""

from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# CONFIG — the "one flag" that swaps the whole backend
# ---------------------------------------------------------------------------
# Change this string and the entire project switches models. That's the point.
# Later this should read from an env var or a config file instead of being
# hardcoded here.

BACKEND = "ollama"          # "ollama" | "bedrock"
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"


# ===========================================================================
# THE INTERFACE — this is the contract
# ===========================================================================
# Every provider must implement generate(). The rest of the project only ever
# sees this shape. Don't add Ollama-specific or Bedrock-specific methods here —
# anything that only one backend can do doesn't belong in the interface.

class InferenceProvider(ABC):
    """Send a prompt to a model, get text back. That's it."""

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Args:
            prompt:      the full text prompt to send
            temperature: randomness. IMPORTANT for self-consistency —
                         at temperature=0 the model gives the same answer every
                         time, which makes the 5-run agreement check meaningless.
                         You need some variation to detect real uncertainty.
        Returns:
            The model's response as a plain string.
        """
        ...


# ===========================================================================
# ZION'S PART #1 — THE OLLAMA PROVIDER
# ===========================================================================
class OllamaProvider(InferenceProvider):
    """Runs a local model via Ollama. No AWS, no cost, works today."""

    def __init__(self, model: str = OLLAMA_MODEL, url: str = OLLAMA_URL):
        self.model = model
        self.url = url

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        # =================================================================
        # TODO(Zion): POST to the Ollama API and return the response text.
        #
        # Ollama expects JSON like:
        #     {
        #       "model": self.model,
        #       "prompt": prompt,
        #       "stream": False,              <- important, or you get chunks
        #       "options": {"temperature": temperature}
        #     }
        #
        # The response JSON has the text under the key "response".
        #
        # Sketch:
        #     import requests
        #     r = requests.post(self.url, json={...}, timeout=120)
        #     r.raise_for_status()
        #     return r.json()["response"]
        #
        # Handle the obvious failure: if Ollama isn't running, requests will
        # throw a ConnectionError. Catch it and raise something readable —
        # "Ollama isn't running, try `ollama serve`" beats a raw stack trace,
        # especially when Mike or a teammate hits it.
        #
        # The 7B on an M2 can be slow. Set a generous timeout (120s) — and
        # remember self-consistency calls this 5x per gene, so a slow model
        # means a slow demo. Worth timing one call early.
        # =================================================================
        raise NotImplementedError("Zion: implement the Ollama POST")


# ===========================================================================
# ZION'S PART #2 — THE BEDROCK PROVIDER (stub it now, finish it if access lands)
# ===========================================================================
class BedrockProvider(InferenceProvider):
    """
    Runs Claude on Amazon Bedrock. We may never get access — that's fine.
    Stub it now so the swap is real and not hypothetical, and so the poster
    claim ("one config flag from Bedrock") is honest.
    """

    def __init__(self, model_id: str = "anthropic.claude-sonnet-4-5-20250929-v1:0",
                 region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        # =================================================================
        # TODO(Zion): only build this out if/when AWS access lands.
        #
        # Sketch:
        #     import boto3, json
        #     client = boto3.client("bedrock-runtime", region_name=self.region)
        #     body = {
        #         "anthropic_version": "bedrock-2023-05-31",
        #         "max_tokens": 1000,
        #         "temperature": temperature,
        #         "messages": [{"role": "user", "content": prompt}],
        #     }
        #     resp = client.invoke_model(modelId=self.model_id, body=json.dumps(body))
        #     payload = json.loads(resp["body"].read())
        #     return payload["content"][0]["text"]
        #
        # Note the shape differs from Ollama's — different request format,
        # different response key. That difference is EXACTLY what this class
        # exists to hide. Everything above this line returns a plain string,
        # so the narrator can't tell the two apart.
        # =================================================================
        raise NotImplementedError("Bedrock: implement if/when AWS access lands")


# ===========================================================================
# THE FACTORY — everything else in the project calls this, not the classes
# ===========================================================================
def get_provider() -> InferenceProvider:
    """
    Return the configured provider. The narrator calls this and never thinks
    about backends again.
    """
    # ===================================================================
    # TODO(Zion): return the right provider based on BACKEND.
    #   if BACKEND == "ollama":  return OllamaProvider()
    #   if BACKEND == "bedrock": return BedrockProvider()
    #   else: raise ValueError(f"Unknown backend: {BACKEND}")
    # ===================================================================
    raise NotImplementedError("Zion: implement the factory")


# ===========================================================================
# SMOKE TEST — run `python inference_provider.py` to check your wiring
# ===========================================================================
if __name__ == "__main__":
    provider = get_provider()
    print(f"Backend: {BACKEND}")
    print("-" * 50)

    reply = provider.generate("In one sentence: what does qPCR measure?")
    print(reply)

    # TODO(Zion): once this prints a sensible sentence, the wrapper is done.
    #
    # Then try calling generate() 5 times with the SAME prompt and print all 5.
    # If they're identical, your temperature is too low and self-consistency
    # won't work. If they vary but all say roughly the same thing, that's
    # exactly the signal the certainty score is built on.
    #
    # That little experiment IS the seed of Stage 3. Do it before you build
    # anything else.
