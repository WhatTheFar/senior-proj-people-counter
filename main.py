import argparse
import ctypes
from logging.handlers import TimedRotatingFileHandler
import logging
import multiprocessing as mp
from datetime import datetime

import dateutil.parser
import requests

import counter_utils
import netpie_utils
from constant import MAIN_LOGGER, COUNTER_LOGGER

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
    log_queue = mp.Queue(-1)


    def log_listener_process(queue):
        root_logger = logging.getLogger()
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        logging_handlers = []
        if args['debug'] is True:
            # handler = logging.StreamHandler()
            handler = TimedRotatingFileHandler('./log/test.log', when="m", interval=2)
            handler.setFormatter(log_formatter)
            handler.setLevel(logging.DEBUG)

            logging_handlers.append(handler)
        else:
            handler = TimedRotatingFileHandler('./log/app.log', when="midnight", interval=1)
            handler.setLevel(logging.INFO)
            handler.setFormatter(log_formatter)

            logging_handlers.append(handler)

        for handler in logging_handlers:
            root_logger.addHandler(handler)

        while True:
            try:
                record = queue.get()
                if record is None:  # We send this as a sentinel to tell the listener to quit.
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record)  # No level or filter logic applied - just do it!

            except Exception:
                import sys, traceback
                print('Whoops! Problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)


    def log_queue_configure_hoc(queue, func):
        def with_logger(*func_args):
            h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
            root_logger = logging.getLogger()
            root_logger.addHandler(h)
            # send all messages, for demo; no other level or filter logic applied.
            # root_logger.setLevel(logging.DEBUG)

            func(*func_args)

        return with_logger


    def log_queue_configure(queue):
        h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
        root_logger = logging.getLogger()
        root_logger.addHandler(h)
        # send all messages, for demo; no other level or filter logic applied.
        # root_logger.setLevel(logging.DEBUG)


    people_count_value = mp.Value(ctypes.c_int, 0)
    should_reset_bg_value = mp.Value(ctypes.c_bool, False)


    def on_people_count(people_diff):
        logger = logging.getLogger(COUNTER_LOGGER)
        with people_count_value.get_lock():
            people_count_value.value += people_diff
            logger.info("People Count: {}".format(people_count_value.value))
            return people_count_value.value


    def check_should_reset_bg():
        with should_reset_bg_value.get_lock():
            tmp = should_reset_bg_value.value
            if tmp is True:
                should_reset_bg_value.value = False
            return tmp


    def on_message(topic, message):
        if topic == '/seniorproj/iot':
            logger = logging.getLogger(MAIN_LOGGER)
            people_count = people_count_value.value
            date = dateutil.parser.parse(message)
            now = datetime.utcnow()

            if now.timestamp() - date.timestamp() > 3:
                logger.info('POST People -> Ignored at {}'.format(now.isoformat()))
                return

            if args["dry_run"]:
                logger.info('POST People -> Ignored by --dry-run')
                return

            for i in range(1, 4):
                try:
                    resp = requests.post(f'{args["server_url"]}/iot/sensor/people', json={
                        "date": message,
                        "actualDate": now.isoformat(),
                        "people": people_count,
                    })
                    if resp.status_code == 201:
                        logger.info('POST People -> Success')
                        break
                    elif resp.status_code == 400:
                        logger.error("POST People -> Bad Request: {}".format(resp.json()))
                        break

                except Exception as e:
                    logger.exception("POST People -> Exception occurred")

                logger.info('POST People -> Retry attempt #{}'.format(i))
                continue

        elif topic == '/seniorproj/people/bg':
            should_reset_bg_value.value = True

        elif topic == '/seniorproj/people/set':
            people_count_value.value = int(message)


    logger_process = mp.Process(target=log_listener_process, args=(log_queue,))
    netpie_process = mp.Process(target=netpie_utils.netpie_process,
                                args=(
                                    log_queue,
                                    args['key'],
                                    args['secret'],
                                    args['appid'],
                                    ['/iot', '/people/bg', '/people/set'],
                                    on_message,
                                    args['debug'],))

    logger_process.start()
    netpie_process.start()

    counter_utils.counter_process(log_queue,
                                  video=args['video'],
                                  debug=args['debug'],
                                  output=args['output'],
                                  use_pi_camera=args['pi'],
                                  on_people_count=on_people_count,
                                  check_should_reset_bg=check_should_reset_bg)

    logger_process.terminate()
    netpie_process.terminate()
