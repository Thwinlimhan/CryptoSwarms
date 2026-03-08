from cryptoswarms.wallet_isolation import AgentWalletProfile, validate_wallet_isolation


def test_wallet_isolation_detects_duplicates_and_main_wallet():
    ok, errors = validate_wallet_isolation(
        [
            AgentWalletProfile(agent_name="execution", key_env="EXEC_KEY", secret_env="EXEC_SECRET"),
            AgentWalletProfile(agent_name="risk", key_env="EXEC_KEY", secret_env="MAIN_WALLET_SECRET"),
        ]
    )

    assert ok is False
    assert len(errors) >= 2
