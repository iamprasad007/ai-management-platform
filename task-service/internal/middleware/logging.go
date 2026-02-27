package middleware

import (
	"encoding/json"
	"net/http"
	"net"
	"os"
	"time"
	"fmt"
	"strings"
)

// LogEntry defines the structure for logs sent to Logstash
type LogEntry struct {
    Timestamp string `json:"@timestamp"`
    Level     string `json:"level"`
    Logger    string `json:"logger_name"`
    Message   string `json:"message"`
    Status    int    `json:"status"`
}

// LoggingMiddleware wraps HTTP handlers to log request
func LoggingMiddleware(next http.Handler) http.Handler {
    rawURL := os.Getenv("LOGSTASH_URL")
    // Clean the URL: "http://logstash:5000" -> "logstash:5000"
    logstashURL := strings.TrimPrefix(rawURL, "http://")
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()

        //recorder to tracks the status code
        rw := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

        next.ServeHTTP(rw, r)

        duration := time.Since(start).Milliseconds()
        
        // Format the message
        msg := fmt.Sprintf("HTTP %s %s | Status: %d | Time: %dms", 
            r.Method, r.URL.Path, rw.status, duration)

        entry := LogEntry{
            Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
            Level:     "INFO",
            Logger:    "task-service.internal.middleware.logging",
            Message:   msg,
            Status:    rw.status,
        }

        if logstashURL != "" {
            go func(addr string, payload LogEntry) {
        		conn, err := net.DialTimeout("tcp", addr, 2*time.Second)
        		if err != nil {
            		return // Or log locally
        		}
        		defer conn.Close()

        		data, _ := json.Marshal(payload)
        		data = append(data, '\n') // Required for json_lines codec
        		conn.Write(data)
    		}(logstashURL, entry)
        }
    })
}


type statusRecorder struct {
    http.ResponseWriter
    status int
}

func (r *statusRecorder) WriteHeader(statusCode int) {
    r.status = statusCode
    r.ResponseWriter.WriteHeader(statusCode)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
    return r.ResponseWriter.Write(b)
}
