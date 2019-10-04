import argparse
import microgear.client as microgear
import logging


def start_netpie(key, secret, appid, on_message=None, debug=False):
    microgear.create(key, secret, appid, {'debugmode': debug})

    def on_connect():
        logging.info("Now I am connected with netpie")

    def _on_message(topic, message):
        logging.info(topic + " -> " + message)

        on_message(topic, message[2:-1])

    def on_disconnect():
        logging.info("disconnected")

    microgear.setalias("people_counter")
    microgear.on_connect = on_connect
    microgear.on_message = _on_message
    microgear.on_disconnect = on_disconnect

    microgear.subscribe("/iot")

    microgear.connect(True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="NETPIE key")
    ap.add_argument("--secret", required=True, help="NETPIE secret")
    ap.add_argument("--appid", required=True, help="NETPIE appid")
    args = vars(ap.parse_args())

    start_netpie(args['key'], args['secret'], args['appid'], debug=True)
