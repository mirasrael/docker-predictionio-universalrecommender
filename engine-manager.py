#!/usr/bin/env python
import BaseHTTPServer
import SocketServer
import shutil
import subprocess
import sys
import tempfile
import urlparse
from cgi import parse_header
from subprocess import CalledProcessError

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

ip = "0.0.0.0"
port = 9500
app_id = "1"
work_dir = "/home/predictionio/ur"
driver_memory = "4G"
executor_memory = "4G"

__version__ = "0.1"

print("Staring Prediction.IO Engine Manager...")


# noinspection PyPep8Naming
class EngineManagerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = 'PredictionIOEngineManager/' + __version__

    def do_GET(self):
        parts = urlparse.urlsplit(self.path)
        if parts.path == '/apps':
            self.send_command_output(["pio", "app", "list"])
            return
        self.send_not_found()

    def do_POST(self):
        parts = urlparse.urlsplit(self.path)
        if parts.path == '/app/deploy':
            subprocess.Popen(["pio", "deploy"])
            return self.send_content("Deploy initiated")
        elif parts.path == "/app/train":
            return self.send_command_output(
                ["pio", "train", "--", "--driver-memory", driver_memory, "--executor-memory", executor_memory])
        elif parts.path == "/app/seed":
            return self.handle_app_seed()

        self.send_not_found()

    def get_content(self):
        ctype, pdict = parse_header(self.headers['content-type'])
        if ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            content = self.rfile.read(length)
        else:
            content = None

        return content

    def handle_app_seed(self):
        content = self.get_content()
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.file.write(content)
            tmp.file.flush()
            self.send_command_output(["pio", "import", "--appid", app_id, "--input", tmp.name])

    def send_not_found(self):
        self.send_response(404)
        self.end_headers()

    def send_server_error(self, message=""):
        self.send_content(message, "text/html", 500)

    def send_command_output(self, cmd):
        try:
            self.send_content(subprocess.check_output(cmd, cwd=work_dir))
        except CalledProcessError:
            self.send_server_error()
        except WindowsError:
            self.send_server_error()

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
