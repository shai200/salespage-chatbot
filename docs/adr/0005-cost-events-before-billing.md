# ADR 0005: Record our cost per build and per app, and do not charge yet

## Status

Accepted for the [generalize-app-generation](../../openspec/changes/generalize-app-generation/design.md) design. Not implemented yet.

## Context

A later change will charge through Stripe at no less than twice what Homerun pays. The paid actions are chat tokens, images, Railway compute and storage, and the bytes of a hosted sales page. Billing cannot be reconstructed after the fact if the call sites do not record usage.

## Decision

Append-only `cost_events` store Homerun’s cost in integer USD micros, with the provider, model, quantities, a provider request id, and `cost_basis` (`provider_reported` or `price_table`). `build_id` is set for a generation turn and null for later hosting accrual. The same provider request id and kind cannot be stored twice.

Events are written only from the model provider (chat and image), from static publish (bytes, then byte-hours), and from a Railway usage poller (CPU, memory, egress, volume, backup). There is no customer price column and no Stripe call. Railway builds are not events while Railway does not charge them. The workspace subscription fee is not split across apps.

## Consequences

- The later billing change can sum a build or an app and apply a multiplier of at least 2 to that sum.
- HeartAI’s price is already at least 2× its upstream. This ledger stores HeartAI’s charge to us, not the upstream raw price. Which of those the 2× floor uses is left to the billing change.
- If a host returns tokens and no dollars, the amount is a local price table and the basis says so.
