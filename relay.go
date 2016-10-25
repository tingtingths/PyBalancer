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
	weight   int
}

type PipeArgs struct {
	r_conn net.Conn
	target Target
}

var port = "54322"
var DEBUG = true
var targets = []Target{Target{"ipinfo.io", 80, 1}}
var channel = make(chan PipeArgs)

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

func worker(id int) {
	fmt.Printf("worker %d\n", id)
	for {
		args := <-channel
		r_conn := args.r_conn
		target := args.target
		if DEBUG {
			fmt.Printf("Target: %s:%d\n", target.hostname, target.port)
		}
		target_conn, err := net.Dial("tcp", target.hostname+":"+strconv.Itoa(target.port))
		if err == nil {
			go pipe(r_conn, target_conn)
			go pipe(target_conn, r_conn)
		}
	}
}

func main() {
	fmt.Println(targets)
	listener, err := net.Listen("tcp", ":"+port)
	if err != nil {
		fmt.Println(err)
	}
	rr_ptr := 0
	weight_count := 0
	num_worker := 10
	for i := 0; i < num_worker; i++ {
		go (worker)(i)
	}

	fmt.Println("Relay " + port)
	for {
		r_conn, err := listener.Accept()
		if err != nil && DEBUG {
			fmt.Println(err)
		}
		if DEBUG {
			fmt.Printf("Connected from %s\n", r_conn.RemoteAddr())
		}

		get_host := true
		for get_host {
			if len(targets) <= rr_ptr { // check if ptr out of bound
				rr_ptr = 0
				weight_count = 0
			}
			if weight_count > targets[rr_ptr].weight-1 || targets[rr_ptr].weight <= 0 { // move to next target if exceed weight or weight too low
				rr_ptr++
				weight_count = 0
			} else {
				weight_count++
				get_host = false
			}
		}

		select {
		case channel <- PipeArgs{r_conn, targets[rr_ptr]}:
		}
	}
}
