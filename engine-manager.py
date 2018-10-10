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
app_name = os.environ['PIO_APP_NAME']
app_id = os.environ['PIO_APP_ID']
work_dir = "/home/predictionio/ur"
driver_memory = os.environ.get('PIO_DRIVER_MEMORY', '1G')
executor_memory = os.environ.get('PIO_EXECUTOR_MEMORY', '1G')

__version__ = "0.2.0"

print("Starting Prediction.IO Engine Manager...")


# noinspection PyPep8Naming
class EngineManagerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'PredictionIOEngineManager/' + __version__
    deploy_process = None
    handling = False

    def do_GET(self):
        parts = urlparse.urlsplit(self.path)
        if parts.path == '/apps':
            self.send_command_output(["pio", "app", "list"])
            return
        self.consume_and_ignore_request_body()
        self.send_not_found()

    def do_POST(self):
        if EngineManagerHandler.handling:
            self.consume_and_ignore_request_body()
            return self.send_error(409, "Another operation in progress")

        EngineManagerHandler.handling = True
        try:
            parts = urlparse.urlsplit(self.path)
            self.log_message("Processing command: %s...", parts.path)
            if parts.path == '/app/deploy':
                return self.send_content(self.deploy())
            elif parts.path == "/app/train":
                return self.send_content(self.train())
            elif parts.path == "/app/import":
                return self.send_content(self.handle_import_data())
            elif parts.path == "/app/data-delete":
                return self.send_content(self.data_delete())
            elif parts.path == "/app/update-with-data" or parts.path == "/app/init-with-data":
                self.start_chunked_response()
                try:
                    if parts.path == "/app/init-with-data":
                        self.write_chunk("Cleanup...")
                        self.write_chunk(self.data_delete())
                    self.write_chunk("Import...")
                    self.write_chunk(self.handle_import_data())
                    self.write_chunk("Train...")
                    self.write_chunk(self.train())
                    self.write_chunk("Deploy...")
                    self.write_chunk(self.deploy())
                finally:
                    self.end_chunked_response()
                return
        except StandardError as ex:
            traceback.print_exc()
            return self.send_server_error(ex.message)
        finally:
            EngineManagerHandler.handling = False

        self.consume_and_ignore_request_body()
        self.send_not_found()

    def data_delete(self):
        return self.pio(["app", "data-delete", app_name, "--force"])

    def deploy(self):
        if EngineManagerHandler.deploy_process:
            self.log_message("Killing existing process: %d", EngineManagerHandler.deploy_process.pid)
            subprocess.call(['pkill', '-TERM', '-P', str(EngineManagerHandler.deploy_process.pid)])
            EngineManagerHandler.deploy_process = None
        EngineManagerHandler.deploy_process = subprocess.Popen(["pio", "deploy"])
        return "Deploy initiated"

    def train(self):
        return self.pio(["train", "--", "--driver-memory", driver_memory, "--executor-memory", executor_memory])

    def copy_chunked_body(self, dest):
        """
        Copy chunked body to destination file-like object

        chunks ::= chunk* last_chunk
        chunk ::= chunk_size CRLF chunk_body CRLF
        last_chunk ::= 0 CRLF CRLF

        :param dest:
        :return:
        """
        while True:
            chunk_size = self.rfile.readline(65537)
            if len(chunk_size) > 65536:
                raise ValueError("Invalid chunk_size")
            chunk_size = int(chunk_size, 16)
            if chunk_size > 0:
                dest.write(self.rfile.read(chunk_size))
            self.rfile.readline()
            # zero indicates last chunk
            if chunk_size == 0:
                break

    @staticmethod
    def pio(cmd):
        return subprocess.check_output(["pio"] + cmd, cwd=work_dir)

    def handle_import_data(self):
        tmp_file_name = tempfile.mktemp()
        try:
            with open(tmp_file_name, 'wb') as tmp:
                self.consume_request_body(tmp)

            return self.pio(["import", "--appid", app_id, "--input", tmp_file_name])
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

    def start_chunked_response(self, mime_type="text/html", status_code=200):
        self.send_response(status_code)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-Type", "%s; charset=%s" % (mime_type, encoding))
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def write_chunk(self, chunk):
        self.wfile.write("%x\r\n" % len(chunk))
        self.wfile.write(chunk)
        self.wfile.write("\r\n")

    def end_chunked_response(self):
        self.wfile.write("0\r\n\r\n")

    def consume_and_ignore_request_body(self):
        with open(os.devnull, "w") as null:
            self.consume_request_body(null)

    def consume_request_body(self, out):
        content_length = int(self.headers.get('content-length', '-1'))
        if self.headers.get('transfer-encoding') == "chunked":
            self.copy_chunked_body(out)
        elif content_length >= 0:
            out.write(self.rfile.read(content_length))
        else:
            raise EOFError("Can't determine content-length")


class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""


if __name__ == '__main__':
    httpd = ThreadedHTTPServer((ip, port), EngineManagerHandler)

    sys.stderr.write("Trying to deploy engine... It is OK to fail on this stage\n")
    EngineManagerHandler.deploy_process = subprocess.Popen(["pio", "deploy"])

    sys.stderr.write("Prediction.IO Engine Manager listening: {}:{}\n".format(ip, port))
    httpd.serve_forever()
