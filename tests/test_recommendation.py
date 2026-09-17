# tests/test_recommendation.py
import pytest
from app.config import settings
from app.models import ProjectExtraction, Requirement, TeamRecommendation
from app.services.recommendation import recommend_team, _match_signal


def make_extraction(
    project_name="Test Project",
    summary="A test project summary of sufficient length for validation.",
    requirements=None,
    confidence=0.9,
):
    if requirements is None:
        requirements = [
            Requirement(description="Build user login interface", priority="high")
        ]
    return ProjectExtraction(
        project_name=project_name,
        summary=summary,
        requirements=requirements,
        confidence=confidence,
    )


# ============================================================================
# 1. Word Boundary Signal Matching Unit Tests
# ============================================================================


def test_match_signal_word_boundaries():
    # 'ai' should match isolated 'AI' but NOT 'email', 'chair', 'detail', 'main'
    assert _match_signal("ai", "We need an AI model for prediction") is True
    assert _match_signal("ai", "Send confirmation email to user") is False
    assert _match_signal("ai", "Chair the meeting with detail") is False

    # 'react' should match 'React' but NOT 'reactionary'
    assert _match_signal("react", "Build with React framework") is True
    assert _match_signal("react", "A reactionary approach") is False

    # multi-word signals
    assert _match_signal("machine learning", "Deploy a machine learning pipeline") is True
    assert _match_signal("machine learning", "Machine maintenance learning") is False


# ============================================================================
# 2. Strong AI/ML Project
# ============================================================================


def test_strong_ai_ml_project():
    """Strong AI/ML signals -> AI/ML recommended with high confidence (>= 0.80)"""
    ext = make_extraction(
        project_name="LLM Document Assistant",
        summary="A generative AI assistant leveraging RAG, deep learning, and machine learning models.",
        requirements=[
            Requirement(description="Implement RAG architecture for document retrieval", priority="high"),
            Requirement(description="Fine-tune machine learning model embeddings", priority="high"),
            Requirement(description="Integrate computer vision and deep learning models", priority="medium"),
            Requirement(description="Deploy model training and inference pipeline", priority="high"),
        ],
    )

    rec = recommend_team(ext)
    assert rec.team == "AI / ML"
    assert rec.recommended_team == "AI / ML"
    assert rec.confidence >= 0.80
    assert rec.requires_human_review is False
    assert any("machine learning" in r.lower() or "rag" in r.lower() for r in rec.reasoning)


# ============================================================================
# 3. Strong Web Development Project
# ============================================================================


def test_strong_web_project():
    """Strong Web signals -> Web Development recommended with high confidence"""
    ext = make_extraction(
        project_name="Customer Portal Dashboard",
        summary="Customer portal with responsive frontend, React dashboard, and FastAPI backend.",
        requirements=[
            Requirement(description="Build interactive React frontend dashboard", priority="high"),
            Requirement(description="Implement FastAPI backend REST API", priority="high"),
            Requirement(description="Design responsive HTML website layout with TypeScript", priority="medium"),
            Requirement(description="Develop fullstack user management portal", priority="high"),
        ],
    )

    rec = recommend_team(ext)
    assert rec.team == "Web Development"
    assert rec.recommended_team == "Web Development"
    assert rec.confidence >= 0.80
    assert rec.requires_human_review is False


# ============================================================================
# 4. Mixed AI + Web Project (Multi-team & Supporting Teams)
# ============================================================================


def test_mixed_ai_and_web_project():
    """
    Project requires both AI/ML capabilities and Web portal.
    Verifies:
    1. Primary team is selected.
    2. Supporting team is identified.
    3. requires_human_review is True due to cross-functional complexity.
    """
    ext = make_extraction(
        project_name="AI Analytics Web Portal",
        summary="Web application dashboard that embeds machine learning predictions and an LLM chatbot.",
        requirements=[
            Requirement(description="Implement machine learning model training and prediction", priority="high"),
            Requirement(description="Deploy LLM chatbot for user inquiries", priority="high"),
            Requirement(description="Build React web dashboard frontend", priority="high"),
            Requirement(description="Build backend REST API with FastAPI", priority="medium"),
        ],
    )

    rec = recommend_team(ext)
    assert rec.team in ["AI / ML", "Web Development"]
    assert len(rec.supporting_teams) >= 1
    # Both domains should be represented across primary + supporting
    all_teams = [rec.team] + rec.supporting_teams
    assert "AI / ML" in all_teams
    assert "Web Development" in all_teams
    assert rec.requires_human_review is True
    assert rec.alternative_team in rec.supporting_teams


# ============================================================================
# 5. Ambiguous Project (Low Confidence -> Human Review)
# ============================================================================


