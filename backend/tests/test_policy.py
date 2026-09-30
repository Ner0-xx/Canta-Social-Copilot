import pytest

from app.policy import ActionType, PolicyContext, ReleaseLevel, evaluate_action


@pytest.mark.parametrize(
    "action",
    [
        ActionType.SCRAPE_RESTRICTED_DATA,
        ActionType.AUTOMATE_PLATFORM_BROWSER,
        ActionType.EVADE_SECURITY,
    ],
)
def test_prohibited_actions_are_never_allowed(action: ActionType) -> None:
    decision = evaluate_action(
        action,
        PolicyContext(
            release_level=ReleaseLevel.SCHEDULE,
            publishing_enabled=True,
            approved=True,
            official_api=True,
            explicit_user_request=True,
        ),
    )

    assert decision.allowed is False


def test_kill_switch_blocks_approved_public_action() -> None:
    decision = evaluate_action(
        ActionType.API_PUBLISH,
        PolicyContext(
            release_level=ReleaseLevel.INTEGRATE,
            publishing_enabled=False,
            approved=True,
            official_api=True,
        ),
    )

    assert decision.allowed is False
    assert "kill switch" in decision.reason


def test_official_api_and_approval_are_required() -> None:
    without_approval = evaluate_action(
        ActionType.API_PUBLISH,
        PolicyContext(
            release_level=ReleaseLevel.INTEGRATE,
            publishing_enabled=True,
            official_api=True,
        ),
    )
    without_official_api = evaluate_action(
        ActionType.API_PUBLISH,
        PolicyContext(
            release_level=ReleaseLevel.INTEGRATE,
            publishing_enabled=True,
            approved=True,
        ),
    )

    assert without_approval.allowed is False
    assert without_official_api.allowed is False


def test_manual_publish_requires_explicit_user_action() -> None:
    decision = evaluate_action(
        ActionType.PREPARE_MANUAL_PUBLISH,
        PolicyContext(
            release_level=ReleaseLevel.APPROVE,
            publishing_enabled=True,
            approved=True,
            explicit_user_request=False,
        ),
    )

    assert decision.allowed is False
    assert "explicit user action" in decision.reason

