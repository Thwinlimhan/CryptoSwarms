from agents.research.stack_profiles import recommended_stack_profiles


def test_recommended_stack_profiles_are_priority_sorted():
    profiles = recommended_stack_profiles()
    priorities = [p.priority for p in profiles]
    assert priorities == sorted(priorities)


def test_recommended_stack_profiles_include_core_references():
    profiles = recommended_stack_profiles()
    names = {p.name for p in profiles}

    assert "autoresearch" in names
    assert "RD-Agent" in names
    assert "OpenBB Workspace" in names
    assert "Freqtrade" in names
    assert "QuantConnect Lean" in names
