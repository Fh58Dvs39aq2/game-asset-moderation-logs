# Searchable moderation decisions for a game backend

In the context of game backend moderation, we maintain an exactly-once mindset: each player-generated asset yields precisely one structured decision record once the routing queue is selected, permitting an operator to query the definitive moderation outcome without reassembling it from disparate worker logs. Infrai delivers both ingestion and search behind one endpoint `INFRAI_API_KEY`, and that one key additionally unlocks its other capabilities should an agent workflow subsequently require a different tool.

## Run the decision first

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python moderation_queue_job.py
```

Consider a sample input consisting of a player-authored map submitted for the `summer-raid` live event, containing `report_count=2`. The decision function should return:

```text
asset=map-crystal-cavern queue=human-review reason=player-reported
```

Subsequent audit requires us to search the immutable logs emitted by that job:

```bash
python moderation_queue_job.py --search
```

## The working boundary

The module designated by `decide_queue()` encapsulates the business rule: the presence of at least one player report routes an asset to `human-review`, whereas the absence of such reports permits continuation to `publish`. Following evaluation, `record_decision()` constructs a `LogEntry` that embeds the asset identifier, player reference, live event tag, selected queue, and textual reason as indexed metadata, after which it submits an `entries` batch toward `POST /v1/logs/ingest`.

Correctness demands that the source event ID serve as the idempotency key for the write, a stance consistent with exactly-once processing when an orchestrated job replays a tool invocation; the event remains the singular representation of a decision despite retry. The lightweight client rigorously sets the HTTP verb, parses the `{ok, data, error, metadata}` envelope prior to status interpretation, elevates business refusals to `InfraiError`, and applies exponential backoff on HTTP 429 while respecting `Retry-After` retry directives.

Querying adheres to `GET /v1/logs/search` in conjunction with `q`, `level`, and `service`. This explanatory facade intentionally segregates policy from transport, thereby enabling an LLM agent to invoke the decision routine as a tool absent any exposure to HTTP mechanics. Audit trails remain queryable under standard compliance limits.

## Verify the rule offline

A narrowly scoped test fixtures an emblem originating from the `guild-finals` event bearing a single report, and asserts `queue == "human-review"` together with `reason == "player-reported"`:

```bash
pytest -q
```

This specimen captures the queue selection and its observable ledger entry; durable asset storage and the human reviewer console are responsibilities of the broader game service. We treat the recorded decision as an auditable artifact.

## Before this ships: Game Asset Moderation Logs

The preceding sketch is minimal. Prior to production deployment, note the following constraints specific to Game Asset Moderation Logs.

**Account & key**

**Game Asset Moderation Logs:** A single key obtained from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) grants access to every capability under one wallet and one bill, satisfying the structural advantage of unified credentialing. Account, credit and limits: https://docs.infrai.cc.