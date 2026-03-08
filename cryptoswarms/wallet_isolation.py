from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentWalletProfile:
    agent_name: str
    key_env: str
    secret_env: str
    passphrase_env: str | None = None


MAIN_WALLET_ENV_NAMES = {"MAIN_WALLET_KEY", "MAIN_WALLET_SECRET", "MASTER_PRIVATE_KEY"}


def validate_wallet_isolation(profiles: list[AgentWalletProfile]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    seen: set[str] = set()

    for profile in profiles:
        key_name = profile.key_env.strip().upper()
        secret_name = profile.secret_env.strip().upper()

        if key_name in MAIN_WALLET_ENV_NAMES or secret_name in MAIN_WALLET_ENV_NAMES:
            errors.append(f"{profile.agent_name} references forbidden main-wallet env")

        if key_name in seen:
            errors.append(f"duplicate key env detected: {key_name}")
        if secret_name in seen:
            errors.append(f"duplicate secret env detected: {secret_name}")

        seen.add(key_name)
        seen.add(secret_name)

    return (len(errors) == 0, errors)
