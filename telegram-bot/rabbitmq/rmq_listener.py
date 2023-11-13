import pika
from typing import Callable

def defaultCallback(ch, method, properties, body):
    print(f" [x] Received {body}")

class RMQListener:
    def __init__(
        self, 
        queue: str, 
        host: str, 
        port: str, 
        user: str, 
        password: str,
        callback: Callable = defaultCallback
    ) -> None:
        self.queue = queue
        self.callback = callback
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=host, 
            port=port,
            credentials=pika.PlainCredentials(username=user, password=password),
        ))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue, durable=True)
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.callback, auto_ack=True)
    
    def listen(self):
        self.channel.start_consuming()
