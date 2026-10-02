第一个测试版

```bash
docker pull mobufan/studybuddy:latest
```
```bash
docker pull mobufan/studybuddy:v0.0.1
```

```bash
docker pull ghcr.io/meimolihan/studybuddy:latest
```
```bash
docker pull ghcr.io/meimolihan/studybuddy:v0.0.1
```

## 二进制安装
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/studybuddy/main/scripts/install.sh)" -p 8082 -d /var/lib/StudyBuddy
```

## 二进制卸载
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/studybuddy/main/scripts/uninstall.sh)" -y --purge
```
