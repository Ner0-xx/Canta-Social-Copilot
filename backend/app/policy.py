from dataclasses import dataclass
from enum import IntEnum, StrEnum


class ReleaseLevel(IntEnum):
    OBSERVE = 1
    DRAFT = 2
    APPROVE = 3
    INTEGRATE = 4
    SCHEDULE = 5

    @classmethod
    def parse(cls, value: str) -> "ReleaseLevel":
        try:
            return cls[value.upper()]
        except KeyError as exc:
            raise ValueError(f"Unknown release level: {value}") from exc


class ActionType(StrEnum):
    RESEARCH = "research"
    GENERATE_DRAFT = "generate_draft"
    PREPARE_MANUAL_PUBLISH = "prepare_manual_publish"
    API_PUBLISH = "api_publish"
    SCHEDULE_API_PUBLISH = "schedule_api_publish"
    API_COMMENT = "api_comment"
    API_REPLY = "api_reply"
    REACT = "react"
    FOLLOW = "follow"
    DIRECT_MESSAGE = "direct_message"
    SCRAPE_RESTRICTED_DATA = "scrape_restricted_data"
    AUTOMATE_PLATFORM_BROWSER = "automate_platform_browser"
    EVADE_SECURITY = "evade_security"


@dataclass(frozen=True)
class PolicyContext:
    release_level: ReleaseLevel
    publishing_enabled: bool
    approved: bool = False
    official_api: bool = False
    explicit_user_request: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    required_release_level: ReleaseLevel | None = None


ALWAYS_PROHIBITED = {
    ActionType.SCRAPE_RESTRICTED_DATA,
    ActionType.AUTOMATE_PLATFORM_BROWSER,
    ActionType.EVADE_SECURITY,
}

MVP_DISABLED = {
    ActionType.REACT,
    ActionType.FOLLOW,
    ActionType.DIRECT_MESSAGE,
}


def evaluate_action(action: ActionType, context: PolicyContext) -> PolicyDecision:
    if action in ALWAYS_PROHIBITED:
        return PolicyDecision(False, "This action is prohibited by the product safety policy.")

    if action in MVP_DISABLED:
        return PolicyDecision(False, "This public action is disabled in the MVP.")

    if action is ActionType.RESEARCH:
        return PolicyDecision(True, "Research using approved sources is allowed.")

    if action is ActionType.GENERATE_DRAFT:
        required = ReleaseLevel.DRAFT
        if context.release_level < required:
            return PolicyDecision(False, "Draft generation is not enabled.", required)
        return PolicyDecision(True, "Draft generation is allowed.")

    if not context.publishing_enabled:
        return PolicyDecision(False, "The global publishing kill switch is off.")

    if not context.approved:
        return PolicyDecision(False, "This public action requires a recorded approval.")

    if action is ActionType.PREPARE_MANUAL_PUBLISH:
        required = ReleaseLevel.APPROVE
        if context.release_level < required:
            return PolicyDecision(False, "Assisted publishing is not enabled.", required)
        if not context.explicit_user_request:
            return PolicyDecision(False, "Manual publishing requires an explicit user action.")
        return PolicyDecision(True, "Approved content may be prepared for manual publication.")

    if action in {ActionType.API_PUBLISH, ActionType.API_COMMENT, ActionType.API_REPLY}:
        required = ReleaseLevel.INTEGRATE
        if context.release_level < required:
            return PolicyDecision(False, "Official API actions are not enabled.", required)
        if not context.official_api:
            return PolicyDecision(False, "Public actions must use an approved official API.")
        if action in {ActionType.API_COMMENT, ActionType.API_REPLY} and not context.explicit_user_request:
            return PolicyDecision(
                False,
                "Comments and replies require individual, explicit user approval.",
            )
        return PolicyDecision(True, "The individually approved official API action is allowed.")

    if action is ActionType.SCHEDULE_API_PUBLISH:
        required = ReleaseLevel.SCHEDULE
        if context.release_level < required:
            return PolicyDecision(False, "Scheduled API publishing is not enabled.", required)
        if not context.official_api:
            return PolicyDecision(False, "Scheduled publishing requires an approved official API.")
        return PolicyDecision(True, "The approved post may be scheduled through the official API.")

    return PolicyDecision(False, "The action is not recognized by the policy engine.")

