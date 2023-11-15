import pika


def test_send(queue_name, request_id, msg):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # channel.queue_declare(queue=queue_name)
    message = {'request_id': request_id, 'message': msg}
    channel.basic_publish(exchange='', routing_key=queue_name, body=str(message))
    print(" [x] Send 'Hello World!'")
    connection.close()


def recive(queue_name):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # channel.queue_declare(queue=queue_name)

    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


def test_recive(queue_name):
    try:
        recive(queue_name)
    except KeyboardInterrupt:
        print('Interrupted')
