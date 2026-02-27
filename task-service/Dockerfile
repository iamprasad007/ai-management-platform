# -------- Build stage --------
FROM golang:1.22-alpine AS build

WORKDIR /app

# Install git (required for some Go modules)
RUN apk add --no-cache git

# Copy go mod files first (better layer caching)
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy remaining source code
COPY . .

# Build statically linked binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o task-service ./cmd

# -------- Runtime stage --------
FROM alpine:latest

WORKDIR /app

# Add CA certificates (needed if calling other services over HTTP/HTTPS)
RUN apk add --no-cache ca-certificates

COPY --from=build /app/task-service .

EXPOSE 8081

CMD ["./task-service"]
