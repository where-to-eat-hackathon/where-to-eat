# ENVIRONMENT VARIABLES.
from dataclasses import dataclass
from typing import Optional, List

from dataclasses_json import dataclass_json

RMQ_URL_ENVAR_KEY_NAME = "RMQ_URL"
# Queue that accepts requests FROM Telegram bot.
RMQ_INPUT_PORT_ENVAR_KEY_NAME = "RMQ_INPUT_PORT"
INPUT_QUEUE_NAME_ENVAR_KEY_NAME = "INPUT_QUEUE_NAME"
# Queue that accepts requests FOR Telegram bot.
RMQ_OUTPUT_PORT_ENVAR_KEY_NAME = "RMQ_OUTPUT_PORT"
OUTPUT_QUEUE_NAME_ENVAR_KEY_NAME = "OUTPUT_QUEUE_NAME"
RMQ_USERNAME_ENVAR_KEY_NAME = "RMQ_USERNAME"
RMQ_PASSWORD_ENVAR_KEY_NAME = "RMQ_PASSWORD"
QDRANT_URL_ENVAR_KEY_NAME = "QDRANT_URL"
QDRANT_HTTP_PORT_ENVAR_KEY_NAME = "QDRANT_HTTP_PORT"
QDRANT_GRPC_PORT_ENVAR_KEY_NAME = "QDRANT_GRPC_PORT"
QDRANT_COLLECTION_NAME_ENVAR_KEY_NAME = "QDRANT_COLLECTION_NAME"

# QDRANT COLLECTION FIELDS (also used as JSON fields).
RESPONSE_ADDRESS_KEY = "address"
RESPONSE_NAME_KEY = "name"
RESPONSE_TYPE_KEY = "rubrics"
RESPONSE_RATING_KEY = "rating"
RESPONSE_TEXT_KEY = "text"


@dataclass_json
@dataclass
class GeocodedAddress:
    """Text address transformed into coordinates."""

    latitude: float
    longitude: float


@dataclass_json
@dataclass
class ServiceRequest:
    """Request from service."""

    request_id: int
    message: str
    town: Optional[str] = None
    location: Optional[GeocodedAddress] = None


@dataclass_json
@dataclass
class ServiceResponseBody:
    address: str
    name: str
    type: List[str]
    rating: float
    comment: str
    geocode: Optional[GeocodedAddress] = None


@dataclass_json
@dataclass
class ServiceResponse:
    """Response from service."""

    request_id: int
    body: List[ServiceResponseBody]
