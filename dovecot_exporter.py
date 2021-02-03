#!/usr/bin/python3

from prometheus_client import REGISTRY, MetricsHandler, CollectorRegistry, Counter, write_to_textfile
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, Gauge, Counter, Metric, SummaryMetricFamily
import re
import time
import datetime
import json
from pprint import pprint
from http.server import HTTPServer
from urllib.parse import urlparse
import logging

PROMETHEUS_PORT = 8000
# JSON_REGEXP = re.compile(r'(\{.+\{.+\}\})')
UPDATE_PERIOD = 5


class CollectorHelper(object):
    _json_list = []
    __instance = None

    def __init__(self):
        if not CollectorHelper.__instance:
            print(" __init__ method called..")
        else:
            print("Instance already created:", self.getInstance())

    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            cls.__instance = CollectorHelper()
        return cls.__instance

    def set_json_list(self, parsed_json):
        self._json_list.append(parsed_json)

    def get_json_list(self):
        another_list = []
        test_list = [str(s) for s in self._json_list]
        for i in test_list:
            print(i)
            another_list.append(i)

        for i in self._json_list:
            print(i)
        return self._json_list

    def clear_json_list(self):
        print("Length before cleaning is {}".format(len(self._json_list)))
        self._json_list.clear()
        return "List has been erased. Length after cleaning is {}".format(len(self._json_list))


class DovecotHTTPHandler(MetricsHandler):
    helper = CollectorHelper.getInstance()

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-length']))
        self.helper.set_json_list(json.loads(body.decode('utf-8')))
        self._set_headers()
        # logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
        #             str(self.path), str(self.headers), body.decode('utf-8'))

    def do_GET(self):
        endpoint = urlparse(self.path).path
        if endpoint == '/metrics':
            return super(DovecotHTTPHandler, self).do_GET()
        else:
            self.send_response(404)


class JsonCollector(object):
    imap_commnads_counter = Counter('imap_commands_complete', 'Complete commands per user',
                                    ['user', 'complete_imap_commands'])

    bytes_in_counter = Counter('imap_bytes_in', 'Total incoming bytes per user', ['user', 'bytes_in'])
    bytes_out_counter = Counter('imap_bytes_out', 'Total outgoing bytes per user', ['user', 'bytes_out'])

    json_list = []

    def __init__(self, helper):
        self.helper = helper

    def collect(self):
        self.json_list = self.helper.get_json_list()
        counter = 0

        if self.json_list is None:
            pass
        else: 
            for data in self.json_list:
                # print("This is piece of json_list {}".format(data))
                fields = data.get('fields')

                # print('This is a one of some fields {}'.format(fields))

                # get values from corresponding fields
                user = fields['user']
                reply_status = fields['tagged_reply_state']
                bytes_in = fields['bytes_in']
                bytes_out = fields['bytes_out']

                """
                print(user)
                print(type(user))
                print(reply_status)
                print(bytes_in)
                print(bytes_out)
                """
                # seems like this section work as expected :wonder:
                self.imap_commnads_counter.labels(user, reply_status).inc()
                self.bytes_in_counter.labels(user, "bytes_in").inc(bytes_in)
                self.bytes_out_counter.labels(user, "bytes_out").inc(bytes_out)
                """
                imap_commands_metric = CounterMetricFamily("imap_commands_finished", "Imap commands finished",
                                             labels=['user', 'reply_status'])
                imap_commands_metric.add_metric(labels=[user, reply_status], value=2.5)
                # self.imap_commnads_counter.inc()

                yield imap_commands_metric
                imap_bytes_in_metric = CounterMetricFamily("imap_net_bytes_in", "Incoming imap bytes",
                                                           labels=['user', 'bytes_in'])
                imap_bytes_in_metric.add_metric(labels=[user, "bytes_in"], value=bytes_in)
                # imap_bytes_in_metric.add_metric(labels=[user, 'bytes_out'], value=bytes_out)
                yield imap_bytes_in_metric

                imap_bytes_out_metric = CounterMetricFamily("imap_net_bytes_out", "Outgoing imap bytes",
                                                           labels=['user', 'bytes_out'])
                imap_bytes_out_metric.add_metric(labels=[user, "bytes_out"], value=bytes_out)

                yield imap_bytes_out_metric
                """
                # I don't think we need any cleanups but it is better have one than no
                counter += 1

                if counter == len(self.json_list):
                    print(self.helper.clear_json_list())
                """
                self.imap_commnads_counter.labels(user=fields['user'], field='tagged_reply_state', status=fields['tagged_reply_state']).inc()
                pprint(ttttt)


            # pprint(self.c.collect())

            # custom_counter.labels(bytes_in=fields['bytes_in'], user=fields['user']).inc()

            # yield g
            metric = GaugeMetricFamily('dovecot_imap_commands',
                                       'Dovecot commands', labels=['reply_state', 'user'])

            metric.add_metric(labels={fields['tagged_reply_state'], fields['user']}, value=1)
            metric.add_sample('dovecot_user_commands_success',
                              value=fields['bytes_out'], labels={'user': fields['user']})
            metric.add_sample('dovecot_user_bytes_in_3',
                              value=fields['bytes_in'], labels={'user': fields['user']})
            yield metric




            summary = SummaryMetricFamily('dovecot_bytes', 'Dovecot network activities')

            summary.add_metric('dovecot_user_bytes_out',
                               count_value=fields['bytes_out'], sum_value=fields['bytes_out'])
            summary.add_metric('dovecot_user_bytes_in',
                               count_value=fields['bytes_in'], sum_value=fields['bytes_in'])

            summary.add_sample('dovecot_test_user_bytes_in', {'user': fields['user']}, value=fields['bytes_in'])
            summary.add_sample('dovecot_test_user_bytes_out', {'user': fields['user']}, value=fields['bytes_out'])
            """

            """
            yield summary
            """

