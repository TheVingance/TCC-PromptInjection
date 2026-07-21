import urllib.request
import urllib.error
import json
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
USER_EMAIL = os.getenv("RESEARCHER_EMAIL", "researcher@finsecai.test")
USER_PASSWORD = os.getenv("RESEARCHER_PASSWORD", "research@2026")

cached_token = None


def get_token(force_refresh: bool = False):
    """Obtém um token JWT. Se force_refresh=True, descarta o cache e autentica de novo."""
    global cached_token
    if cached_token and not force_refresh:
        return cached_token

    url = f"{API_BASE_URL}/auth/login"
    payload = json.dumps({
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            cached_token = res_data["access_token"]
            return cached_token
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Failed to authenticate: {e.code} - {body}")
    except Exception as e:
        raise RuntimeError(f"Connection error during authentication: {str(e)}")


def _build_request(prompt: str, config: dict, token: str, vars_dict: dict) -> urllib.request.Request:
    """Monta o objeto Request para o endpoint /ai/chat."""
    provider = config.get("provider", "gemini")
    model_name = config.get("model_name", None)
    is_adversarial = config.get("is_adversarial", True)
    threat_category = vars_dict.get("category") or config.get("threat_category", "prompt_injection")

    payload_dict = {
        "message": prompt,
        "provider": provider,
        "is_adversarial": is_adversarial,
        "threat_category": threat_category
    }
    if model_name:
        payload_dict["model_name"] = model_name

    payload = json.dumps(payload_dict).encode("utf-8")

    return urllib.request.Request(
        f"{API_BASE_URL}/ai/chat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )


def call_api(prompt, options, context):
    config = options.get("config", {})
    vars_dict = context.get("vars", {}) if isinstance(context, dict) else {}

    # Tenta até 2 vezes: na primeira usa o token cacheado;
    # se vier 401 (token expirado), força re-autenticação e tenta mais uma vez.
    for attempt in range(2):
        try:
            force_refresh = (attempt == 1)  # Na segunda tentativa, força novo token
            token = get_token(force_refresh=force_refresh)
            req = _build_request(prompt, config, token, vars_dict)

            with urllib.request.urlopen(req, timeout=180) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return {
                    "output": res_data.get("response", "")
                }

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            if e.code == 401 and attempt == 0:
                # Token expirado — descarta cache e tenta novamente
                global cached_token
                cached_token = None
                continue
            return {
                "error": f"API HTTP Error {e.code}: {body}"
            }
        except Exception as e:
            return {
                "error": f"Error: {str(e)}"
            }

    return {"error": "Falha após re-autenticação: token inválido persistente."}
