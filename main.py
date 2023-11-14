import re
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

def average_pool(last_hidden_states: Tensor,
                 attention_mask: Tensor) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

tokenizer = AutoTokenizer.from_pretrained('intfloat/e5-base-v2')
model = AutoModel.from_pretrained('intfloat/e5-base-v2')


def parse_file(filename: str):
    f = open(filename, 'r')
    reg = re.compile(r"address=(.*)\sname_ru=(.*)\srating=(.*)\.\srubrics=(.*)text=(.*)")
    food = ['кафе', 'кофейня', 'кондитерская', 'ресторан', 'быстрое питание', 'доставка еды и обедов', 'пекарня',
            'столовая', 'бар', 'паб', 'суши-бар', 'торты', 'магазин пива']
    regex = re.compile(r".*(" + '|'.join(food) + r").")
    for line in f:
        comment = reg.match(line)
        comment = comment.groups()
        rubrics = comment[4].lower()
        if not (regex.match(rubrics)):
            continue
        go_through_model(comment)


def go_through_model(line):
    batch_dict = tokenizer(line[4], max_length=512, padding=True, truncation=True, return_tensors='pt')
    outputs = model(**batch_dict)
    embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
    # normalize embeddings
    embeddings = F.normalize(embeddings, p=2, dim=1)

    #добавить в бд