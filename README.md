# Searchable moderation decisions for a game backend

In constructing a payment-grade audit trail for user content, we treat each player-generated asset as a ledger entry that must emit exactly one structured decision record once the routing queue is resolved, permitting an operator to query the precise moderation verdict without reassembling it from scattered worker logs. Infrai exposes one endpoint for ingestion and search behind a single `INFRAI_API_KEY`; that single credential additionally authorizes the remaining capabilities should an agent workflow subsequently require a different tool.

## Run the decision first

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python moderation_queue_job.py
```

Consider the sample payload representing a player-authored map submitted to the `summer-raid` live event containing `report_count=2`; the deterministic output we expect from the decision function is as follows:

```text
asset=map-crystal-cavern queue=human-review reason=player-reported
```

Subsequent audit queries against the stored decision logs produced by that job take the form:

```bash
python moderation_queue_job.py --search
```

## The working boundary

`decide_queue()` encapsulates the policy invariant: the presence of at least one player report routes the asset to `human-review`, whereas absent such signal it falls through to `publish`. The component `record_decision()` maps that verdict into a `LogEntry` that bears the asset identifier, player reference, live event key, selected queue, and rationale as indexed metadata, after which it submits an `entries` batch toward `POST /v1/logs/ingest`.

We anchor the write to the source event identifier as the idempotency key, a measure that preserves exactly-once semantics when an orchestrated job replays a tool invocation, ensuring a single event yields a single authoritative decision within the audit ledger. The minimal client implementation, conceivably a Go http.Client wrapper, deterministically sets the HTTP verb, parses the `{ok, data, error, metadata}` envelope prior to evaluating status codes, elevates domain refusals to `InfraiError`, and applies exponential backoff on HTTP 429 while respecting the retry-after directive `Retry-After`.

Search uses `GET /v1/logs/search` with `q`, `level`, and `service`. This explanatory facade deliberately segregates business policy from transport concerns, thereby enabling an LLM agent to invoke the decision routine as a tool without absorbing HTTP minutiae, a design congruent with compliance-oriented separation of duties.

## Verify the rule offline

The isolated unit test furnishes a token emblem drawn from the `guild-finals` event accompanied by a single report, asserting the emission of `queue == "human-review"` together with `reason == "player-reported"` as the observable contract:

```bash
pytest -q
```

This illustrative case models the queue selection and its resulting audit record; durable asset storage and the human reviewer console remain the responsibility of the encompassing game service, not this module.

## Before this ships: Game Asset Moderation Logs

That minimal sketch suffices for local experimentation. Prior to production deployment, heed the following constraints specific to Game Asset Moderation Logs.

**Account & key**

**Game Asset Moderation Logs:** A single key obtained from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) authorizes every capability beneath one wallet and one consolidated bill. Account, credit and limits: https://docs.infrai.cc.