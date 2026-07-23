"""Initial migration — all tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("cpf", sa.String(14), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_number", sa.String(20), unique=True, nullable=False, index=True),
        sa.Column("agency", sa.String(10), nullable=False, server_default="0001"),
        sa.Column("account_type", sa.Enum("checking", "savings", "investment", name="accounttype"), nullable=False),
        sa.Column("balance", sa.Numeric(15, 2), default=0.00),
        sa.Column("status", sa.Enum("active", "frozen", "closed", name="accountstatus"), default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("to_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("transaction_type", sa.Enum("deposit", "withdrawal", "transfer", "pix", "fee", "interest", name="transactiontype"), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.Enum("pending", "completed", "failed", "reversed", name="transactionstatus"), default="completed"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Investments
    op.create_table(
        "investments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("investment_type", sa.Enum("stocks", "bonds", "funds", "crypto", "real_estate", name="investmenttype"), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("quantity", sa.Numeric(15, 6), nullable=False),
        sa.Column("average_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("current_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Loans
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("interest_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("monthly_payment", sa.Numeric(15, 2), nullable=True),
        sa.Column("outstanding_balance", sa.Numeric(15, 2), nullable=True),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", "active", "paid", "defaulted", name="loanstatus"), default="pending"),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(50), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # AI Interactions
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(50), nullable=False, index=True),
        sa.Column("provider", sa.Enum("ollama", "deepseek", "gemini", name="llmprovider"), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("assistant_response", sa.Text(), nullable=True),
        sa.Column("threat_category", sa.Enum("none", "jailbreak", "social_eng", "data_extraction", "priv_esc", "financial_fraud", "prompt_injection", "misinformation", "other", name="threatcategory"), default="none"),
        sa.Column("is_adversarial", sa.Boolean(), default=False),
        sa.Column("safety_triggered", sa.Boolean(), default=False),
        sa.Column("researcher_notes", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Adversarial Cases
    op.create_table(
        "adversarial_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True, index=True),
        sa.Column("attack_vector", sa.String(100), nullable=False),
        sa.Column("severity", sa.Enum("low", "medium", "high", "critical", name="caseseverity"), default="medium"),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("observed_behavior", sa.Text(), nullable=True),
        sa.Column("is_successful_attack", sa.Boolean(), nullable=True),
        sa.Column("mitigation_notes", sa.Text(), nullable=True),
        sa.Column("interaction_id", sa.Integer(), sa.ForeignKey("ai_interactions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("adversarial_cases")
    op.drop_table("ai_interactions")
    op.drop_table("audit_logs")
    op.drop_table("loans")
    op.drop_table("investments")
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("users")
