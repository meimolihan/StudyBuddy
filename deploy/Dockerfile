# ---------- 构建阶段 ----------
FROM golang:1.23-alpine AS builder

WORKDIR /src
ENV GOPROXY=https://goproxy.cn,direct
ENV CGO_ENABLED=0
ENV GOFLAGS=-mod=mod

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -ldflags "-s -w" -o /out/studybuddy ./cmd/studybuddy

# ---------- 运行阶段 ----------
FROM alpine:3.19

RUN apk add --no-cache ca-certificates tzdata && \
    addgroup -S app && adduser -S -G app app

WORKDIR /app
COPY --from=builder /out/studybuddy /app/studybuddy
COPY --from=builder /src/content /app/content
COPY --from=builder /src/wallpapers /app/wallpapers

# 数据与教材均声明为卷，便于持久化与替换教材
VOLUME ["/app/data", "/app/archive", "/app/content"]

ENV TZ=Asia/Shanghai
ENV STUDYBUDDY_PORT=8080
ENV STUDYBUDDY_CONTENT=/app/content
ENV STUDYBUDDY_DATA=/app/data
ENV STUDYBUDDY_ARCHIVE=/app/archive

EXPOSE 8080

USER app
ENTRYPOINT ["/app/studybuddy"]
