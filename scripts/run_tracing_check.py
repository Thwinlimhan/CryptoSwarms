from __future__ import annotations

from cryptoswarms.tracing_deploy import evaluate_tracing_deployment


def main() -> None:
    status = evaluate_tracing_deployment()
    print({
        "langsmith_ready": status.langsmith_ready,
        "deepflow_reachable": status.deepflow_reachable,
    })


if __name__ == "__main__":
    main()
