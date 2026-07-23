import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time
import argparse

# Configura a saída para UTF-8 para evitar erros de encoding no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_BASE_URL = "http://localhost:8000/api/v1"
USER_EMAIL = "researcher@finsecai.test"
USER_PASSWORD = "research@2026"

# Mapeamento: nome do modelo Ollama -> arquivo YAML individual em promptfoo/
MODEL_CONFIG_MAP = {
    "llama3.1:latest":      "promptfoo/llama3.1.yaml",
    "llama3:8b":            "promptfoo/llama3_8b.yaml",
    "deepseek-r1:latest":   "promptfoo/deepseek_r1.yaml",
    "deepseek-v2:latest":   "promptfoo/deepseek_v2.yaml",
    "gemma4:latest":        "promptfoo/gemma4.yaml",
    "nemotron-mini:latest": "promptfoo/nemotron_mini.yaml",
}

# Arquivo padrão (todos os modelos juntos)
ALL_MODELS_CONFIG = "promptfoo.yaml"


def get_token():
    payload = json.dumps({"email": USER_EMAIL, "password": USER_PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE_URL}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["access_token"]
    except Exception as e:
        print(f"Erro ao autenticar: {e}")
        return None

def fetch_metrics(token: str, model_name: Optional[str] = None):
    """Busca métricas de segurança via API backend (geral ou filtrado por modelo)."""
    url = f"{API_BASE_URL}/research/metrics"
    if model_name:
        url += f"?model_name={urllib.parse.quote(model_name)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Erro ao buscar métricas: {e}")
        return None

def run_promptfoo(config_file: str) -> bool:
    """Executa o promptfoo com o arquivo de configuração especificado. Retorna True se sucesso."""
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [npx_cmd, "promptfoo", "eval", "-c", config_file, "--no-cache", "--repeat", "5"]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[Aviso] Promptfoo retornou erro {e.returncode}. Prosseguindo para obter métricas do banco...")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="FinSecAI — Ciclo de Avaliação de Segurança com LLMs locais (Ollama)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modelos disponíveis (--model):\n"
            + "".join(f"  {m}\n" for m in MODEL_CONFIG_MAP.keys())
            + "\nExemplos:\n"
            "  python scripts/run_experiments.py                          # Todos os modelos juntos\n"
            "  python scripts/run_experiments.py --model llama3.1:latest # Apenas Llama 3.1\n"
            "  python scripts/run_experiments.py --model gemma4:31b      # Apenas Gemma 4 31B\n"
        )
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Roda apenas um modelo específico. Se omitido, roda todos os modelos juntos."
    )
    args = parser.parse_args()

    # Seleciona o arquivo de configuração do promptfoo
    if args.model:
        if args.model not in MODEL_CONFIG_MAP:
            available = "\n  ".join(MODEL_CONFIG_MAP.keys())
            print(f"[Erro] Modelo '{args.model}' não reconhecido.")
            print(f"Modelos disponíveis:\n  {available}")
            sys.exit(1)
        config_file = MODEL_CONFIG_MAP[args.model]
        label = f"modelo '{args.model}'"
        total_exec = "100 execuções (20 payloads × 5 repetições)"
    else:
        config_file = ALL_MODELS_CONFIG
        label = "TODOS os modelos"
        total_exec = "execução acumulada de todos os modelos"

    print("=" * 60)
    print("[FinSecAI] Iniciando Ciclo de Avaliação de Segurança...")
    print(f"[Configuração] Executando {label}")
    print(f"[Configuração] {total_exec}")
    print(f"[Configuração] Arquivo promptfoo: {config_file}")
    print("=" * 60)

    start_time = time.time()

    print(f"\n[Execução] Executando Promptfoo ({config_file})...")
    run_promptfoo(config_file)

    duration = time.time() - start_time
    print(f"\nDuração do experimento: {duration:.2f} segundos.")

    # Busca métricas consolidadas do banco de dados relacional
    print("\n[PostgreSQL] Buscando métricas agregadas no banco...")
    token = get_token()
    if not token:
        print("[Erro] Não foi possível buscar as métricas pois a autenticação falhou.")
        return

    metrics = fetch_metrics(token, model_name=args.model)
    if not metrics:
        print("[Erro] Falha ao recuperar as métricas do servidor.")
        return

    print("\n" + "=" * 60)
    print("RESULTADOS CONSOLIDADOS DO EXPERIMENTO (PostgreSQL)")
    print("=" * 60)
    print(f"Total de Interações: {metrics['total_interactions']}")
    print(f"Interações Adversariais: {metrics['adversarial_interactions']}")
    print(f"Mecanismos de Safety Ativados: {metrics['safety_triggered_count']}")
    print(f"Taxa de Ativação do Safety - Safety Refusal Rate (SFR): {metrics['safety_trigger_rate']}%")
    print(f"Casos de Sucesso de Ataques: {metrics['successful_attacks']}")
    print(f"Casos de Defesa com Sucesso (Falha do Ataque): {metrics['failed_attacks']}")
    print("-" * 60)
    print(f"Attack Success Probability (ASP): {metrics['attack_success_probability']:.2f}%")
    print(f"Attack Success Rate (ASR): {metrics['attack_success_rate']:.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
