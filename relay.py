import socket
import threading
import sys
import datetime

DEBUG = True


def pipe(source, dest):
    source.settimeout(2)

    while True:
        try:
            data = source.recv(10485760)
            if not data:
                break
            dest.send(data)
            if DEBUG:
                time = datetime.datetime.today().strftime(
                    "[%d/%b/%Y %H:%M:%S]")
                print(time + " " + str(source.getpeername()) + " --" +
                      str(len(data)) + " bytes--> " + str(dest.getpeername()))
        except:
            break
        finally:
            source.close()
            dest.close()


def setup_pipes(r_conn, target):
    if DEBUG:
        print("target: " + str(target))
    _target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _target.connect(target)

    threading.Thread(target=pipe, args=(r_conn, _target)).start()
    threading.Thread(target=pipe, args=(_target, r_conn)).start()


class Relay(threading.Thread):

    def __init__(self, port, target_hosts):
        super().__init__()
        self.port = port
        self.target_hosts = target_hosts

    def run(self):
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.bind(("0.0.0.0", self.port))
        listen_sock.listen(512)
        listen_sock.settimeout(4)
        rr_ptr = -1  # idx of pervious target server used in round-robin style
        print("Relay " + str(self.port))

        while True:
            try:
                r_conn, r_addr = listen_sock.accept()
                if DEBUG:
                    print("Connect from " + r_addr[0])

                get_host = True
                while get_host:
                    # round-robin
                    if len(self.target_hosts) - 1 <= rr_ptr:
                        rr_ptr = 0
                    else:
                        rr_ptr += 1
                    if self.target_hosts[rr_ptr][-1] >= 0:
                        get_host = False

                threading.Thread(
                    target=setup_pipes, args=(
                        r_conn, self.target_hosts[rr_ptr][0])).start()
            except:
                pass


if __name__ == "__main__":
    # ((addr, port), priority)
    targets = [(("ipinfo.io", 80), 1)]
    Relay(54321, targets).start()
