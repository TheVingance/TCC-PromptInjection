1. Como validar você mesmo cada teste e visualizar como a LLM reage?
Você tem duas formas complementares para fazer isso:

Opção A: Interface Web do Pesquisador (Tempo Real)
Acesse o painel web em http://localhost:3000 e faça login como pesquisador (researcher@finsecai.test / research@2026).
Digite ou cole qualquer payload adversarial na caixa de chat (ou utilize os botões da lateral esquerda).
Selecione o modelo local do Ollama no dropdown e marque a caixa Modo Adversarial (isso configurará a flag is_adversarial = True e salvará no banco).
Envie o prompt e veja instantaneamente na tela se o FinBot exibiu o badge 🛡️ SAFETY TRIGGERED (indicando defesa) ou se respondeu normalmente.
No painel direito de Histórico, filtre pela aba "⚠️ Adversariais" e clique no item que acabou de criar. Um modal detalhado abrirá contendo o input completo, a resposta bruta da LLM, categoria do ataque, latência e tokens.
Opção B: Interface Interativa do Promptfoo (Visão em Matriz)
Para visualizar a reação detalhada do modelo em lote para os 100 testes:

Certifique-se de ter rodado o script automatizado (python scripts/run_experiments.py).
No seu terminal (diretório do projeto), execute:
bash
npx promptfoo view
Isso iniciará um servidor web local e abrirá uma aba no seu navegador (geralmente em http://localhost:15000).
Lá você verá uma matriz interativa comparativa com todos os 20 payloads e as 5 repetições de cada um.
Você pode clicar em cada uma das células da tabela para expandir e ler a resposta bruta exata que o Llama 3.1 gerou para aquela tentativa, junto com o status da asserção de segurança.
2. De que forma o frontend permite averiguar os payloads de cada categoria de ataque?
O frontend foi projetado especificamente para atuar como uma central de auditoria de testes de TCC:

Chaveamento de Histórico Adversarial: O painel de histórico possui dois filtros no topo: "Todos" e "⚠️ Adversariais". Ao clicar em "⚠️ Adversariais", a interface busca no banco apenas as interações com ataques e oculta consultas normais.
Inspeção Detalhada por Modal: Ao clicar em qualquer interação da lista, a interface abre uma janela flutuante de auditoria (Modal) que recupera os metadados do PostgreSQL. Nele, você averigua:
Prompt do Usuário: O payload exato disparado.
Resposta do Assistente: O texto de reação da LLM.
Threat Category: A categoria científica atribuída (ex: jailbreak, data_extraction, priv_esc, prompt_injection).
Safety Triggered: Indicador visual imediato (✅ SIM / ❌ NÃO) se a defesa contra injeção foi bem-sucedida.
Cards Estatísticos: No painel superior de métricas, você pode conferir o ASR e o ASP calculados sob demanda pelo backend, proporcionando a consolidação estatística por categoria de ataque de forma direta.