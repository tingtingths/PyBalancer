package main

import (
	"bufio"
	"fmt"
	"net"
	"runtime"
	"strconv"
)

type Target struct {
	hostname string
	port     int
	weight   int
}

type Job struct {
	r_conn net.Conn
	target Target
}

const (
    DIR_SEND = 1
    DIR_RECV = 2
)

// CONFIG -----
var port = "59999"
var DEBUG = true
var num_worker = runtime.NumCPU() * 2
var pipe_buf_size = 4000
var chan_buf_size = 1
var targets = []Target{Target{"ipinfo.io", 80, 1}}

// ------------

var workQ = make(chan Job, chan_buf_size)

func pipe(source, dest net.Conn, dir int) {
	reader := bufio.NewReader(source)
	writer := bufio.NewWriter(dest)
	buf := make([]byte, pipe_buf_size)
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
                if dir == DIR_SEND {
				    fmt.Printf("(%s) --%d bytes--> (%s)\n", source.RemoteAddr(), n, dest.RemoteAddr())
                }
                if dir == DIR_RECV {
				    fmt.Printf("(%s) <--%d bytes-- (%s)\n", dest.RemoteAddr(), n, source.RemoteAddr())
                }
			}
		}
	}
}

func worker(id int) {
	fmt.Printf("worker %d\n", id)
	for {
		job := <-workQ
		r_conn := job.r_conn
		target := job.target
		if DEBUG {
			fmt.Printf("Target: %s:%d\n", target.hostname, target.port)
		}
		target_conn, err := net.Dial("tcp", target.hostname+":"+strconv.Itoa(target.port))
		if err == nil {
			go pipe(r_conn, target_conn, DIR_SEND)
			go pipe(target_conn, r_conn, DIR_RECV)
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

		workQ <- Job{r_conn, targets[rr_ptr]}
	}
}
