import pickle
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

if __name__ == '__main__':
    client = QdrantClient("localhost", port=6333)
    # client.set_model('intfloat/multilingual-e5-large')
    # client.set_model(model)
    # vector_config = client.get_fastembed_vector_params()
    vector_config = VectorParams(size=384, distance=Distance.COSINE)

    # client.create_collection(collection_name=collection_name,
    #                          vectors_config=vector_config)

    collection_name = "reviews-MiniLM-L12-V2"

    with open('../points.pickle', 'rb') as f:
        points = pickle.loads(f.read())

    batch = 1024
    idx = 0

    while idx < len(points):
        b = points[idx:idx + batch]
        client.upsert(collection_name=collection_name, wait=True, points=b)
        idx += batch

    # client.add(collection_name=collection_name,
    #            documents=docs,
    #            metadata=metadata,
    #            ids=ids,
    #            parallel=None)

    # embedding_model = Embedding(model_name="intfloat/multilingual-e5-large",
    #                             max_length=512)
    # embeddings = embedding_model.embed(docs)