def test_ambiguous_project_flags_low_confidence():
    """Sparse / vague signals lead to confidence < 0.70 and requires_human_review=True"""
    ext = make_extraction(
        project_name="Simple Integration",
        summary="We need some general software to help with our daily tasks.",
        requirements=[
            Requirement(description="Connect with existing third-party API", priority="medium"),
        ],
    )

    rec = recommend_team(ext)
    # Only 'api' matched (weak signal, score 2)
    assert rec.confidence < settings.CONFIDENCE_THRESHOLD
    assert rec.requires_human_review is True
    assert any("below threshold" in r.lower() for r in rec.reasoning)


# ============================================================================
# 6. No Matching Signals
# ============================================================================


def test_no_matching_signals():
    """Completely irrelevant non-technical requirements yield recommended_team=None and 0.0 confidence"""
    ext = make_extraction(
        project_name="Legal Compliance Review",
        summary="Review legal patent filings, licensing contracts, and intellectual property trademarks.",
        requirements=[
            Requirement(description="Review patent filings and trademark agreements", priority="high"),
            Requirement(description="Consult with legal counsel on licensing policies", priority="high"),
        ],
    )

    rec = recommend_team(ext)
    assert rec.team is None
    assert rec.recommended_team is None
    assert rec.supporting_teams == []
    assert rec.confidence == 0.0
    assert rec.requires_human_review is True
    assert any("no configured team signals matched" in r.lower() for r in rec.reasoning)


# ============================================================================
# 7. Empty Requirements Handling
# ============================================================================


def test_empty_requirements_fallback():
    """Empty list or None input safely returns None team and 0.0 confidence without raising"""
    # Case A: None
    rec_none = recommend_team(None)
    assert rec_none.team is None
    assert rec_none.confidence == 0.0
    assert rec_none.requires_human_review is True

    # Case B: Empty list
    rec_empty_list = recommend_team([])
    assert rec_empty_list.team is None
    assert rec_empty_list.confidence == 0.0
    assert rec_empty_list.requires_human_review is True

    # Case C: Empty string
    rec_empty_str = recommend_team("   ")
    assert rec_empty_str.team is None
    assert rec_empty_str.confidence == 0.0
    assert rec_empty_str.requires_human_review is True


# ============================================================================
# 8. Close Scores Between Competing Teams
# ============================================================================


def test_close_competing_scores_penalizes_confidence():
    """
    When two teams have nearly identical scores (e.g. margin <= 1),
    confidence is penalized and human review is mandated.
    """
    # Custom config with precisely equal / close weights
    custom_signals = {
        "Team Alpha": {"alpha_keyword": 5},
        "Team Beta": {"beta_keyword": 5},
    }

    text = "We need alpha_keyword and also beta_keyword in this build."
    rec = recommend_team(text, team_signals=custom_signals)

    # Tie: 5 vs 5 (margin = 0)
    assert rec.team in ["Team Alpha", "Team Beta"]
    assert len(rec.supporting_teams) == 1
    assert rec.confidence < settings.CONFIDENCE_THRESHOLD
    assert rec.requires_human_review is True
    assert any("tie score" in r.lower() or "close margin" in r.lower() for r in rec.reasoning)


# ============================================================================
# 9. Confidence Bound Invariant (Always 0.0 <= confidence <= 1.0)
# ============================================================================


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Non-matching words here",
        "api",
        "react frontend dashboard fastapi backend fullstack website",
        "machine learning deep learning rag llm computer vision neural nlp",
        "kubernetes docker aws cloud terraform devops ci/cd infrastructure",
        "ios android swift kotlin flutter mobile app",
        "etl data pipeline data warehouse snowflake bigquery spark kafka",
    ],
)
def test_confidence_always_clamped(text):
    rec = recommend_team(text)
    assert 0.0 <= rec.confidence <= 1.0


# ============================================================================
# 10. Config-Driven Extensibility
# ============================================================================


def test_custom_team_signals_override():
    """Verifies that recommendation logic dynamically respects custom config-driven signals"""
    custom_signals = {
        "Embedded Systems": {
            "firmware": 5,
            "microcontroller": 5,
            "c++": 4,
            "can bus": 4,
        },
        "Game Development": {
            "unreal engine": 5,
            "unity": 5,
            "shader": 4,
            "3d rendering": 4,
        },
    }

    text = "We need firmware development on a microcontroller with CAN bus integration."
    rec = recommend_team(text, team_signals=custom_signals)

    assert rec.team == "Embedded Systems"
    assert rec.confidence >= 0.80
    assert rec.requires_human_review is False
    assert any("firmware" in r for r in rec.reasoning)
