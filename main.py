import argparse
import ctypes
from logging.handlers import RotatingFileHandler
import logging
import multiprocessing as mp
from datetime import datetime

import dateutil.parser
import requests

import counter_utils
import netpie_utils

if __name__ == '__main__':
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="NETPIE key")
    ap.add_argument("--secret", required=True, help="NETPIE secret")
    ap.add_argument("--appid", required=True, help="NETPIE appid")

    ap.add_argument("--server-url", required=True, help="backend server url")

    ap.add_argument("-d", "--debug", default=False, action="store_true", help="non-headless and wait for key")
    ap.add_argument("--dry-run", default=False, action="store_true", help="dry-run")

    ap.add_argument("-v", "--video", help="path to the video file")
    ap.add_argument("--pi", "--use-pi-camera", default=False, action="store_true", help="use Pi camera")
    ap.add_argument("-o", "--output", type=str, help="path to optional output video file")
    args = vars(ap.parse_args())

    # initialize logging configuration
    logging_handlers = []
    if args['debug'] is True:
        logging_level = logging.DEBUG
        logging_handlers.append(logging.StreamHandler())
    else:
        logging_level = logging.INFO
        logging_handlers.append(RotatingFileHandler('./log/app.log', maxBytes=1000000, backupCount=40))

    logging.basicConfig(level=logging_level,
                        handlers=logging_handlers,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    people_count_value = mp.Value(ctypes.c_int, 0)
    should_reset_bg_value = mp.Value(ctypes.c_bool, False)


    def on_people_count(people_diff):
        with people_count_value.get_lock():
            people_count_value.value += people_diff
            logging.info("People Count: {}".format(people_count_value.value))
            return people_count_value.value


    def check_should_reset_bg():
        with should_reset_bg_value.get_lock():
            tmp = should_reset_bg_value.value
            if tmp is True:
                should_reset_bg_value.value = False
            return tmp


    def on_message(topic, message):
        if topic == '/seniorproj/iot':
            people_count = people_count_value.value
            date = dateutil.parser.parse(message)
            now = datetime.utcnow()

            if now.timestamp() - date.timestamp() > 3:
                logging.info('POST People -> Ignored at {}'.format(now.isoformat()))
                return

            if args["dry_run"]:
                logging.info('POST People -> Ignored by --dry-run')
                return

            for i in range(1, 4):
                try:
                    resp = requests.post(f'{args["server_url"]}/iot/sensor/people', json={
                        "date": message,
                        "actualDate": now.isoformat(),
                        "people": people_count,
                    })
                    if resp.status_code == 201:
                        logging.info('POST People -> Success')
                        break
                    elif resp.status_code == 400:
                        logging.error("POST People -> Bad Request: {}".format(resp.json()))
                        break

                except Exception as e:
                    logging.exception("POST People -> Exception occurred")

                logging.info('POST People -> Retry attempt #{}'.format(i))
                continue

        elif topic == '/seniorproj/people/bg':
            should_reset_bg_value.value = True

        elif topic == '/seniorproj/people/set':
            people_count_value.value = int(message)


    netpie_process = mp.Process(target=netpie_utils.start_netpie,
                                args=(
                                    args['key'],
                                    args['secret'],
                                    args['appid'],
                                    ['/iot', '/people/bg', '/people/set'],
                                    on_message,
                                    args['debug'],))
    netpie_process.start()

    counter_utils.start_simple_counter(video=args['video'],
                                       debug=args['debug'],
                                       output=args['output'],
                                       use_pi_camera=args['pi'],
                                       on_people_count=on_people_count,
                                       check_should_reset_bg=check_should_reset_bg)

    netpie_process.terminate()
