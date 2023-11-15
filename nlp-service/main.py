import json
import pika
import os

from common import (
    INPUT_QUEUE_NAME_ENVAR_KEY_NAME,
    RMQ_URL_ENVAR_KEY_NAME,
    RMQ_INPUT_PORT_ENVAR_KEY_NAME,
    RMQ_PASSWORD_ENVAR_KEY_NAME,
    RMQ_USERNAME_ENVAR_KEY_NAME,
    OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME,
    QDRANT_URL_ENVAR_KEY_NAME,
    QDRANT_HTTP_PORT_ENVAR_KEY_NAME,
    QDRANT_GRPC_PORT_ENVAR_KEY_NAME,
    QDRANT_COLLECTION_NAME_ENVAR_KEY_NAME,
    RESPONSE_ADDRESS_KEY,
    RESPONSE_TYPE_KEY,
    RMQ_OUTPUT_PORT_ENVAR_KEY_NAME,
    ServiceResponse,
    ServiceResponseBody,
    ServiceRequest, GeocodedAddress, RESPONSE_NAME_KEY, RESPONSE_RATING_KEY, RESPONSE_TEXT_KEY,
)
from sentence_transformers import SentenceTransformer
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchText

import http.client
from urllib.parse import quote


def find_nearest_coordinate(self, goal: GeocodedAddress, given_coords: List[GeocodedAddress]):
    """
    Calculation is taken from
    https://medium.com/analytics-vidhya/finding-nearest-pair-of-latitude-and-longitude-match-using-python-ce50d62af546
    """
    from math import radians, cos, sin, asin, sqrt

    earth_radius_km = 6371
    goal_longitude, goal_latitude = map(radians, [goal.longitude, goal.latitude])
    res = []
    for specific_coord in given_coords:
        specific_longitude, specific_latitude = map(radians, [specific_coord.longitude, specific_coord.latitude])
        dlon = specific_longitude - goal_longitude
        dlat = specific_latitude - goal_latitude
        a = sin(dlat / 2) ** 2 + cos(goal_latitude) * cos(specific_latitude) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        km = earth_radius_km * c
        res.append(km)
    return res


class PythonService:
    def __init__(self):
        # =============== RMQ configuration ================
        rmq_url = os.getenv(RMQ_URL_ENVAR_KEY_NAME)
        rmq_username = os.getenv(RMQ_USERNAME_ENVAR_KEY_NAME)
        rmq_password = os.getenv(RMQ_PASSWORD_ENVAR_KEY_NAME)

        # Input queue configuration.
        rmq_input_port = int(os.getenv(RMQ_INPUT_PORT_ENVAR_KEY_NAME))
        input_connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rmq_url,
                port=rmq_input_port,
                credentials=pika.credentials.PlainCredentials(
                    username=rmq_username, password=rmq_password
                ),
            )
        )
        rmq_input_channel = input_connection.channel()

        input_queue_name = os.getenv(INPUT_QUEUE_NAME_ENVAR_KEY_NAME)
        rmq_input_channel.queue_declare(queue=input_queue_name, durable=True)
        rmq_input_channel.basic_qos(prefetch_count=1)
        rmq_input_channel.basic_consume(
            queue=input_queue_name, on_message_callback=self.handle_request_callback
        )
        self.rmq_input_channel = rmq_input_channel

        # Output queue configuration.
        rmq_output_port = int(os.getenv(RMQ_OUTPUT_PORT_ENVAR_KEY_NAME))
        output_connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rmq_url,
                port=rmq_output_port,
                credentials=pika.credentials.PlainCredentials(
                    username=rmq_username, password=rmq_password
                ),
            )
        )
        rmq_output_channel = output_connection.channel()

        output_queue_name = os.getenv(OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME)
        rmq_output_channel.queue_declare(queue=output_queue_name, durable=True)
        self.rmq_output_channel = rmq_output_channel

        # ============ Quadrant configuration ==============
        self.transformer_model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        qdrant_url = os.getenv(QDRANT_URL_ENVAR_KEY_NAME)
        qdrant_port = os.getenv(QDRANT_HTTP_PORT_ENVAR_KEY_NAME)
        qdrant_gprc_port = int(os.getenv(QDRANT_GRPC_PORT_ENVAR_KEY_NAME))
        qdrant_client = QdrantClient(
            host=qdrant_url,
            port=qdrant_port,
            grpc_port=qdrant_gprc_port,
            prefer_grpc=True,
        )

        self.qdrant_client = qdrant_client

        qdrant_collection_name = os.getenv(QDRANT_COLLECTION_NAME_ENVAR_KEY_NAME)
        self.qdrant_collection_name = qdrant_collection_name

        # ============ Geocoder configuration ==============
        self.encoder_connection = http.client.HTTPSConnection('geocode.maps.co')

    def transform_address_into_coordinates(self, address: str) -> Optional[GeocodedAddress]:
        query_params = []
        for address in address.split(", "):
            # `quote` used to encode russian symbols.
            query_params.extend([quote(single_param) for single_param in address.split(" ")])
        address_as_param = "+".join(query_params)
        self.encoder_connection.request("GET", f"/search?q={address_as_param}")

        response = self.encoder_connection.getresponse()
        if response.status == 429:
            # We've exceeded requests per second limit. We may wait for some time and recursively call ourselves.
            return None

        data = response.read()
        deserialized_data = json.loads(data)
        if len(deserialized_data) >= 1:
            nearest_res = deserialized_data[0]
            return GeocodedAddress(float(nearest_res["lat"]), float(nearest_res["lon"]))
        else:
            # Server doesn't found anything.
            return None

    def search_db(self, message, town_filter_name=None) -> List[ServiceResponseBody]:
        embedding = self.transformer_model.encode([message])[0]

        if town_filter_name is None:
            query_filter = None
        else:
            query_filter = Filter(must=[FieldCondition(
                key=RESPONSE_ADDRESS_KEY,
                match=MatchText(text=town_filter_name),
            )])
        print(self.qdrant_collection_name)
        print(query_filter)
        # print(embedding)
        search_result = self.qdrant_client.search(
            collection_name=self.qdrant_collection_name,
            query_vector=embedding,
            query_filter=query_filter,
        )

        response = []
        for res in search_result:
            res_payload = res.payload
            response.append(
                ServiceResponseBody(
                    res_payload[RESPONSE_ADDRESS_KEY],
                    res_payload[RESPONSE_NAME_KEY],
                    res_payload[RESPONSE_TYPE_KEY],
                    res_payload[RESPONSE_RATING_KEY],
                    res_payload[RESPONSE_TEXT_KEY],
                )
            )
        return response

    def handle_request_callback(self, ch, method, properties, body):
        request = ServiceRequest(**json.loads(body))

        print(f"Successfully get message: [{request}]")

        quadrant_response = self.search_db(request.message)
        response_dataclasses = [
            ServiceResponse(request.request_id, res_body)
            for res_body in quadrant_response
        ]
        serialized_response = ServiceResponse.schema().dumps(
            response_dataclasses, many=True
        )

        self.rmq_output_channel.basic_publish(
            exchange="",
            routing_key=OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME,
            body=serialized_response,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Successfully sent response: [{serialized_response}]")

    def start_listening_input_query(self):
        self.rmq_input_channel.start_consuming()


if __name__ == "__main__":
    service = PythonService()
    res = service.search_db("Я бы хотел поесть вкусной пиццы!", town_filter_name="Санкт-Петербург")
    # res = service.search_db("Я бы хотел поесть вкусной пиццы!")
    print("Printing db search result:")
    for r in res:
        print(r.address)
