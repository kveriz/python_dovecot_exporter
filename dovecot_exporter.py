#!/usr/bin/python3

from prometheus_client import MetricsHandler, Counter
import json
from http.server import HTTPServer
from urllib.parse import urlparse
import configparser
import logging
import os


class DovecotMetricsHandler(object):
    __instance = None

    def __init__(self) -> None:
        pass

    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            cls.__instance = DovecotMetricsHandler
        return cls.__instance

    """
    def prepare_metric(self, event):
        event_name = event['event']
        fields = event['fields']

        user = fields['user']
        if event_name.contains('imap'):
            reply_status = fields['tagged_reply_state']
            bytes_in = fields['bytes_in']
            bytes_out = fields['bytes_out']
            running_usecs = fields['running_usecs']
            cmd_name = fields['cmd_name']
        else:
            user = fields['user']
            message_size = fields['message_size']
    """

class DovecotHTTPHandler(MetricsHandler):
    helper = DovecotMetricsHandler.getInstance()

    # group of IMAP metrics and thing connected with it
    imap_complete_commands = Counter('dovecot_imap_commands_finished', 'Complete IMAP dovecot commands', ['user', 'reply_state'])
    imap_bytes_in = Counter('dovecot_imap_bytes_in', 'Dovecot IMAP bytes in', labelnames=['user'])
    imap_bytes_out = Counter('dovecot_imap_bytes_out', 'Dovecot IMAP bytes out', labelnames=['user'])
    imap_running_usecs = Counter('dovecot_imap_running_usecs', 'Dovecot IMAP usecs was spent by IMAP cmd', labelnames=['user', 'cmd_name'])

    # group of local delivery(LMTP) metrics
    lmtp_complete_commands = Counter('dovecot_mail_delivery_finished', 'Complete LMTP dovecot commands ', ['user'])
    lmtp_received_messages_size = Counter('dovecot_mail_delivery_messages_size', 'Received LMTP messages size ', ['user'])

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-length']))
        self._set_headers()
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), body.decode('utf-8'))

        data = json.loads(body.decode('utf-8'))

        # prepare needed fields
        logging.info("It's whole data: {}".format(data))
        event = data['event']

        logging.info(event)
        fields = data['fields']
        user = fields['user']

        logging.info("It's data: {}".format(fields))

        if event == 'imap_command_finished':
            reply_state = fields['tagged_reply_state']
            bytes_in = fields['bytes_in']
            bytes_out = fields['bytes_out']
            running_usecs = fields['running_usecs']
            cmd_name = fields['cmd_name']

            self.imap_complete_commands.labels(user, reply_state).inc()
            self.imap_bytes_in.labels(user).inc(bytes_in)
            self.imap_bytes_out.labels(user).inc(bytes_out)
            self.imap_running_usecs.labels(user, cmd_name).inc(running_usecs)

        if event == 'mail_delivery_finished':
            message_size = fields['message_size']

            self.lmtp_complete_commands.labels(user).inc()
            self.lmtp_received_messages_size.labels(user).inc(message_size)

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
    # logging.basicConfig(level=logging.INFO)
    try:
        http_server.serve_forever(update_period)
    except KeyboardInterrupt:
        pass
    http_server.server_close()


if __name__ == '__main__':
    main()
