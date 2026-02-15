import os
import json

import requests


class BlackboardService:
    DEFAULT_BASE_URL = "https://app.backboard.io/api"

    def __init__(self):
        self.api_key = os.getenv("BLACKBOARD_API_KEY") or os.getenv("BACKBOARD_API_KEY")
        if not self.api_key:
            raise ValueError("BLACKBOARD_API_KEY or BACKBOARD_API_KEY is not set.")
        self.base_url = (
            os.getenv("BACKBOARD_API_BASE_URL")
            or os.getenv("BLACKBOARD_API_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")

    def _candidate_base_urls(self) -> list[str]:
        bases = {self.base_url.rstrip("/")}
        base = self.base_url.rstrip("/")

        if "app.backboard.io" in base:
            bases.add(base.replace("app.backboard.io", "api.backboard.io"))

        if base.endswith("/api"):
            bases.add(base[: -len("/api")])
        else:
            bases.add(f"{base}/api")

        expanded = set()
        for item in bases:
            clean = item.rstrip("/")
            expanded.add(clean)
            if "app.backboard.io" in clean:
                expanded.add(clean.replace("app.backboard.io", "api.backboard.io"))

        return sorted(expanded)

    def _model_endpoints(self) -> list[str]:
        endpoints = []
        for base in self._candidate_base_urls():
            endpoints.extend(
                [
                    f"{base}/models",
                    f"{base}/v1/models",
                    f"{base}/models/all",
                    f"{base}/api/models",
                    f"{base}/api/models/all",
                ]
            )
        return sorted(set(endpoints))

    def _chat_endpoints(self) -> list[str]:
        generic = (
            os.getenv("BACKBOARD_INFERENCE_URL")
            or os.getenv("BLACKBOARD_INFERENCE_URL")
            or ""
        ).strip()
        if generic and ("chat" in generic and "completions" in generic):
            if generic.startswith("http://") or generic.startswith("https://"):
                return [generic.rstrip("/")]
            return [f"{self.base_url}/{generic.lstrip('/')}"]

        configured = (
            os.getenv("BACKBOARD_CHAT_COMPLETIONS_URL")
            or os.getenv("BLACKBOARD_CHAT_COMPLETIONS_URL")
            or ""
        ).strip()
        if configured:
            if configured.startswith("http://") or configured.startswith("https://"):
                return [configured.rstrip("/")]
            return [f"{self.base_url}/{configured.lstrip('/')}"]

        candidates = []
        for base in self._candidate_base_urls():
            candidates.extend([f"{base}/chat/completions", f"{base}/v1/chat/completions"])
        return sorted(set(candidates))

    def _response_endpoints(self) -> list[str]:
        candidates = []
        for base in self._candidate_base_urls():
            candidates.extend([f"{base}/responses", f"{base}/v1/responses"])
        return sorted(set(candidates))

    def _completion_endpoints(self) -> list[str]:
        candidates = []
        for base in self._candidate_base_urls():
            candidates.extend([f"{base}/completions", f"{base}/v1/completions"])
        return sorted(set(candidates))

    def _stateful_chat_endpoints(self) -> list[str]:
        generic = (
            os.getenv("BACKBOARD_INFERENCE_URL")
            or os.getenv("BLACKBOARD_INFERENCE_URL")
            or ""
        ).strip()
        if generic and "chat" in generic and "completions" not in generic:
            if generic.startswith("http://") or generic.startswith("https://"):
                return [generic.rstrip("/")]
            return [f"{self.base_url}/{generic.lstrip('/')}"]

        configured = (
            os.getenv("BACKBOARD_STATEFUL_CHAT_URL")
            or os.getenv("BLACKBOARD_STATEFUL_CHAT_URL")
            or ""
        ).strip()
        if configured:
            if configured.startswith("http://") or configured.startswith("https://"):
                return [configured.rstrip("/")]
            return [f"{self.base_url}/{configured.lstrip('/')}"]

        candidates = []
        for base in self._candidate_base_urls():
            candidates.extend([f"{base}/v1/chat", f"{base}/chat"])
        return sorted(set(candidates))

    def _header_variants(self) -> list[dict]:
        return [
            {"x-api-key": self.api_key, "Content-Type": "application/json"},
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        ]

    def _assistant_headers(self) -> dict:
        return {"X-API-Key": self.api_key}

    def _assistant_endpoint(self) -> str:
        return f"{self.base_url}/assistants"

    def _assistant_thread_endpoint(self, assistant_id: str) -> str:
        return f"{self.base_url}/assistants/{assistant_id}/threads"

    def _thread_messages_endpoint(self, thread_id: str) -> str:
        return f"{self.base_url}/threads/{thread_id}/messages"

    def _fetch_models(self) -> list[dict]:
        last_error = None
        for endpoint in self._model_endpoints():
            for headers in self._header_variants():
                try:
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    if isinstance(data, list):
                        return [m for m in data if isinstance(m, dict)]
                    if isinstance(data, dict):
                        for key in ("models", "data", "items", "results"):
                            value = data.get(key)
                            if isinstance(value, list):
                                return [m for m in value if isinstance(m, dict)]
                except Exception as exc:
                    last_error = exc
                    continue
        if last_error:
            raise last_error
        return []

    def _pick_model_id(self, models: list[dict]) -> str:
        preferred = (
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet-latest",
            "gemini-1.5-flash",
        )
        model_ids = [str(m.get("id") or "").strip() for m in models if m.get("id")]
        for pref in preferred:
            if pref in model_ids:
                return pref
        return model_ids[0] if model_ids else "gpt-4o-mini"

    def _resolve_model_id(self, models: list[dict], requested_model: str | None = None) -> str:
        if requested_model:
            request_clean = requested_model.strip()
            available = {str(m.get("id") or "").strip() for m in models if m.get("id")}
            if request_clean in available:
                return request_clean
        return self._pick_model_id(models)

    def _extract_text(self, response_json: dict) -> str:
        choices = response_json.get("choices", []) if isinstance(response_json, dict) else []
        if not choices:
            return ""
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            chunks = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
            return "\n".join(chunks).strip()
        return ""

    def _extract_response_text(self, response_json: dict) -> str:
        if not isinstance(response_json, dict):
            return ""

        output_text = response_json.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = response_json.get("output", [])
        if isinstance(output, list):
            chunks = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content", [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            chunks.append(part["text"])
            if chunks:
                return "\n".join(chunks).strip()

        return ""

    def _extract_stateful_chat_text(self, response_json: dict) -> str:
        if not isinstance(response_json, dict):
            return ""

        candidates = [
            response_json.get("response"),
            response_json.get("content"),
            response_json.get("output"),
            response_json.get("message"),
            response_json.get("text"),
        ]
        data_node = response_json.get("data")
        if isinstance(data_node, dict):
            candidates.extend(
                [
                    data_node.get("response"),
                    data_node.get("content"),
                    data_node.get("output"),
                    data_node.get("message"),
                    data_node.get("text"),
                ]
            )
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()

        messages = response_json.get("messages")
        if isinstance(messages, list) and messages:
            last = messages[-1]
            if isinstance(last, dict):
                text = last.get("content") or last.get("text")
                if isinstance(text, str):
                    return text.strip()
        return ""

    def _extract_json(self, text: str) -> dict:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    def get_user_profile(self) -> dict:
        models = self._fetch_models()
        providers = sorted({m.get("provider") for m in models if isinstance(m, dict) and m.get("provider")})
        return {
            "name": "Backboard API Key",
            "email": "Not provided by API key endpoint",
            "profile_info": {
                "api_base_url": self.base_url,
                "models_count": len(models),
                "providers": providers,
            },
        }

    def list_models(self) -> list[dict]:
        try:
            models = self._fetch_models()
            result = []
            for item in models:
                model_id = str(item.get("id") or item.get("model") or item.get("model_name") or "").strip()
                if not model_id:
                    continue
                result.append(
                    {
                        "id": model_id,
                        "provider": str(item.get("provider") or item.get("vendor") or "").strip(),
                        "name": str(item.get("name") or model_id),
                    }
                )
            if result:
                return result
        except Exception:
            pass

        # Assistant API flow does not require explicit model selection.
        return [{"id": "assistant-default", "provider": "backboard", "name": "Assistant Default"}]

    def _invoke_assistant_api(
        self,
        prompt: str,
        system_prompt: str,
        requested_model: str | None = None,
    ) -> dict:
        headers = self._assistant_headers()

        assistant_payload = {
            "name": "FinPrint Assistant",
            "system_prompt": system_prompt,
        }
        if requested_model and requested_model != "assistant-default":
            assistant_payload["model"] = requested_model

        assistant_resp = requests.post(
            self._assistant_endpoint(),
            json=assistant_payload,
            headers=headers,
            timeout=20,
        )
        # Some accounts may reject explicit model in assistant creation.
        if assistant_resp.status_code >= 400 and "model" in assistant_payload:
            assistant_payload.pop("model", None)
            assistant_resp = requests.post(
                self._assistant_endpoint(),
                json=assistant_payload,
                headers=headers,
                timeout=20,
            )
        assistant_resp.raise_for_status()
        assistant_data = assistant_resp.json()
        assistant_id = str(assistant_data.get("assistant_id") or assistant_data.get("id") or "").strip()
        if not assistant_id:
            raise ValueError("Assistant creation succeeded but no assistant_id was returned.")

        thread_resp = requests.post(
            self._assistant_thread_endpoint(assistant_id),
            json={},
            headers=headers,
            timeout=20,
        )
        thread_resp.raise_for_status()
        thread_data = thread_resp.json()
        thread_id = str(thread_data.get("thread_id") or thread_data.get("id") or "").strip()
        if not thread_id:
            raise ValueError("Thread creation succeeded but no thread_id was returned.")

        msg_resp = requests.post(
            self._thread_messages_endpoint(thread_id),
            headers=headers,
            data={"content": prompt, "stream": "false"},
            timeout=25,
        )
        msg_resp.raise_for_status()
        msg_data = msg_resp.json()

        text = ""
        for key in ("content", "response", "message", "text"):
            value = msg_data.get(key) if isinstance(msg_data, dict) else None
            if isinstance(value, str) and value.strip():
                text = value.strip()
                break

        if not text and isinstance(msg_data, dict):
            messages = msg_data.get("messages")
            if isinstance(messages, list) and messages:
                last = messages[-1]
                if isinstance(last, dict):
                    maybe = last.get("content") or last.get("text")
                    if isinstance(maybe, str):
                        text = maybe.strip()

        if not text:
            raise ValueError("Assistant message endpoint returned empty content.")

        return {"text": text, "model": requested_model or "assistant-default"}

    def _invoke_text(self, prompt: str, requested_model: str | None = None) -> dict:
        model_id = requested_model or "assistant-default"
        try:
            models = self._fetch_models()
            model_id = self._resolve_model_id(models, requested_model)
        except Exception:
            model_id = requested_model or "assistant-default"

        # Preferred integration based on Backboard docs (assistants -> threads -> messages).
        try:
            return self._invoke_assistant_api(
                prompt=prompt,
                system_prompt="You are a helpful financial assistant.",
                requested_model=model_id,
            )
        except Exception:
            pass

        request_payload = {
            "model": model_id,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        responses_payload = {
            "model": model_id,
            "temperature": 0.2,
            "input": prompt,
        }
        completions_payload = {
            "model": model_id,
            "prompt": prompt,
            "temperature": 0.2,
        }
        stateful_chat_payload = {
            "model_name": model_id,
            "memory": "Auto",
            "send_to_llm": "true",
            "web_search": "off",
            "content": prompt,
        }

        last_error = None
        candidates = []
        candidates.extend([("stateful_chat", endpoint) for endpoint in self._stateful_chat_endpoints()])
        candidates.extend([("chat", endpoint) for endpoint in self._chat_endpoints()])
        candidates.extend([("responses", endpoint) for endpoint in self._response_endpoints()])
        candidates.extend([("completions", endpoint) for endpoint in self._completion_endpoints()])

        for kind, endpoint in candidates:
            for url in (endpoint, f"{endpoint}/"):
                for headers in self._header_variants():
                    try:
                        if kind == "stateful_chat":
                            stateful_headers = dict(headers)
                            stateful_headers.pop("Content-Type", None)
                            multipart_payload = {k: (None, str(v)) for k, v in stateful_chat_payload.items()}
                            response = requests.post(
                                url,
                                headers=stateful_headers,
                                files=multipart_payload,
                                timeout=20,
                            )
                        elif kind == "responses":
                            response = requests.post(url, headers=headers, json=responses_payload, timeout=20)
                        elif kind == "completions":
                            response = requests.post(url, headers=headers, json=completions_payload, timeout=20)
                        else:
                            response = requests.post(url, headers=headers, json=request_payload, timeout=20)
                        response.raise_for_status()
                        data = None
                        text = ""
                        try:
                            data = response.json()
                        except ValueError:
                            text = (response.text or "").strip()

                        if data is not None:
                            if kind == "stateful_chat":
                                text = self._extract_stateful_chat_text(data)
                            elif kind == "responses":
                                text = self._extract_response_text(data)
                            else:
                                text = self._extract_text(data)
                        if not text.strip():
                            raise ValueError("Model returned empty response.")
                        return {"text": text, "model": model_id}
                    except Exception as exc:
                        last_error = exc
                        continue

        if last_error:
            raise RuntimeError(
                f"Unable to reach a Backboard inference endpoint. Tried: "
                f"{', '.join(self._stateful_chat_endpoints() + self._chat_endpoints() + self._response_endpoints() + self._completion_endpoints())}. "
                f"Last error: {last_error}"
            )
        raise RuntimeError("Unable to generate output from Blackboard.")

    def generate_money_dna_stats(self, payload: dict, requested_model: str | None = None) -> dict:
        prompt = (
            "You are a financial insights engine. Based on the provided JSON input, "
            "return ONLY valid JSON with keys: ai_narrative (string), "
            "comparisons (array of up to 4 strings), recommendations (array of up to 3 strings). "
            "Each recommendation must include a concrete monthly savings estimate in dollars when possible. "
            "Input JSON: "
            f"{json.dumps(payload, ensure_ascii=True)}"
        )
        generated = self._invoke_text(prompt, requested_model=requested_model)
        parsed = self._extract_json(generated["text"])
        if not isinstance(parsed, dict):
            raise ValueError("Blackboard response did not return JSON object.")

        return {
            "ai_narrative": str(parsed.get("ai_narrative") or "").strip(),
            "comparisons": [
                str(item).strip() for item in (parsed.get("comparisons") or []) if str(item).strip()
            ][:4],
            "recommendations": [
                str(item).strip() for item in (parsed.get("recommendations") or []) if str(item).strip()
            ][:3],
            "model": generated.get("model") or "",
        }

    def generate_financial_coach_reply(
        self,
        conversation: list[dict],
        context_payload: dict,
        requested_model: str | None = None,
    ) -> dict:
        prompt = (
            "You are a concise financial coach. Use the context JSON and conversation to provide practical "
            "weekly actions, spending cautions, and one measurable target for the next 7 days.\n"
            "Context JSON:\n"
            f"{json.dumps(context_payload, ensure_ascii=True)}\n"
            "Conversation JSON:\n"
            f"{json.dumps(conversation, ensure_ascii=True)}"
        )
        generated = self._invoke_text(prompt, requested_model=requested_model)
        return {"reply": generated["text"], "model": generated.get("model") or ""}

    def run_prompt(self, prompt: str, requested_model: str | None = None) -> dict:
        generated = self._invoke_text(prompt, requested_model=requested_model)
        return {"output": generated["text"], "model": generated.get("model") or ""}
