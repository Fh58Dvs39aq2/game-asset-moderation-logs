"""Emit and search observable decisions from a game moderation job."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from infrai_logs import InfraiLogs, LogEntry, LogSearch


class AssetKind(str, Enum):
    AVATAR = "avatar"
    MAP = "map"
    EMBLEM = "emblem"


@dataclass(frozen=True)
class PlayerAssetEvent:
    event_id: str
    asset_id: str
    player_id: str
    asset_kind: AssetKind
    live_event_id: str
    report_count: int


@dataclass(frozen=True)
class QueueDecision:
    queue: str
    reason: str


def decide_queue(event: PlayerAssetEvent) -> QueueDecision:
    """Put reported assets in human review; let unreported assets continue."""
    if event.report_count > 0:
        return QueueDecision(queue="human-review", reason="player-reported")
    return QueueDecision(queue="publish", reason="no-reports")


def record_decision(client: InfraiLogs, event: PlayerAssetEvent) -> QueueDecision:
    decision = decide_queue(event)
    client.ingest(
        LogEntry(
            level="warning" if decision.queue == "human-review" else "info",
            message="player asset moderation decision",
            service="game-moderation-job",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "event_id": event.event_id,
                "asset_id": event.asset_id,
                "player_id": event.player_id,
                "asset_kind": event.asset_kind.value,
                "live_event_id": event.live_event_id,
                "queue": decision.queue,
                "reason": decision.reason,
            },
        ),
        idempotency_key=event.event_id,
    )
    return decision


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", action="store_true")
    args = parser.parse_args()
    client = InfraiLogs()
    if args.search:
        result = client.search(
            LogSearch(q="human-review", service="game-moderation-job", level="warning")
        )
        print(result)
        return

    event = PlayerAssetEvent(
        event_id=str(uuid4()),
        asset_id="map-crystal-cavern",
        player_id="player-2048",
        asset_kind=AssetKind.MAP,
        live_event_id="summer-raid",
        report_count=2,
    )
    decision = record_decision(client, event)
    print(f"asset={event.asset_id} queue={decision.queue} reason={decision.reason}")


if __name__ == "__main__":
    main()
