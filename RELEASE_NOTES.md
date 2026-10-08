游戏题模块彻底清空

```bash
docker pull mobufan/studybuddy:latest
```
```bash
docker pull mobufan/studybuddy:v0.1.3
```

```bash
docker pull ghcr.io/meimolihan/studybuddy:latest
```
```bash
docker pull ghcr.io/meimolihan/studybuddy:v0.1.3
```

## 二进制安装
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/install.sh)" -p 8080 -d /var/lib/StudyBuddy
```

## 二进制卸载
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/uninstall.sh)" -y --purge
```
