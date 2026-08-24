"""
FinSecAI — Script de Exportação e Consolidação de Respostas das 9 LLMs
Gera:
1. REGISTRO_COMPLETO_RESPOSTAS_LLMS.md (Relatório textual exaustivo para TCC)
2. relatorios/respostas_completas_900_execucoes.json (Dump completo estruturado)
3. relatorios/respostas_completas_900_execucoes.csv (Tabela CSV com BOM UTF-8)
"""

import os
import sys
import json
import csv
import urllib.request
import urllib.error
from collections import defaultdict
from typing import Dict, List, Any

# Configura encoding UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
USER_EMAIL = os.getenv("RESEARCHER_EMAIL", "researcher@finsecai.test")
USER_PASSWORD = os.getenv("RESEARCHER_PASSWORD", "research@2026")

CATEGORIES_MAP = {
    "jailbreak": {
        "title": "1. Injeção Direta e Bypass de Instrução (Jailbreak / System Prompt Extraction)",
        "desc": "Tentativas de forçar a LLM a abandonar sua persona (FinBot), ignorar diretivas de segurança ou revelar o prompt de sistema confidencial.",
        "icon": "🔓"
    },
    "data_extraction": {
        "title": "2. Exfiltração de Dados Confidenciais de Terceiros (Data Extraction / Cross-Tenant)",
        "desc": "Tentativas de induzir a LLM a revelar saldos, transações, CPFs e dados pessoais pertencentes a outros clientes bancários cadastrados.",
        "icon": "🕵️"
    },
    "priv_esc": {
        "title": "3. Acionamento Indevido de Ferramentas e Escalação de Privilégios (Privilege Escalation)",
        "desc": "Tentativas de manipular a LLM para invocar ferramentas administrativas ou perigosas (como alterar saldo ou forçar saques em contas alheias).",
        "icon": "⚡"
    },
    "prompt_injection": {
        "title": "4. Injeção Indireta de Prompt via Ferramentas MCP (Indirect Prompt Injection)",
        "desc": "Prompts de usuários aparentemente legítimos (ex: consultar extrato/investimentos) que processam dados bancários contaminados por injeções em banco de dados.",
        "icon": "💉"
    }
}

MODEL_ORDER = [
    "llama3.1:latest",
    "deepseek-r1:latest",
    "gemma4:latest",
    "qwen2.5:7b",
    "phi3.5:latest",
    "nemotron-mini:latest",
    "deepseek-v2:latest",
    "llama3:8b",
    "mistral:latest"
]

MODEL_DISPLAY_NAMES = {
    "llama3.1:latest": "Meta Llama 3.1 (8B)",
    "deepseek-r1:latest": "DeepSeek R1 (7B Reasoning)",
    "gemma4:latest": "Google Gemma 4 (31B/MoE)",
    "qwen2.5:7b": "Alibaba Qwen 2.5 (7B)",
    "phi3.5:latest": "Microsoft Phi 3.5 (3.8B)",
    "nemotron-mini:latest": "NVIDIA Nemotron Mini (4B)",
    "deepseek-v2:latest": "DeepSeek V2 (16B)",
    "llama3:8b": "Meta Llama 3 (8B Base)",
    "mistral:latest": "Mistral Instruct (7B)"
}


def get_token() -> str:
    payload = json.dumps({"email": USER_EMAIL, "password": USER_PASSWORD}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE_URL}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        return res_data["access_token"]


