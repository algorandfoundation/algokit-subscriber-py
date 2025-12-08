import itertools
import logging
import time

from algokit_algod_client import AlgodClient
from algokit_algod_client.models import BlockResponse

logger = logging.getLogger(__package__)


def get_blocks_bulk(start_round: int, max_round: int, client: AlgodClient) -> list[BlockResponse]:
    """
    Retrieves blocks in bulk (30 at a time) between the given round numbers.
    :param start_round: Starting round to fetch
    :param max_round: Max round to fetch (inclusive)
    :param client: The algod client
    :return: The blocks
    """
    # Grab 30 at a time to not overload the node
    blocks = []
    for chunk in itertools.batched(range(start_round, max_round + 1), 30):
        logger.info(f"Retrieving {len(chunk)} blocks from round {chunk[0]} via algod")
        start_time = time.time()

        for round_num in chunk:
            response = client.block(round_num)
            blocks.append(response)

        elapsed_time = time.time() - start_time
        logger.debug(
            f"Retrieved {len(chunk)} blocks from round {chunk[0]} via algod in {elapsed_time:.2f}s"
        )

    return blocks
