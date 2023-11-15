import os
import sys
from rabbitmq import RMQListener, RMQSender

def main():
    rmq_host = os.getenv('RMQHOST')
    if rmq_host is None:
        raise Exception('rmq host is not provided')
    
    rmq_port = os.getenv('RMQPORT')
    if rmq_port is None:
        raise Exception('rmq port is not provided')
    
    rmq_user = os.getenv('RMQUSER')
    if rmq_user is None:
        raise Exception('rmq user is not provided')
    
    rmq_password = os.getenv('RMQPASSWORD')
    if rmq_password is None:
        raise Exception('rmq password is not provided')

    rmq_place_description_queue = os.getenv('RMQINQUEUE') #place_description
    if rmq_place_description_queue is None:
        raise Exception('rmq place_description queue  is not provided')
    
    rmq_place_suggestion_queue = os.getenv('RMQOUTQUEUE') #place_suggestion
    if rmq_place_suggestion_queue is None:
        raise Exception('rmq place_suggestion queue  is not provided')

    rmq_sender = RMQSender(
        queue=rmq_place_description_queue,
        host=rmq_host,
        port=rmq_port,
        user=rmq_user,
        password=rmq_password,
    )

    rmq_listener = RMQListener(
        queue=rmq_place_suggestion_queue,
        host=rmq_host,
        port=rmq_port,
        user=rmq_user,
        password=rmq_password,
    )

    try:
        rmq_listener.listen()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main()
