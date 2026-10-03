feat: 归档页面权限控制，补充UI相关测试

```bash
docker pull mobufan/studybuddy:latest
```
```bash
docker pull mobufan/studybuddy:v0.0.6
```

```bash
docker pull ghcr.io/meimolihan/studybuddy:latest
```
```bash
docker pull ghcr.io/meimolihan/studybuddy:v0.0.6
```

## 二进制安装
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/install.sh)" -p 8080 -d /var/lib/StudyBuddy
```

## 二进制卸载
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/uninstall.sh)" -y --purge
```
