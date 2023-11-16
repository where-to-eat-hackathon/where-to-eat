from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

if __name__ == '__main__':
    model = SentenceTransformer('')

    text = input("Текст запроса: ")
    client = QdrantClient("localhost", port=6333)

    query_vec = model.encode([text])

    search_result = client.search(collection_name="test_collection",
                                  query_vector=query_vec[0],
                                  limit=3)

    print(search_result)
