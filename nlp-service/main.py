import json
import pika
import os
from time import time

from common import (
    INPUT_QUEUE_NAME_ENVAR_KEY_NAME,
    RMQ_URL_ENVAR_KEY_NAME,
    RMQ_PORT_ENVAR_KEY_NAME,
    RMQ_PASSWORD_ENVAR_KEY_NAME,
    RMQ_USERNAME_ENVAR_KEY_NAME,
    OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME,
    QDRANT_URL_ENVAR_KEY_NAME,
    QDRANT_HTTP_PORT_ENVAR_KEY_NAME,
    QDRANT_GRPC_PORT_ENVAR_KEY_NAME,
    QDRANT_COLLECTION_NAME_ENVAR_KEY_NAME,
    RESPONSE_ADDRESS_KEY,
    RESPONSE_TYPE_KEY,
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


def find_geocode_distance(goal: GeocodedAddress, given_coord: Optional[GeocodedAddress]):
    """
    Calculation is taken from
    https://medium.com/analytics-vidhya/finding-nearest-pair-of-latitude-and-longitude-match-using-python-ce50d62af546
    """
    from math import radians, cos, sin, asin, sqrt
    # Big value returned in case input coord is None.
    BIG_GEOCODE_DISTANCE = 1000

    if given_coord is None:
        return BIG_GEOCODE_DISTANCE

    earth_radius_km = 6371
    goal_longitude, goal_latitude = map(radians, [goal.longitude, goal.latitude])
    specific_longitude, specific_latitude = map(radians, [given_coord.longitude, given_coord.latitude])
    dlon = specific_longitude - goal_longitude
    dlat = specific_latitude - goal_latitude
    a = sin(dlat / 2) ** 2 + cos(goal_latitude) * cos(specific_latitude) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    km_distance = earth_radius_km * c
    return km_distance


class PythonService:
    def __init__(self):
        # =============== RMQ configuration ================
        self.rmq_url = os.getenv(RMQ_URL_ENVAR_KEY_NAME)
        self.rmq_username = os.getenv(RMQ_USERNAME_ENVAR_KEY_NAME)
        self.rmq_password = os.getenv(RMQ_PASSWORD_ENVAR_KEY_NAME)
        self.rmq_port = int(os.getenv(RMQ_PORT_ENVAR_KEY_NAME))
        self.retries = 0
        self.max_retries = 5
        self.last_try_time = None
        self.allowed_time_interval = 10

        output_connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rmq_url,
                port=self.rmq_port,
                credentials=pika.credentials.PlainCredentials(
                    username=self.rmq_username, password=self.rmq_password
                ),
            )
        )
        rmq_output_channel = output_connection.channel()
        output_queue_name = os.getenv(OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME)
        rmq_output_channel.queue_declare(queue=output_queue_name, durable=True)
        self.rmq_output_channel = rmq_output_channel

        input_connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rmq_url,
                port=self.rmq_port,
                credentials=pika.credentials.PlainCredentials(
                    username=self.rmq_username, password=self.rmq_password
                ),
            )
        )
        rmq_input_channel = input_connection.channel()
        input_queue_name = os.getenv(INPUT_QUEUE_NAME_ENVAR_KEY_NAME)
        rmq_input_channel.queue_declare(queue=input_queue_name, durable=True)
        rmq_input_channel.basic_consume(
            queue=input_queue_name,
            on_message_callback=self.handle_request_callback,
            auto_ack=True
        )
        self.rmq_input_channel = rmq_input_channel

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
        search_result = self.qdrant_client.search(
            collection_name=self.qdrant_collection_name,
            query_vector=embedding,
            query_filter=query_filter,
            limit=5
        )

        response = []
        for res in search_result:
            res_payload = res.payload

            res_payload_address = res_payload[RESPONSE_ADDRESS_KEY]
            try:
                address_geocode = self.transform_address_into_coordinates(res_payload_address)
            except Exception as e:
                address_geocode = None
                print(f"Failed to geocode location. Raised error {str(e)}")
            response.append(
                ServiceResponseBody(
                    res_payload_address,
                    res_payload[RESPONSE_NAME_KEY],
                    res_payload[RESPONSE_TYPE_KEY],
                    res_payload[RESPONSE_RATING_KEY],
                    res_payload[RESPONSE_TEXT_KEY],
                    address_geocode
                )
            )
        return response

    def send_response(self, serialized_response, output_queue_name, time):
        if time > self.max_retries:
            self.rmq_output_channel.basic_publish(
                exchange='',
                routing_key=output_queue_name,
                body=serialized_response
            )
            return
        try:
            self.rmq_output_channel.basic_publish(
                exchange='',
                routing_key=output_queue_name,
                body=serialized_response
            )
        except:
            output_connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rmq_url,
                    port=self.rmq_port,
                    credentials=pika.credentials.PlainCredentials(
                        username=self.rmq_username, password=self.rmq_password
                    ),
                )
            )
            rmq_output_channel = output_connection.channel()
            output_queue_name = os.getenv(OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME)
            rmq_output_channel.queue_declare(queue=output_queue_name, durable=True)
            self.rmq_output_channel = rmq_output_channel
            self.send_response(serialized_response, output_queue_name, time + 1)

    def handle_request_callback(self, ch, method, properties, body):
        request = ServiceRequest(**json.loads(body))
        print(f"Successfully get message: [{request}]")

        quadrant_response = self.search_db(request.message, request.town)
        # if request.location is not None:
        #     response_dataclasses.sort(key=lambda res: find_geocode_distance(request.location, res.))
        response = ServiceResponse(request.request_id, quadrant_response)
        serialized_response = ServiceResponse.schema().dumps(
            response, many=False
        )

        output_queue_name = os.getenv(OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME)
        self.send_response(serialized_response, output_queue_name, 0)

    def start_listening_input_query(self):
        self.last_try_time = time()
        while True:
            if self.retries > self.max_retries:
                self.rmq_input_channel.start_consuming()
                raise Exception("too mush retries")
            try:
                self.rmq_input_channel.start_consuming()
            except:
                print(f"error while listening")
                if time() - self.last_try_time > self.allowed_time_interval:
                    self.retries += 1
                else:
                    self.retries = 0

                input_connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self.rmq_url,
                        port=self.rmq_port,
                        credentials=pika.credentials.PlainCredentials(
                            username=self.rmq_username, password=self.rmq_password
                        ),
                    )
                )
                rmq_input_channel = input_connection.channel()
                input_queue_name = os.getenv(INPUT_QUEUE_NAME_ENVAR_KEY_NAME)
                rmq_input_channel.queue_declare(queue=input_queue_name, durable=True)
                rmq_input_channel.basic_consume(
                    queue=input_queue_name,
                    on_message_callback=self.handle_request_callback,
                    auto_ack=True
                )
                self.rmq_input_channel = rmq_input_channel



if __name__ == "__main__":
    service = PythonService()
    service.start_listening_input_query()
