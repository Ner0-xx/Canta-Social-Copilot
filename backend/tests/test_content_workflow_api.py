def test_create_and_list_ideas(client) -> None:
    response = client.post(
        "/api/content/ideas",
        json={
            "title": "Launch a practical leadership thread",
            "summary": "A short idea about leading with calm under pressure.",
            "source_type": "rss",
            "source_ref": "https://example.com/leadership",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "idea"
    assert payload["title"] == "Launch a practical leadership thread"

    listing = client.get("/api/content/ideas")
    assert listing.status_code == 200
    assert any(item["id"] == payload["id"] for item in listing.json())


def test_create_draft_and_transition_status(client) -> None:
    idea = client.post(
        "/api/content/ideas",
        json={
            "title": "Share a weekly systems tip",
            "summary": "A short idea for a recurring content series.",
            "source_type": "note",
            "source_ref": "personal-note",
        },
    ).json()

    draft = client.post(
        f"/api/content/ideas/{idea['id']}/drafts",
        json={
            "platform": "x",
            "title": "Weekly systems tip",
            "body": "Small systems make big teams calmer.",
        },
    )

    assert draft.status_code == 200
    draft_payload = draft.json()
    assert draft_payload["status"] == "draft"

    transition = client.post(
        f"/api/content/drafts/{draft_payload['id']}/transition",
        json={"status": "approved"},
    )

    assert transition.status_code == 200
    assert transition.json()["status"] == "approved"
