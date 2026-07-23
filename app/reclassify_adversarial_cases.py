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
            new_status, new_desc = _classify_adversarial_outcome(
                interaction.threat_category,
                interaction.assistant_response or "",
                interaction.safety_triggered
            )
            
            if case.is_successful_attack != new_status or case.observed_behavior != new_desc:
                print(f"Atualizando caso #{case.id} ({interaction.model_name}):")
                print(f"  Categoria: {interaction.threat_category.value}")
                print(f"  Anterior: status={case.is_successful_attack}, obs={case.observed_behavior}")
                print(f"  Novo: status={new_status}, obs={new_desc}")
                
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
