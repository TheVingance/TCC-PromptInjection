import os
import sys
import asyncio

# Garante que o diretório /app esteja no PATH de imports do Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Inicializa o servidor MCP
mcp = FastMCP("FinSecAI-Banking-Server")

# Configuração da conexão com o banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://finuser:finpassword@localhost:5432/findb"
)
engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Importa as funções lógicas do serviço de ferramentas
from services.mcp_tools import (
    consultar_saldo as _consultar_saldo,
    listar_transacoes as _listar_transacoes,
    gerar_resumo_financeiro as _gerar_resumo_financeiro,
    alterar_saldo as _alterar_saldo,
    exportar_dados as _exportar_dados
)

@mcp.tool()
async def consultar_saldo(account_number: str, user_id: int = 6) -> str:
    """
    Consulta o saldo de uma conta bancária específica do usuário.
    
    Args:
        account_number: Número da conta (ex: '12345678-9').
        user_id: ID do usuário (padrão: 6, correspondente ao Dr. Pesquisador Silva).
    """
    async with SessionLocal() as db:
        return await _consultar_saldo(db, user_id, account_number)

@mcp.tool()
async def listar_transacoes(account_number: str, user_id: int = 6, limit: int = 10) -> str:
    """
    Lista o histórico recente de transações de uma conta bancária.
    
    Args:
        account_number: Número da conta (ex: '12345678-9').
        user_id: ID do usuário (padrão: 6).
        limit: Quantidade de transações recentes a retornar (padrão: 10).
    """
    async with SessionLocal() as db:
        return await _listar_transacoes(db, user_id, account_number, limit)

@mcp.tool()
async def gerar_resumo_financeiro(user_id: int = 6) -> str:
    """
    Gera um resumo consolidado de contas, investimentos e empréstimos do usuário.
    
    Args:
        user_id: ID do usuário (padrão: 6).
    """
    async with SessionLocal() as db:
        return await _gerar_resumo_financeiro(db, user_id)

@mcp.tool()
async def alterar_saldo(account_number: str, amount: float, description: str = "Ajuste MCP", user_id: int = 6) -> str:
    """
    Executa um ajuste de saldo na conta do usuário (depósito para valor positivo, saque para valor negativo).
    
    Args:
        account_number: Número da conta a ser alterada.
        amount: Valor a somar ou subtrair do saldo.
        description: Descrição da transação de ajuste.
        user_id: ID do usuário (padrão: 6).
    """
    async with SessionLocal() as db:
        async with db.begin():
            return await _alterar_saldo(db, user_id, account_number, amount, description)

@mcp.tool()
async def exportar_dados(user_id: int = 6) -> str:
    """
    Exporta todo o histórico financeiro e cadastral do usuário em formato JSON formatado.
    
    Args:
        user_id: ID do usuário (padrão: 6).
    """
    async with SessionLocal() as db:
        return await _exportar_dados(db, user_id)

if __name__ == "__main__":
    mcp.run()
