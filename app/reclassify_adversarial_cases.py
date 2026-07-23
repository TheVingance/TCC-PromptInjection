import asyncio
import sys
import os

# Adiciona o diretório atual ao path do Python para importações relativas funcionarem fora do uvicorn
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.adversarial_case import AdversarialCase
from models.ai_interaction import AIInteraction
from services.ai_service import _classify_adversarial_outcome

async def main():
    print("Iniciando reclassificação de casos adversariais...")
    async with AsyncSessionLocal() as session:
        # Busca todos os casos adversariais associados a uma interação
        stmt = (
            select(AdversarialCase, AIInteraction)
            .join(AIInteraction, AdversarialCase.interaction_id == AIInteraction.id)
        )
        res = await session.execute(stmt)
        rows = res.all()
        
        updated_count = 0
        for case, interaction in rows:
            orig_safety = interaction.safety_triggered
            new_status, new_desc = _classify_adversarial_outcome(
                interaction.threat_category,
                interaction.assistant_response or "",
                orig_safety
            )
            
            # Se o ataque foi bem-sucedido ou parcial, o safety trigger na verdade NÃO foi ativado com sucesso para conter o ataque.
            if new_status is True or new_status is None:
                interaction.safety_triggered = False
            
            if case.is_successful_attack != new_status or case.observed_behavior != new_desc or interaction.safety_triggered != orig_safety:
                print(f"Atualizando caso #{case.id} e interação #{interaction.id} ({interaction.model_name}):")
                print(f"  Categoria: {interaction.threat_category.value}")
                print(f"  Anterior: status={case.is_successful_attack}, safety={orig_safety}, obs={case.observed_behavior}")
                print(f"  Novo: status={new_status}, safety={interaction.safety_triggered}, obs={new_desc}")
                
                case.is_successful_attack = new_status
                case.observed_behavior = new_desc
                updated_count += 1
        
        if updated_count > 0:
            await session.commit()
            print(f"\nReclassificação concluída! {updated_count} registros atualizados com sucesso.")
        else:
            print("\nNenhum registro precisou ser alterado.")

if __name__ == "__main__":
    asyncio.run(main())
