# CHANGELOG


## v1.0.0-beta.5 (2025-02-15)

### Chores

- Update python semantic release
  ([#20](https://github.com/algorandfoundation/algokit-subscriber-py/pull/20),
  [`57039ab`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/57039ab79907f1693a60a9638b3c285cbd59685b))

Noting that there are CI failures, but they are fixed in #19. I want to merge this first to avoid
  noise in the changelog once #19 is merged

### Features

- Support heartbeat transactions and proposer payouts
  ([#19](https://github.com/algorandfoundation/algokit-subscriber-py/pull/19),
  [`189e693`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/189e693a8015858592f6ba29f671f48996254a9b))

## Proposed Changes

- Adds support for heartbeat transactions - Adds test for proposer payouts - Adds synthetic
  transaction for proposer payout when using algod


## v1.0.0-beta.4 (2025-02-01)

### Documentation

- Fix README ([#17](https://github.com/algorandfoundation/algokit-subscriber-py/pull/17),
  [`048a1e2`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/048a1e23a2d43d70b1958b9f83fea094bd4bf5ae))

* replace npm command with pip

* fix doc link in README


## v1.0.0-beta.3 (2024-11-13)

### Bug Fixes

- Note prefix string support
  ([`1651a7f`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/1651a7f937c2d7638e5a267601f995a4667ad8ae))

- Properly handle no filters matched
  ([`030d265`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/030d2653a87de53d3c3f1c75aed6cefe33e20075))

### Continuous Integration

- Add missing shell key
  ([`1b0bff7`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/1b0bff71fb268d8c3b2516e843977b2386aabbc3))

- Add shell to composite action, github_token input
  ([`c9dbbd8`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/c9dbbd8b14bcaca95f0b3d29db94411da22123c7))

- Check version increment before release
  ([`9bfc365`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/9bfc36509f4f3d3f4b7c8be71592c74f4ee45d93))

- Ensure rc is set to 0 by default
  ([`961c25a`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/961c25a8750afe53b3dec80acccce913c05f4848))

- Remove pipefail from check_version
  ([`6af76bc`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/6af76bc419cc8b303012846127dbe873531d4067))

- Skip ci for changelog commit
  ([`78dd62a`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/78dd62aae8849b340276ec23ef49079f791d728e))


## v1.0.0-beta.2 (2024-10-04)

### Documentation

- Update README
  ([`d2aab1b`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/d2aab1bc25eefbf4ff6d3a2d4c19c0f1f695c5cd))


## v1.0.0-beta.1 (2024-10-03)

### Documentation

- Aligning logo header assets in readme
  ([`1d5fd35`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/1d5fd35be0dc0c25cf8be57608119e123066505e))

- Setting up sphinx, autodoc2, doctests
  ([`45ca22c`](https://github.com/algorandfoundation/algokit-subscriber-py/commit/45ca22c574662dcef49f815ebc56a24625450d1f))