def main():
    http_server = HTTPServer(('localhost', PROMETHEUS_PORT), DovecotHTTPHandler)
    helper = CollectorHelper.getInstance()
    logging.basicConfig(level=logging.INFO)
    try:
        """
        collector_helper = CollectorHelper()
        print(CollectorHelper.get_json_list())
        for i in collector_helper.get_json_list():
            print(i)

        custom_collector = JsonCollector(collector_helper.get_json_list())
        """
        REGISTRY.register(JsonCollector(helper))

        """
        collector_helper = CollectorHelper()
        custom_collector = JsonCollector(collector_helper.get_json_list())
        REGISTRY.register(custom_collector)
        REGISTRY.collect()
        """
        http_server.serve_forever(UPDATE_PERIOD)

    except KeyboardInterrupt:
        pass

    http_server.server_close()


if __name__ == '__main__':
    main()

    """
    # parse_log(LOG_FILE)
    # show_json_list(jsons_list)

    # start simple HTTP server which is receiving POST JSON from dovecot
    helper_server = HTTPServer(('localhost', HTTP_PORT), SimpleHTTPServer)

    helper_server.serve_forever()
    helper = CollectorHelper()
    json_list = helper.get_json_list()
    print((json_list))
    for i in json_list:
        print(i)
    # Start up the server to expose the metrics.
    
    start_http_server(PROMETHEUS_PORT)

    helper_server.serve_forever()
    helper = CollectorHelper()
    json_list = helper.get_json_list()
    REGISTRY.register(JsonCollector(json_list))

    while True:
        time.sleep(UPDATE_PERIOD)

def parse_log(log_file):
    with open(log_file, encoding='utf-8', errors='ignore') as fp:
        for line in fp:
            match_json = re.search(JSON_REGEXP, line)
            if match_json is None:
                continue
            else:
                json_part = match_json.group(0)
                # print(json_part)
                parsed_json = json.loads(json_part)
                jsons_list.append(parsed_json)


class SimpleServer(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        self._set_headers()
        body = self.rfile.read(int(self.headers['Content-length']))
        qs = parse_qs(body.decode('utf-8'))
        for k in qs.keys():
            print("The key has type" + str(type(k)))
            keys = k.split('\t')
            for key in keys:
                print(key)

        for v in qs.values():
            print("The value has type" + str(type(v)))
            val_list = v[0].split('\t')
            for value in val_list:
                print(value)




try:
    start_http_server(8000)
    server = HTTPServer(('localhost', HTTP_PORT), SimpleServer)
    print('Started http server on port {}'.format(HTTP_PORT))

    server.serve_forever()

except KeyboardInterrupt:
    print('^C received, shutting down the web server')

    server.socket.close()
"""
