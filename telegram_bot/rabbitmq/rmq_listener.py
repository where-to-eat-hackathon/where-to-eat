import pika
from typing import Callable
from time import time


def defaultCallback(ch, method, properties, body):
    print(f" [x] Received {body.decode(properties.content_encoding)} from output queue")


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
        self.retries = 0
        self.max_retries = 5
        self.last_try_time = None
        self.allowed_time_interval = 10
        self.queue = queue
        self.callback = callback
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=host, 
            port=int(port),
            credentials=pika.PlainCredentials(username=user, password=password),
        ))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue, durable=True)
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.callback, auto_ack=True)
        print(f"Set listener on queue with name: [{self.queue}]")
    
    def listen(self):
        self.last_try_time = time()
        while True:
            if self.retries > self.max_retries:
                self.channel.start_consuming()
            try:
                self.channel.start_consuming()
            except:
                print(f"error while listening")
                if time() - self.last_try_time > self.allowed_time_interval:
                    self.retries += 1
                else:
                    self.retries = 0
