from cryptoswarms.tracing_deploy import evaluate_tracing_deployment


def test_evaluate_tracing_deployment_langsmith_flags():
    status = evaluate_tracing_deployment(
        {
            "LANGCHAIN_TRACING_V2": "true",
            "LANGCHAIN_API_KEY": "k",
            "LANGCHAIN_PROJECT": "p",
            "DEEPFLOW_HOST": "127.0.0.1",
            "DEEPFLOW_PORT": "9",
        }
    )
    assert status.langsmith_ready is True


def test_evaluate_tracing_deployment_missing_langsmith_flags():
    status = evaluate_tracing_deployment(
        {
            "LANGCHAIN_TRACING_V2": "false",
            "LANGCHAIN_API_KEY": "",
            "LANGCHAIN_PROJECT": "",
            "DEEPFLOW_HOST": "127.0.0.1",
            "DEEPFLOW_PORT": "9",
        }
    )
    assert status.langsmith_ready is False
