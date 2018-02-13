#!/usr/bin/env python
import BaseHTTPServer
import SocketServer
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

ip = "0.0.0.0"
port = 9500
app_id = os.environ['PIO_APP_ID']
work_dir = "/home/predictionio/ur"
driver_memory = "4G"
executor_memory = "4G"

__version__ = "0.1"

print("Staring Prediction.IO Engine Manager...")


# noinspection PyPep8Naming
class EngineManagerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'PredictionIOEngineManager/' + __version__

    def do_GET(self):
        parts = urlparse.urlsplit(self.path)
        if parts.path == '/apps':
            self.send_command_output(["pio", "app", "list"])
            return
        self.send_not_found()

    def do_POST(self):
        try:
            parts = urlparse.urlsplit(self.path)
            if parts.path == '/app/deploy':
                subprocess.Popen(["pio", "deploy"])
                return self.send_content("Deploy initiated")
            elif parts.path == "/app/train":
                return self.send_command_output(
                    ["pio", "train", "--", "--driver-memory", driver_memory, "--executor-memory", executor_memory])
            elif parts.path == "/app/seed":
                return self.handle_app_seed()
        except StandardError as ex:
            traceback.print_exc()
            self.send_server_error(ex.message)
            return

        self.send_not_found()

    def copy_chunked_body(self, dest):
        while True:
            chunk_size = ''
            while True:
                ch = self.rfile.read(1)
                if ch == '\r':
                    break
                chunk_size += ch
            chunk_size = int(chunk_size or '0', 16)
            # zero indicates last chunk
            if chunk_size == 0:
                return
            # by protocol definition it should use CRLF as separator
            if self.rfile.read(1) != '\n':
                raise ValueError("Invalid new line indicator for chunk size")
            dest.write(self.rfile.read(chunk_size))
            if self.rfile.read(1) != '\r' and self.rfile.read(1) != '\n':
                raise ValueError("Invalid new line indicator after chunk")

    def handle_app_seed(self):
        tmp_file_name = tempfile.mktemp()
        try:
            with open(tmp_file_name, 'wb') as tmp:
                content_length = int(self.headers.get('content-length', '-1'))
                if self.headers.get('transfer-encoding') == "chunked":
                    self.copy_chunked_body(tmp)
                elif content_length >= 0:
                    tmp.write(self.rfile.read(content_length))
                else:
                    self.send_server_error("Can't determine content-length")

            self.send_command_output(["pio", "import", "--appid", app_id, "--input", tmp_file_name])
        finally:
            os.unlink(tmp_file_name)

    def send_not_found(self):
        self.send_response(404)
        self.end_headers()

    def send_server_error(self, message=""):
        self.send_content(message, "text/html", 500)

    def send_command_output(self, cmd):
        self.send_content(subprocess.check_output(cmd, cwd=work_dir))

    def send_json(self, json):
        self.send_content(json, "application/json")

    def send_content(self, content, mime_type="text/html", status_code=200):
        f = StringIO()
        f.write(content)
        length = f.tell()
        f.seek(0)
        self.send_response(status_code)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-Type", "%s; charset=%s" % (mime_type, encoding))
        self.send_header("Content-Length", str(length))
        self.end_headers()
        try:
            shutil.copyfileobj(f, self.wfile)
        finally:
            f.close()


httpd = SocketServer.TCPServer((ip, port), EngineManagerHandler)

print("Prediction.IO Engine Manager listening: {}:{}".format(ip, port))
httpd.serve_forever()