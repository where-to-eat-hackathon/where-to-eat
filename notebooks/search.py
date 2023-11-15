import re
import torch.nn.functional as F
from torch import Tensor
#from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.models import PointStruct

#tokenizer = AutoTokenizer.from_pretrained('intfloat/e5-base-v2')
#model = AutoModel.from_pretrained('intfloat/e5-base-v2')
model = SentenceTransformer('intfloat/e5-base-v2')

client = QdrantClient("localhost", port=6333)


def search_line(line: str):
    output = model.encode("query: " + line)
    search_result = client.search(
        collection_name="test_collection", query_vector=output, limit=3
    )
    print(search_result)


search_line('Вкусный кофе')
