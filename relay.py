import socket
import threading
import sys
import datetime


def pipe(source, dest):
    source.settimeout(2)
    while True:
        try:
            data = source.recv(4194304)
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

def relay(port, backend_hosts):
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.bind(("", port))
    listen_sock.listen(64)
    listen_sock.settimeout(4)
    rr_ptr = 0 # idx of pervious backend server used in round-robin style

    while True:
        try:
            # round-robin
            if len(backend_hosts) - 1 <= rr_ptr:
                rr_ptr = 0
            else:
                rr_ptr += 1

            r_conn, r_addr = listen_sock.accept()
            backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend.connect(backend_hosts[rr_ptr])
            print("Connected from " + r_addr[0])

            threading.Thread(target=pipe, args=(r_conn, backend)).start()
            threading.Thread(target=pipe, args=(backend, r_conn)).start()

            #handle(r_conn, r_addr, backend_sock)
        except socket.timeout:
            pass
        except Exception as e:
            print(e)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    backend = [("localhost", 4343)]
    relay(80, backend)
