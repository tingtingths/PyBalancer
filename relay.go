package main

import (
	"bufio"
	"fmt"
	"net"
	"strconv"
)

type Target struct {
	hostname string
	port     int
}

var port = "54322"
var DEBUG = true
var targets = []Target{Target{"127.0.0.1", 80}}

func pipe(source, dest net.Conn) {
	reader := bufio.NewReader(source)
	writer := bufio.NewWriter(dest)
	buf := make([]byte, 40960)
	for {
		n, err := reader.Read(buf)
		if err != nil {
			source.Close()
			dest.Close()
			break
		} else {
			_, err := writer.Write(buf[:n])
			if err != nil {
				source.Close()
				dest.Close()
				break
			}
			writer.Flush()
			if DEBUG {
				fmt.Printf("(%s) --%d bytes--> (%s)\n", source.RemoteAddr(), n, dest.RemoteAddr())
			}
		}
	}
}

func setup_pipes(r_conn net.Conn, target Target) {
	if DEBUG {
		fmt.Printf("Target: %s:%d\n", target.hostname, target.port)
	}
	target_conn, err := net.Dial("tcp", target.hostname+":"+strconv.Itoa(target.port))
	if err == nil {
		go pipe(r_conn, target_conn)
		go pipe(target_conn, r_conn)
	}
}

func main() {
	fmt.Println(targets)
	listener, err := net.Listen("tcp", ":"+port)
	if err != nil {
		fmt.Println(err)
	}
	rr_ptr := -1

	fmt.Println("Relay " + port)
	for {
		r_conn, err := listener.Accept()
		if err != nil && DEBUG {
			fmt.Println(err)
		}
		if DEBUG {
			fmt.Printf("Connected from %s\n", r_conn.RemoteAddr())
		}

		if len(targets)-1 <= rr_ptr {
			rr_ptr = 0
		} else {
			rr_ptr++
		}

		go setup_pipes(r_conn, targets[rr_ptr])
	}
}