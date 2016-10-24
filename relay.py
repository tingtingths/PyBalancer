import socket
import threading
import sys
import datetime

id_pool = list(range(0, 10000))
pending_close = []
to_print = True


def notify_end(id, source, dest):
    """Prepare to close the socket,
    or actually close it.
    Each relay has two socket connections each handle by one thread,
        client --> target and
        target --> client.
    The program close both connection if both threads are finished.
    """
    lock = threading.Lock()
    lock.acquire()
    if id in pending_close:
        # the other thread is done, close all
        source.close()
        dest.close()
        pending_close.remove(id)
        id_pool.append(id)
    else:
        # the other thread not done, prepare to close this
        pending_close.append(id)
    lock.release()


def pipe(id, source, dest):
    source.settimeout(2)

    while True:
        try:
            data = source.recv(10485760)
            if not data:
                break
            dest.send(data)
            if to_print:
                time = datetime.datetime.today().strftime(
                    "[%d/%b/%Y %H:%M:%S]")
                print(time + " " + str(source.getpeername()) + " --" +
                      str(len(data)) + " bytes--> " + str(dest.getpeername()))
        except socket.timeout:
            pass
        except Exception as e:
            print(e)
            break

    dest.shutdown(socket.SHUT_WR)
    notify_end(id, source, dest)


def setup_pipes(r_conn, target):
    global id_pool

    print("target: " + str(target))
    _target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _target.connect(target)
    id = id_pool.pop(0)

    threading.Thread(target=pipe, args=(id, r_conn, _target)).start()
    threading.Thread(target=pipe, args=(id, _target, r_conn)).start()


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
        rr_ptr = -1  # idx of pervious backend server used in round-robin style
        print("Relay " + str(self.port))

        while True:
            try:
                r_conn, r_addr = listen_sock.accept()
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

                threading.Thread(target=setup_pipes, args=(
                    r_conn, self.target_hosts[rr_ptr][0])).start()
                threading.Thread(target=setup_pipes, args=(r_conn, self.backend_hosts[rr_ptr][0] )).start()
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(e)


if __name__ == "__main__":
    to_print = True
    # ((addr, port), priority)
    targets = [(("ipinfo.io", 80), 1)]
    Relay(54321, targets).start()
