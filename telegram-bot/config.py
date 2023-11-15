import os


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

rmq_place_description_queue = os.getenv('RMQINQUEUE')  # place_description
if rmq_place_description_queue is None:
    raise Exception('rmq place_description queue  is not provided')

rmq_place_suggestion_queue = os.getenv('RMQOUTQUEUE')  # place_suggestion
if rmq_place_suggestion_queue is None:
    raise Exception('rmq place_suggestion queue  is not provided')


answer_delay_sec = 12
if "ANSWER_DELAY_SEC" in os.environ:
    answer_delay_sec = int(os.getenv("ANSWER_DELAY_SEC"))

BOT_TOKEN = ""
if "BOT_TOKEN" in os.environ:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_LINK = ""
if "BOT_LINK" in os.environ:
    BOT_LINK = os.getenv("BOT_LINK")