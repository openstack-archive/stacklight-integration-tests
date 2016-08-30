#!/usr/bin/env python
from kafka import KafkaConsumer
from kafka import KafkaProducer

import logging
import threading
import time


LOG_FILENAME = '/tmp/log.txt'
logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)


class Producer(threading.Thread):
    daemon = True

    def run(self):
        producer = KafkaProducer(bootstrap_servers='localhost:9092')

        for i in xrange(5):
            producer.send('my-topic', str(i))
            time.sleep(1)


class Consumer(threading.Thread):
    daemon = True

    def run(self):
        l = []
        consumer = KafkaConsumer(bootstrap_servers='localhost:9092',
                                 auto_offset_reset='earliest',
                                 group_id='test_group')
        consumer.subscribe(['my-topic'])
        for message in consumer:
            l.append(message)
            if len(l) == 5:
                break
        try:
            assert(len(l) == 5)
        except AssertionError:
            logging.info("error")


def main():
    threads = [
        Producer(),
        Consumer()
    ]

    for t in threads:
        t.start()

    time.sleep(7)
    logging.info('this is a test')

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s.%(msecs)s:%(name)s:%'
                        '(thread)d:%(levelname)s:%(process)d:%(message)s',
                        level=logging.INFO, handlers=[logging.StreamHandler()])
    main()
