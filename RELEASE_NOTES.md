feat: 新增教材页面与模板

```bash
docker pull mobufan/studybuddy:latest
```
```bash
docker pull mobufan/studybuddy:v0.0.4
```

```bash
docker pull ghcr.io/meimolihan/studybuddy:latest
```
```bash
docker pull ghcr.io/meimolihan/studybuddy:v0.0.4
```

## 二进制安装
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/install.sh)" -p 8080 -d /var/lib/StudyBuddy
```

## 二进制卸载
```bash
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/uninstall.sh)" -y --purge
```
