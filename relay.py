import socket
import threading
import sys
import datetime

id_pool = list(range(0, 10000))
pending_poll = []

def notify_end(id, source, dest):
    lock = threading.Lock()
    lock.acquire()
    if id in pending_poll:
        source.close()
        dest.close()
        pending_poll.remove(id)
        id_pool.append(id)
    else:
        pending_poll.append(id)
    lock.release()

def pipe(id, source, dest):
    source.settimeout(2)
    while True:
        try:
            data = source.recv(10485760)
            if not data: break
            dest.send(data)
            time = datetime.datetime.today().strftime("[%d/%b/%Y %H:%M:%S]")
            print(time + " " + str(source.getpeername()) + " --" + str(len(data)) + " bytes--> " + str(dest.getpeername()))
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
    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    backend.connect(target)
    id = id_pool.pop(0)

    threading.Thread(target=pipe, args=(id, r_conn, backend)).start()
    threading.Thread(target=pipe, args=(id, backend, r_conn)).start()

class Relay(threading.Thread):
    def __init__(self, port, backend_hosts):
        super().__init__()
        self.port = port
        self.backend_hosts = backend_hosts

    def run(self):
        print("Relay " +str(self.port))
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.bind(("localhost", self.port))
        listen_sock.listen(512)
        listen_sock.settimeout(4)
        rr_ptr = -1 # idx of pervious backend server used in round-robin style

        while True:
            try:
                r_conn, r_addr = listen_sock.accept()
                print("Connect from " + r_addr[0])

                get_host = True
                while get_host:
                    # round-robin
                    if len(self.backend_hosts) - 1 <= rr_ptr:
                        rr_ptr = 0
                    else:
                        rr_ptr += 1
                    if self.backend_hosts[rr_ptr][-1] >= 0:
                        get_host = False

                threading.Thread(target=setup_pipes, args=(r_conn, self.backend_hosts[rr_ptr][0] )).start()
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(e)


if __name__ == "__main__":
    # ((addr, port), priority)
    backend = [(("localhost", 4343), -1), (("ting-xps", 4343), 0), (("ting-xps", 4545), 0)]
    Relay(54321, backend).start()
