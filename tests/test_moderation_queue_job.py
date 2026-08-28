from moderation_queue_job import AssetKind, PlayerAssetEvent, decide_queue


def test_reported_player_asset_is_routed_to_human_review() -> None:
    event = PlayerAssetEvent(
        event_id="evt-17",
        asset_id="emblem-9",
        player_id="player-3",
        asset_kind=AssetKind.EMBLEM,
        live_event_id="guild-finals",
        report_count=1,
    )

    decision = decide_queue(event)

    assert decision.queue == "human-review"
    assert decision.reason == "player-reported"