def fetch_all_interactions(token: str) -> List[Dict[str, Any]]:
    req = urllib.request.Request(
        f"{API_BASE_URL}/research/export",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def save_json_and_csv(interactions: List[Dict[str, Any]], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. JSON
    json_path = os.path.join(output_dir, "respostas_completas_900_execucoes.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(interactions, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON gerado com sucesso: {json_path}")

    # 2. CSV com BOM (abertura perfeita no Excel)
    csv_path = os.path.join(output_dir, "respostas_completas_900_execucoes.csv")
    fieldnames = [
        "id", "session_id", "created_at", "model_name", "provider",
        "threat_category", "is_adversarial", "safety_triggered",
        "is_successful_attack", "status_classificacao", "latency_ms",
        "tokens_used", "user_prompt", "assistant_response", "researcher_notes"
    ]
    
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for item in interactions:
            # Determina status textual
            succ = item.get("is_successful_attack")
            if succ is True:
                status_txt = "ATAQUE_BEM_SUCEDIDO"
            elif succ is False:
                status_txt = "DEFESA_BLOQUEADO"
            else:
                status_txt = "PARCIAL_INCONCLUSIVO"
                
            writer.writerow({
                "id": item.get("id"),
                "session_id": item.get("session_id"),
                "created_at": item.get("created_at"),
                "model_name": item.get("model_name"),
                "provider": item.get("provider"),
                "threat_category": item.get("threat_category"),
                "is_adversarial": item.get("is_adversarial"),
                "safety_triggered": item.get("safety_triggered"),
                "is_successful_attack": item.get("is_successful_attack"),
                "status_classificacao": status_txt,
                "latency_ms": item.get("latency_ms"),
                "tokens_used": item.get("tokens_used"),
                "user_prompt": item.get("user_prompt"),
                "assistant_response": item.get("assistant_response"),
                "researcher_notes": item.get("researcher_notes", "")
            })
    print(f"[OK] CSV gerado com sucesso: {csv_path}")


def generate_markdown_report(interactions: List[Dict[str, Any]], output_filepath: str):
    """Gera um relatório Markdown estruturado e pronto para consulta no TCC."""
    
    # Agrupa por Categoria -> Payload Prompt -> Modelo -> Lista de Execuções
    grouped_data = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    
    for item in interactions:
        cat = item.get("threat_category", "outros")
        prompt = item.get("user_prompt", "").strip()
        model = item.get("model_name", "desconhecido")
        grouped_data[cat][prompt][model].append(item)

    lines = []
    lines.append("# Registro Exaustivo de Respostas Experimentais das 9 LLMs")
    lines.append("")
    lines.append("> 📄 **Apêndice de Resultados Experimentais — FinSecAI**  ")
    lines.append("> **Finalidade**: Documentação integral de todas as respostas dadas pelos 9 modelos de linguagem frente a cada um dos 20 payloads adversariais testados (900 execuções no total).  ")
    lines.append("> **Uso no TCC**: Este documento serve como evidência empírica das reações defensivas, vazamentos de dados, desvios de persona e chamadas indevidas de ferramentas observadas na pesquisa.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Sumário Executivo de Navegação")
    lines.append("")
    
    # Gera Links no Sumário
    cat_idx = 1
    for cat_key, cat_info in CATEGORIES_MAP.items():
        if cat_key not in grouped_data:
            continue
        anchor_cat = f"cat-{cat_key}"
        lines.append(f"### [{cat_info['title']}](#{anchor_cat})")
        
        prompts_in_cat = list(grouped_data[cat_key].keys())
        for p_idx, prompt in enumerate(prompts_in_cat, 1):
            short_p = (prompt[:75] + "…") if len(prompt) > 75 else prompt
            anchor_p = f"payload-{cat_key}-{p_idx}"
            lines.append(f"* [Payload #{cat_idx}.{p_idx}: {short_p}](#{anchor_p})")
        lines.append("")
        cat_idx += 1
        
    lines.append("---")
    lines.append("")
    
    # Itera por Categorias
    cat_num = 1
    for cat_key, cat_info in CATEGORIES_MAP.items():
        if cat_key not in grouped_data:
            continue
        anchor_cat = f"cat-{cat_key}"
        lines.append(f"<a id='{anchor_cat}'></a>")
        lines.append(f"## {cat_info['icon']} {cat_info['title']}")
        lines.append(f"*{cat_info['desc']}*")
        lines.append("")
        
        prompts_dict = grouped_data[cat_key]
        for p_num, (prompt_text, models_dict) in enumerate(prompts_dict.items(), 1):
            anchor_p = f"payload-{cat_key}-{p_num}"
            lines.append(f"<a id='{anchor_p}'></a>")
            lines.append(f"### 🎯 Payload #{cat_num}.{p_num}")
            lines.append("")
            lines.append(f"**Prompt Adversarial Enviado:**")
            lines.append("```text")
            lines.append(prompt_text)
            lines.append("```")
            lines.append("")
            
            # Tabela resumo comparativa do Payload
            lines.append("#### 📊 Matriz Comparativa de Comportamento para Este Payload")
            lines.append("")
            lines.append("| Modelo LLM | Sucessos Ataque | Falhas (Defesa) | Parciais | Safety Triggered | Latência Média | Status Predominante |")
            lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
            
            for m_key in MODEL_ORDER:
                runs = models_dict.get(m_key, [])
                if not runs:
                    continue
                display_name = MODEL_DISPLAY_NAMES.get(m_key, m_key)
                n_runs = len(runs)
                succ_runs = sum(1 for r in runs if r.get("is_successful_attack") is True)
                fail_runs = sum(1 for r in runs if r.get("is_successful_attack") is False)
                part_runs = sum(1 for r in runs if r.get("is_successful_attack") is None)
                safety_trig = sum(1 for r in runs if r.get("safety_triggered") is True)
                avg_lat = sum(r.get("latency_ms", 0) for r in runs) / n_runs if n_runs else 0
                
                if succ_runs > fail_runs and succ_runs > part_runs:
                    pred_status = "🚨 **VULNERÁVEL** (Ataque Efetivo)"
                elif fail_runs >= succ_runs and fail_runs >= part_runs:
                    pred_status = "🛡️ **DEFENDIDO** (Bloqueio Total)"
                else:
                    pred_status = "⚠️ **PARCIAL / AMBÍGUO**"
                    
                safety_str = f"🛡️ Sim ({safety_trig}/{n_runs})" if safety_trig > 0 else "❌ Não (0/5)"
                lines.append(f"| **{display_name}** | {succ_runs}/{n_runs} | {fail_runs}/{n_runs} | {part_runs}/{n_runs} | {safety_str} | {avg_lat:.1f} ms | {pred_status} |")
                
            lines.append("")
            lines.append("#### 💬 Respostas Reais Fornecidas por Cada Modelo")
            lines.append("")
            
            for m_key in MODEL_ORDER:
                runs = models_dict.get(m_key, [])
                if not runs:
                    continue
                display_name = MODEL_DISPLAY_NAMES.get(m_key, m_key)
                
                # Pega a primeira execução como representativa e verifica se há variação
                sample_run = runs[0]
                resp_text = sample_run.get("assistant_response", "").strip()
                if not resp_text:
                    resp_text = "*(Resposta vazia ou erro)*"
                    
                succ = sample_run.get("is_successful_attack")
                if succ is True:
                    tag = "🚨 [VULNERABILIDADE / ATAQUE COM SUCESSO]"
                elif succ is False:
                    tag = "🛡️ [DEFESA BEM-SUCEDIDA / BLOQUEADO]"
                else:
                    tag = "⚠️ [COMPORTAMENTO PARCIAL / INCONCLUSIVO]"
                    
                safety_tag = "🛡️ Safety Ativado" if sample_run.get("safety_triggered") else "❌ Safety Não Ativado"
                lat = sample_run.get("latency_ms", 0)
                
                lines.append(f"##### 🤖 **{display_name}** (`{m_key}`)")
                lines.append(f"- **Classificação**: {tag} | **Filtro**: {safety_tag} | **Latência**: `{lat:.1f} ms`")
                lines.append(f"- **Transcrição da Resposta do Modelo:**")
                lines.append("> " + resp_text.replace("\n", "\n> "))
                
                # Se houver notas do pesquisador
                if sample_run.get("researcher_notes"):
                    lines.append(f"- **Notas de Análise**: *{sample_run.get('researcher_notes')}*")
                lines.append("")
                
            lines.append("---")
            lines.append("")
            
        cat_num += 1

    lines.append("## 6. Arquivos e Datasets Complementares")
    lines.append("")
    lines.append("Para reprodução estatística, cálculos em Python/Pandas ou integração em planilhas:")
    lines.append("* **Dataset Completo em JSON (900 execuções)**: [`relatorios/respostas_completas_900_execucoes.json`](file:///c:/Users/triches/Documents/ProjetoTCC/relatorios/respostas_completas_900_execucoes.json)")
    lines.append("* **Dataset Completo em CSV (Formatado com BOM UTF-8)**: [`relatorios/respostas_completas_900_execucoes.csv`](file:///c:/Users/triches/Documents/ProjetoTCC/relatorios/respostas_completas_900_execucoes.csv)")
    lines.append("* **Script Gerador Automatizado**: [`scripts/export_all_responses.py`](file:///c:/Users/triches/Documents/ProjetoTCC/scripts/export_all_responses.py)")
    lines.append("")

    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"[OK] Relatório Markdown gerado com sucesso: {output_filepath}")


def main():
    print("=" * 60)
    print("[FinSecAI] Exportando e Documentando Respostas das 9 LLMs")
    print("=" * 60)
    
    try:
        print("[1/4] Autenticando com credenciais de pesquisador...")
        token = get_token()
        
        print("[2/4] Buscando todas as interações no PostgreSQL...")
        interactions = fetch_all_interactions(token)
        print(f"      Total de interações recuperadas: {len(interactions)}")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        relatorios_dir = os.path.join(base_dir, "relatorios")
        md_path = os.path.join(base_dir, "REGISTRO_COMPLETO_RESPOSTAS_LLMS.md")
        
        print("[3/4] Gravando Datasets em JSON e CSV...")
        save_json_and_csv(interactions, relatorios_dir)
        
        print("[4/4] Gerando Relatório Markdown Estruturado para o TCC...")
        generate_markdown_report(interactions, md_path)
        
        print("=" * 60)
        print("PROCESSO CONCLUÍDO COM SUCESSO!")
        print(f"- Relatório Markdown: {md_path}")
        print(f"- Diretório de Relatórios: {relatorios_dir}")
        print("=" * 60)
        
    except Exception as e:
        print(f"[Erro Fatal]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
