import pika


class RMQSender:
    def __init__(
        self, 
        queue: str, 
        host: str, 
        port: str, 
        user: str, 
        password: str,
    ) -> None:
        self.queue = queue
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=host, 
            port=port, 
            credentials=pika.PlainCredentials(username=user, password=password),
        ))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue, durable=True)

    def send_message(self, request_id: int, msg: str) -> None:
        message = {'request_id': request_id, 'message': msg}
        self.channel.basic_publish(exchange='',
                                   routing_key=self.queue,
                                   body=str(message),
                                   properties=pika.BasicProperties(
                                       content_encoding='utf-8',
                                       delivery_mode=1,
                                   ))

    def close_connection(self) -> None:
        self.connection.close()
