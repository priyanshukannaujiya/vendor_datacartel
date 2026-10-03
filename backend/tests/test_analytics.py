def test_analytics_uses_stored_batches_without_invented_scores(
    client,
    sample_vendor,
    sample_batch,
):
    response = client.get("/api/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kpis"]["total_vendors"] == 1
    assert sum(
        item["value"] for item in payload["charts"]["vendor_risk_distribution"]
    ) == 0
    recent_batch = payload["tables"]["recent_batch_assessments"][0]
    assert recent_batch["risk_score"] is None
    assert recent_batch["email_status"] is None

