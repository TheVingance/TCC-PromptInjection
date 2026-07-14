import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

# Configura a saída para UTF-8 para evitar erros de encoding no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_BASE_URL = "http://localhost:8000/api/v1"
USER_EMAIL = "researcher@finsecai.test"
USER_PASSWORD = "research@2026"

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

def fetch_metrics(token):
    req = urllib.request.Request(
        f"{API_BASE_URL}/research/metrics",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Erro ao buscar métricas: {e}")
        return None

def main():
    print("[FinSecAI] Iniciando Ciclo de Avaliação de Segurança...")
    print("[Configuracao] 20 payloads adversariais x 5 repeticoes cada = 100 execucoes.")
    
    start_time = time.time()
    
    # Executa o promptfoo
    print("[Execucao] Executando Promptfoo no shell...")
    cmd = ["npx.cmd" if os.name == "nt" else "npx", "promptfoo", "eval", "-c", "promptfoo.yaml", "--no-cache", "--repeat", "5"]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n[Sucesso] Avaliação automatizada do Promptfoo finalizada!")
    except subprocess.CalledProcessError as e:
        print(f"\n[Aviso] Promptfoo retornou erro {e.returncode}. Prosseguindo para obter métricas do banco...")
    
    duration = time.time() - start_time
    print(f"Duração do experimento: {duration:.2f} segundos.")
    
    # Busca métricas consolidadas do banco de dados relacional
    print("[PostgreSQL] Buscando métricas agregadas no banco...")
    token = get_token()
    if not token:
        print("[Erro] Não foi possível buscar as métricas pois a autenticação falhou.")
        return
        
    metrics = fetch_metrics(token)
    if not metrics:
        print("[Erro] Falha ao recuperar as métricas do servidor.")
        return
        
    print("\n" + "="*50)
    print("RESULTADOS CONSOLIDADOS DO EXPERIMENTO (PostgreSQL)")
    print("="*50)
    print(f"Total de Interações: {metrics['total_interactions']}")
    print(f"Interações Adversariais: {metrics['adversarial_interactions']}")
    print(f"Mecanismos de Safety Ativados: {metrics['safety_triggered_count']}")
    print(f"Taxa de Ativação do Safety (SFR): {metrics['safety_trigger_rate']}%")
    print(f"Casos de Invasão de Sucesso: {metrics['successful_attacks']}")
    print(f"Casos de Defesa de Sucesso (Falha do Ataque): {metrics['failed_attacks']}")
    print("-"*50)
    print(f"Attack Success Probability (ASP): {metrics['attack_success_probability']:.2f}%")
    print(f"Attack Success Rate (ASR): {metrics['attack_success_rate']:.2f}%")
    print("="*50)

if __name__ == "__main__":
    main()
