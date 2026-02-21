---
title: Fast Catchup
description: Use Algorand Indexer to catch up millions of rounds in seconds rather than days.
---

When [subscribing to the chain](../sync-behaviour/) for the purposes of building an index you often will want to start at the beginning of the chain or a substantial time in the past when the given solution you are subscribing for started.

This kind of catch up takes days to process since algod only lets you retrieve a single block at a time and retrieving a block takes 0.5-1s. Given there are millions of blocks in MainNet it doesn't take long to do the math to see why it takes so long to catch up.

This subscriber library has a unique, optional indexer catch up mode that allows you to use indexer to catch up to the tip of the chain in seconds or minutes rather than days for your specific filter.

This is really handy when you are doing local development or spinning up a new environment and don't want to wait for days.

To make use of this feature, you need to set the `sync_behaviour` config to `catchup-with-indexer` and ensure that you pass `indexer` in to the [entry point](../../guide/subscriptions/) along with `algod`.

Any [filter](../filtering/) you apply will be seamlessly translated to indexer searches to get the historic transactions in the most efficient way possible based on the apis indexer exposes. Once the subscriber is within `max_rounds_to_sync` of the tip of the chain it will switch to subscribing using `algod`.

The indexer catchup isn't magic - if the filter you are trying to catch up with generates an enormous number of transactions then it will run very slowly. In that instance there is a config parameter `max_indexer_rounds_to_sync` so you can break the indexer catchup into multiple "polls" e.g. 100,000 rounds at a time.

## How Indexer Catchup Works

Indexer catchup runs in two stages:

1. **Pre-filtering**: Any filters that can be translated to the [indexer search transactions endpoint](https://dev.algorand.co/reference/rest-api/indexer/operations/searchfortransactions/). This query is then run between the rounds that need to be synced and paginated 1000 results at a time. The following filters are converted to a pre-filter:
   - `sender` (single value)
   - `receiver` (single value)
   - `type` (single value)
   - `note_prefix`
   - `app_id` (single value)
   - `asset_id` (single value)
   - `min_amount` and `max_amount` when their value is less than 2 \*\* 53 - 1 and type or asset context is provided

2. **Post-filtering**: All remaining filters are then applied in-memory to the resulting list of transactions from the pre-filter before being returned as subscribed transactions.