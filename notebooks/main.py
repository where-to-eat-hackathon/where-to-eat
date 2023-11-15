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
client.create_collection(
    collection_name="test_collection",
    vectors_config=VectorParams(size=model.get_sentence_embedding_dimension(), distance=Distance.DOT),
)

def average_pool(last_hidden_states: Tensor,
                 attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def parse_file(filename: str):
    f = open(filename, 'r')
    reg = re.compile(r"address=(.*)\sname_ru=(.*)\srating=(.*)\.\srubrics=(.*)text=(.*)")
    food = ['кафе', 'кофейня', 'кондитерская', 'ресторан', 'быстрое питание', 'доставка еды и обедов', 'пекарня',
            'столовая', 'бар', 'паб', 'суши-бар', 'торты', 'магазин пива']
    regex = re.compile(r".*(" + '|'.join(food) + r").")
    counter = 1
    for line in f:
        if counter == 1001:
            break
        comment = reg.match(line)
        if not comment:
            continue
        comment = comment.groups()
        rubrics = comment[4].lower()
        if not (regex.match(rubrics)):
            continue
        counter += 1
        go_through_model(comment, counter)



def go_through_model(line, line_id):
    #batch_dict = tokenizer(line[4], max_length=512, padding=True, truncation=True, return_tensors='pt')
    #outputs = model(**batch_dict)
    outputs = model.encode('query: ' + line[4])
    #embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
    # normalize embeddings
    #embeddings = F.normalize(embeddings, p=2, dim=1)

    #добавить в бд

    operation_info = client.upsert(
        collection_name="test_collection",
        wait=True,
        points=[
            PointStruct(id=line_id, vector=outputs, payload={"address": line[0], "name": line[1]})
        ]
    )
    line_id += 1
    print(operation_info)

parse_file(r"geo-reviews-dataset-2023.tskv")
