from typing import Optional

import pika
import json


class RMQSender:

    def __init__(
        self,
        queue: str,
        host: str,
        port: str,
        user: str,
        password: str,
    ) -> None:
        self.retries = 0
        self.max_retries = 5
        self.queue = queue
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=host,
                port=int(port),
                credentials=pika.PlainCredentials(username=user,
                                                  password=password),
            ))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue, durable=True)

    def send_message(self, request_id: int, msg: str, town: Optional[str]) -> None:
        message = {'request_id': request_id, 'message': msg, "town": town}
        if self.retries > self.max_retries:
            print(f'too much fails')
            self.channel.basic_publish(exchange='',
                                       routing_key=self.queue,
                                       body=json.dumps(message),
                                       properties=pika.BasicProperties(
                                           content_encoding='utf-8',
                                           delivery_mode=1,
                                       ))

        try:
            self.channel.basic_publish(exchange='',
                                       routing_key=self.queue,
                                       body=json.dumps(message),
                                       properties=pika.BasicProperties(
                                           content_encoding='utf-8',
                                           delivery_mode=1,
                                       ))
        except:
            print(f"exception while message publishing")
            self.retries += 1
            self.send_message(request_id, msg, town)
        print(f"Sent message to the input queue: [{msg}]")
        print(f"Input queue name: [{self.queue}]")
        self.retries = 0

    def close_connection(self) -> None:
        self.connection.close()
