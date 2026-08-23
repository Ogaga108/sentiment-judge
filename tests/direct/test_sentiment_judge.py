import json

CONTRACT = "contracts/sentiment_judge.py"


def _mock_positive(direct_vm):
    direct_vm.mock_llm(
        r"Analyze the sentiment",
        json.dumps({"label": "positive", "score": 82, "confidence": 91, "reasoning": "very upbeat"}),
    )


def _mock_negative(direct_vm):
    direct_vm.mock_llm(
        r"Analyze the sentiment",
        json.dumps({"label": "negative", "score": -70, "confidence": 88, "reasoning": "complaint"}),
    )


def test_analyze_positive(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _mock_positive(direct_vm)

    result = contract.analyze("This product is absolutely amazing, I love it!")

    assert result["label"] == "positive"
    assert result["score"] == 82
    assert result["key"]


def test_analyze_negative(direct_vm, direct_deploy, direct_bob):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_bob
    _mock_negative(direct_vm)

    result = contract.analyze("Terrible service, everything arrived broken.")

    assert result["label"] == "negative"
    assert result["score"] == -70


def test_result_is_persisted(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _mock_positive(direct_vm)

    analyzed = contract.analyze("What a wonderful day to ship code")
    stored = contract.get_result("What a wonderful day to ship code")

    assert stored["exists"] is True
    assert stored["label"] == analyzed["label"]
    assert stored["score"] == analyzed["score"]


def test_unknown_text_returns_not_exists(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)

    stored = contract.get_result("never analyzed before")

    assert stored["exists"] is False


def test_stats_counts_analyses(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    _mock_positive(direct_vm)

    contract.analyze("good good good")
    contract.analyze("great great great")

    assert contract.stats()["total_analyses"] == 2


def test_rejects_short_text(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("text too short"):
        contract.analyze("ok")


def test_rejects_oversized_text(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("text too long"):
        contract.analyze("x" * 8001)
