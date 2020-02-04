import argparse
import microgear.client as microgear
import logging
import logging.handlers

from constant import NETPIE_LOGGER


def netpie_process(log_queue, key, secret, appid, topics=None, on_message=None, debug=False):
    h = logging.handlers.QueueHandler(log_queue)  # Just the one handler needed
    root_logger = logging.getLogger()
    root_logger.addHandler(h)
    # send all messages, for demo; no other level or filter logic applied.
    root_logger.setLevel(logging.DEBUG)

    start_netpie(key, secret, appid, topics=topics, on_message=on_message, debug=debug)


def start_netpie(key, secret, appid, topics=None, on_message=None, debug=False):
    logger = logging.getLogger(NETPIE_LOGGER)
    microgear.create(key, secret, appid, {'debugmode': debug})

    def on_connect():
        logger.info("Now I am connected with netpie")

    def _on_message(topic, message):
        logger.info(topic + " -> " + message)

        on_message(topic, message[2:-1])

    def on_disconnect():
        logger.info("disconnected")

    microgear.setalias("people_counter")
    microgear.on_connect = on_connect
    microgear.on_message = _on_message
    microgear.on_disconnect = on_disconnect

    for topic in topics:
        microgear.subscribe(topic)

    microgear.connect(True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="NETPIE key")
    ap.add_argument("--secret", required=True, help="NETPIE secret")
    ap.add_argument("--appid", required=True, help="NETPIE appid")
    args = vars(ap.parse_args())

    start_netpie(args['key'], args['secret'], args['appid'], debug=True)
