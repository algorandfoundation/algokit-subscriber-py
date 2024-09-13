import time
from typing import cast

import msgpack  # type: ignore[import-untyped]
from algosdk.v2client.algod import AlgodClient

from .types.block import BlockData
from .utils import chunk_array, logger, range_inclusive


def block_response_to_block_data(response: bytes) -> BlockData:
    return cast(
        BlockData,
        msgpack.unpackb(
            response, strict_map_key=False, unicode_errors="surrogateescape"
        ),
    )


def get_blocks_bulk(context: dict[str, int], client: AlgodClient) -> list[BlockData]:
    """
    Retrieves blocks in bulk (30 at a time) between the given round numbers.
    :param context: A dictionary containing 'startRound' and 'maxRound'
    :param client: The algod client
    :return: The blocks
    """
    # Grab 30 at a time to not overload the node
    block_chunks = chunk_array(
        range_inclusive(context["start_round"], context["max_round"]), 30
    )
    blocks = []

    for chunk in block_chunks:
        logger.info(f"Retrieving {len(chunk)} blocks from round {chunk[0]} via algod")
        start_time = time.time()

        for round_num in chunk:
            response = client.algod_request(
                "GET",
                f"/blocks/{round_num}",
                params={"format": "msgpack"},
                response_format="msgpack",
            )
            decoded = block_response_to_block_data(cast(bytes, response))
            blocks.append(decoded)

        elapsed_time = time.time() - start_time
        logger.debug(
            f"Retrieved {len(chunk)} blocks from round {chunk[0]} via algod in {elapsed_time:.2f}s"
        )

    return blocks
