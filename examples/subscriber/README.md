# AlgoKit Subscriber Examples

15 runnable examples covering the `algokit-subscriber` Python API — from a single `poll_once()` call to ARC-28 event parsing, inner transactions, and lifecycle hooks.

## Prerequisites

- **Python >= 3.12**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **AlgoKit LocalNet** running (`algokit localnet start`)

## Quick Start

All commands are run from the `examples/subscriber` directory:

```bash
cd examples/subscriber

# Install dependencies
uv sync

# Run a single example
uv run python 01_basic_poll_once.py

# Run all examples
./verify-all.sh
```

## Examples

| # | File | Description |
|---|------|-------------|
| 01 | `01_basic_poll_once.py` | Single `poll_once()` call with a sender filter |
| 02 | `02_continuous_subscriber.py` | Continuous polling with event handlers and auto-stop |
| 03 | `03_payment_filters.py` | Payment filters: sender, receiver, amount range, note prefix |
| 04 | `04_asset_transfer.py` | ASA lifecycle: create, opt-in, transfer subscription |
| 05 | `05_app_call.py` | Application call subscription with ABI method filtering |
| 06 | `06_multiple_filters.py` | Multiple named filters with deduplication |
| 07 | `07_balance_changes.py` | Balance change filtering for ALGO and ASA transfers |
| 08 | `08_arc28_events.py` | ARC-28 event parsing, filtering, and inspection |
| 09 | `09_inner_transactions.py` | Inner transaction subscription and parent-child relationships |
| 10 | `10_batch_and_mappers.py` | Custom mapper transforms and batch handlers |
| 11 | `11_watermark_persistence.py` | File-backed watermark persistence across polls |
| 12 | `12_sync_behaviours.py` | All 4 sync behaviours demonstrated |
| 13 | `13_custom_filters.py` | Custom filter predicates with multi-condition logic |
| 14 | `14_stateless_subscriptions.py` | `get_subscribed_transactions()` for serverless patterns |
| 15 | `15_lifecycle_hooks.py` | `on_before_poll`, `on_poll`, `on_error` hooks and inspect callback |

## Shared Utilities

The `shared/` package provides helpers used across examples:

- **`constants.py`** — LocalNet connection constants (`ALGOD_CONFIG`, `KMD_CONFIG`, `INDEXER_CONFIG`) and individual values (`*_SERVER`, `*_PORT`, `*_TOKEN`)
- **`utils.py`** — display helpers (`print_header`, `print_step`, `format_algo`, `shorten_address`), `format_micro_algo()`, and `create_filter_tester()` for reusable filter verification
- **`artifacts/testing-app.arc56.json`** — ARC-56 app spec used by examples 05, 08, 09

## Development

### Adding New Examples

1. Create a file following naming: `NN_descriptive_name.py`
2. Add a docstring header describing the example
3. Add to `verify-all.sh`

### Example Header Format

```python
"""
Example: [Title]

This example demonstrates [description].
- Key operation 1
- Key operation 2

Prerequisites:
- LocalNet running
"""
```

### Running Tests

```bash
# Run all verification scripts (from examples/subscriber/)
./verify-all.sh
```
