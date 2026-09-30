def test_strategy_round_trip(client) -> None:
    payload = {
        "brand": {
            "display_name": "Ada Example",
            "account_purpose": "Share practical engineering leadership lessons.",
            "biography": "Builder and engineering leader.",
            "expertise": ["engineering leadership", "developer tools"],
            "offers": ["consulting"],
            "business_goals": ["grow a trusted professional audience"],
            "sensitive_topics": ["private client information"],
            "required_disclosures": [],
        },
        "voice": {
            "tone": ["clear", "warm", "specific"],
            "preferred_vocabulary": ["practical"],
            "avoided_vocabulary": ["guru"],
            "formatting_preferences": "Short paragraphs.",
            "call_to_action_style": "Ask a genuine question when useful.",
            "writing_examples": ["A representative writing example."],
        },
        "audiences": [
            {
                "name": "Engineering managers",
                "description": "First-line and senior managers.",
                "needs": ["better team systems"],
                "interests": ["leadership"],
                "desired_action": "Join a thoughtful discussion",
            }
        ],
        "pillars": [
            {
                "name": "Engineering leadership",
                "description": "Lessons from building healthy teams.",
                "target_percentage": 100,
                "example_topics": ["planning", "feedback"],
            }
        ],
    }

    response = client.put("/api/strategy", json=payload)
    assert response.status_code == 200
    assert response.json()["brand"]["display_name"] == "Ada Example"

    saved = client.get("/api/strategy")
    assert saved.status_code == 200
    assert saved.json()["pillars"][0]["target_percentage"] == 100

    audit = client.get("/api/audit-events")
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "strategy.updated"


def test_pillar_percentages_must_total_one_hundred(client) -> None:
    response = client.put(
        "/api/strategy",
        json={
            "brand": {},
            "voice": {},
            "audiences": [],
            "pillars": [
                {
                    "name": "One incomplete pillar",
                    "target_percentage": 60,
                }
            ],
        },
    )

    assert response.status_code == 422

