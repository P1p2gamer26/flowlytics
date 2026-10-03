from django.conf import settings

MAX_TOKENS = 1200


class LlmClient:
    def __init__(self, api_key=None, model=None):
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        self._model = model or settings.LLM_MODEL

    @property
    def model(self):
        return self._model

    def generate(self, prompt):
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def describir_imagen(self, prompt, jpeg):
        import base64

        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg",
                    "data": base64.b64encode(jpeg).decode()}},
                {"type": "text", "text": prompt},
            ]}],
        )
        return "".join(b.text for b in response.content if b.type == "text")


class FakeLlmClient:
    """Doble para tests: no hace red."""

    def __init__(self, canned="## Qué está funcionando\n- todo bien", model="fake-model"):
        self._canned = canned
        self.model = model
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self._canned

    def describir_imagen(self, prompt, jpeg):
        self.prompts.append(prompt)
        return self._canned
