from agents.research.progressive_loader import ProgressiveSkillLoader
from agents.research.research_factory import KnowledgeDocument
from agents.research.skill_hub import SkillHub


def test_progressive_loader_respects_budget_and_scores():
    docs = [
        KnowledgeDocument("d1", "Kelly Sizing", "paper", ("kelly risk sizing confidence edge " * 20).strip(), ("kelly", "risk")),
        KnowledgeDocument("d2", "Unrelated", "paper", ("weather sports music " * 20).strip(), ("misc",)),
    ]
    loader = ProgressiveSkillLoader(token_budget=120)
    out = loader.load(query="kelly risk", documents=docs)

    assert out
    assert out[0].doc_id == "d1"
    assert sum(x.token_estimate for x in out) <= 120


def test_skill_hub_lifecycle_and_audit_flow():
    hub = SkillHub()
    created = hub.create_skill(skill_id="s1", name="risk-playbook", content="api_key=abc", actor="research_agent")
    assert "[REDACTED]" in created.content

    patched = hub.patch_skill(skill_id="s1", patch_text="add kelly", actor="research_agent")
    edited = hub.edit_skill(skill_id="s1", new_content="clean content", actor="research_agent")
    pending = hub.submit_to_hub(skill_id="s1", actor="research_agent")
    approved = hub.approve_skill(skill_id="s1", actor="governor_agent")

    assert patched.version == 2
    assert edited.version == 3
    assert pending.status == "pending_review"
    assert approved.status == "approved"
    assert len(hub.audit_events("s1")) == 5
