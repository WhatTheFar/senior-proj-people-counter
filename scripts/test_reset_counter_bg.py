import argparse
import microgear.client as client
import time


def connection():
    print("Now I am connected with netpie")


def subscription(topic, message):
    print(topic + " " + message)


if __name__ == '__main__':
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="NETPIE key")
    ap.add_argument("--secret", required=True, help="NETPIE secret")
    ap.add_argument("--appid", required=True, help="NETPIE appid")
    args = vars(ap.parse_args())

    client.create(args['key'], args['secret'],
                  args['appid'], {'debugmode': True})

    client.setname("test_reset_counter_bg")
    client.on_connect = connection
    client.on_message = subscription
    client.subscribe("/people/bg")

    client.connect()

    while True:
        client.publish("/people/bg", "Hello world. " + str(int(time.time())))
        time.sleep(20)
