from algokit_utils import AlgorandClient
from algokit_utils.models.network import AlgoClientNetworkConfig

# Individual LocalNet constants
ALGOD_SERVER = "http://localhost"
ALGOD_PORT = 4001
ALGOD_TOKEN = "a" * 64

KMD_SERVER = "http://localhost"
KMD_PORT = 4002
KMD_TOKEN = "a" * 64

INDEXER_SERVER = "http://localhost"
INDEXER_PORT = 8980
INDEXER_TOKEN = "a" * 64

# Composed config objects
ALGOD_CONFIG = AlgoClientNetworkConfig(server=ALGOD_SERVER, token=ALGOD_TOKEN, port=ALGOD_PORT)
KMD_CONFIG = AlgoClientNetworkConfig(server=KMD_SERVER, token=KMD_TOKEN, port=KMD_PORT)
INDEXER_CONFIG = AlgoClientNetworkConfig(
    server=INDEXER_SERVER, token=INDEXER_TOKEN, port=INDEXER_PORT
)