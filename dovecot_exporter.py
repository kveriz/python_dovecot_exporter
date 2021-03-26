#!/usr/bin/python3

from prometheus_client import MetricsHandler, Counter, Gauge, Histogram, Summary
import json
from http.server import HTTPServer
from urllib.parse import urlparse
from argparse import ArgumentParser
import configparser
import logging
import os


class DovecotMetricsHandler(object):
    __instance = None

    # group of IMAP metrics and thing connected with it
    imap_complete_commands = Counter('dovecot_imap_commands_finished', 'Complete IMAP dovecot commands', ['user', 'reply_state'])
    imap_bytes_in = Counter('dovecot_imap_bytes_in', 'Dovecot IMAP bytes in', labelnames=['user'])
    imap_bytes_out = Counter('dovecot_imap_bytes_out', 'Dovecot IMAP bytes out', labelnames=['user'])
    imap_running_usecs = Counter('dovecot_imap_running_usecs', 'Dovecot IMAP usecs was spent by IMAP cmd', ['user', 'cmd_name'])

    # group of local delivery(LMTP) metrics
    lmtp_complete_commands = Counter('dovecot_mail_delivery_finished', 'Complete LMTP dovecot commands ', ['user'])
    lmtp_received_messages_size = Counter('dovecot_mail_delivery_messages_size', 'Received LMTP messages size ', ['user'])

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DovecotMetricsHandler, cls).__new__(cls)
        return cls.instance

    def auth_handler(self, json_data):
        logging.info("Within handler {}: {}".format(self.auth_handler.__name__, json_data))
        pass

    def imap_handler(self, json_data):
        logging.info("Within handler {}: {}".format(self.imap_handler.__name__, json_data))
        fields = json_data['fields']

        user = fields['user']
        reply_state = fields['tagged_reply_state']
        bytes_in = fields['bytes_in']
        bytes_out = fields['bytes_out']
        running_usecs = fields['running_usecs']
        cmd_name = fields['cmd_name']

        self.imap_complete_commands.labels(user, reply_state).inc()
        self.imap_bytes_in.labels(user).inc(bytes_in)
        self.imap_bytes_out.labels(user).inc(bytes_out)
        self.imap_running_usecs.labels(user, cmd_name).inc(running_usecs)

    def lmtp_handler(self, json_data):
        logging.info("Within handler {}: {}".format(self.lmtp_handler.__name__, json_data))
        fields = json_data['fields']

        user = fields['user']
        message_size = fields['message_size']

        self.lmtp_complete_commands.labels(user).inc()
        self.lmtp_received_messages_size.labels(user).inc(message_size)

    def sieve_handler(self, json_data):
        logging.info("Within handler {}: {}".format(self.sieve_handler.__name__, json_data))
        pass


class DovecotHTTPHandler(MetricsHandler):
    """
    This is a prototype of dovecot's metrics exporter.

    You can enable debugging by the adding DEXPORTER_DEBUG variable into yours environment
    or simply in command line before exporter name
    """
    HELPER = DovecotMetricsHandler()

    event_switch = {
        'imap': lambda json_data: DovecotHTTPHandler.HELPER.imap_handler(json_data),
        'mail': lambda json_data: DovecotHTTPHandler.HELPER.lmtp_handler(json_data),
        'sieve': lambda json_data: DovecotHTTPHandler.HELPER.sieve_handler(json_data),
        'auth': lambda json_data: DovecotHTTPHandler.HELPER.auth_handler(json_data),
    }

    # it's very complicated thing below, but I'll keep it just in case
    """
    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        self.arg = self.get_args()
        super().__init__(request, client_address, server)
    """
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _get_event_type(self, event_fqn):
        return event_fqn.split('_')[0]

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-length']))
        self._set_headers()
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), body.decode('utf-8'))

        data = json.loads(body.decode('utf-8'))

        # prepare needed fields
        logging.info("It's whole data: {}".format(data))
        event_type = self._get_event_type(data['event'])
        logging.info("Event type is: {}".format(event_type))

        fields = data['fields']
        user = fields['user']

        # we may use fqdn in some metrics, because a lot of users exist
        fqdn = user.split('@')[1]

        logging.info("It's a useful data: {}".format(fields))

        # self.event_switch[event](data)

        event_handler = [value for key, value in self.event_switch.items() if event_type in key.lower()]
        logging.info(dir(event_handler))
        logging.info("event_handler is {}: ".format(type(event_handler)))

        event_handler[0](data)

    def do_GET(self):
        endpoint = urlparse(self.path).path
        if endpoint == '/metrics':
            return super(DovecotHTTPHandler, self).do_GET()
        else:
            self.send_response(404)


def main():
    conf_file = os.path.join(os.path.abspath('/etc/dovecot_exporter/'), "exporter.ini")

    config = configparser.ConfigParser()
    config.read(conf_file)
    address = config['main']['bind_address']
    port = int(config['main']['port'])
    update_period = int(config['main']['update_period'])

    http_server = HTTPServer((address, port), DovecotHTTPHandler)
    if os.getenv('DEXPORTER_DEBUG') is not None:
        logging.basicConfig(level=logging.INFO)
    try:
        http_server.serve_forever(update_period)
    except KeyboardInterrupt:
        pass
    http_server.server_close()


if __name__ == '__main__':
    main()
