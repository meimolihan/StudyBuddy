BINARY   := studybuddy
DIST     := dist
LDFLAGS  := -s -w
GOPROXY  ?= https://goproxy.cn,direct
export CGO_ENABLED := 0
export GOFLAGS     := -mod=mod
export GOPROXY

.PHONY: all build run test vet fmt clean windows linux darwin arm dist docker docker-run

all: build

## 当前平台编译
build:
	go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY) ./cmd/studybuddy

## 直接运行（源码方式）
run: build
	./$(DIST)/$(BINARY)

vet:
	go vet ./...

fmt:
	go fmt ./...

## Windows amd64
windows:
	GOOS=windows GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-windows-amd64.exe ./cmd/studybuddy

## Linux amd64 / arm64
linux:
	GOOS=linux   GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-linux-amd64 ./cmd/studybuddy
	GOOS=linux   GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-linux-arm64 ./cmd/studybuddy

## macOS amd64 / arm64
darwin:
	GOOS=darwin  GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-darwin-amd64 ./cmd/studybuddy
	GOOS=darwin  GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-darwin-arm64 ./cmd/studybuddy

## Windows / Linux 的双架构静态二进制（交付用）
arm:
	GOOS=windows GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-windows-arm64.exe ./cmd/studybuddy
	GOOS=linux   GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(DIST)/$(BINARY)-linux-arm64 ./cmd/studybuddy

dist: windows linux darwin arm
	@echo "产物位于 $(DIST)/"

## 容器
docker:
	docker build -t mobufan/studybuddy:latest .

docker-buildx:
	docker buildx build --platform linux/amd64,linux/arm64 -t mobufan/studybuddy:latest --load .

docker-run:
	docker compose -f deploy/docker-compose.yml up -d

clean:
	rm -rf $(DIST)
