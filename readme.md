## 通过拨号服务器搭建代理

### 使用方法

- 在config/settings.py中修改一下内容
```python

# redis 配置
redis_host = "127.0.0.1" # redis地址
redis_port = 6379 # redis端口
redis_pwd = "" # redis密码，如果没有就留空
redis_db = 0 # redis数据库
redis_key = "proxy:pool" # redis中的key

# 拨号命令，adsl服务商会提供
dial_cmd = "pppoe-stop;pppoe-start\n"

# 代理IP的端口，使用代理IP时的端口
dial_port = 3008

# 网卡名称 拨号网卡名称
dial_network_name = "ppp0"


# 服务器列表
servers = [
    {"host": "服务器地址", "port": 端口, "username": "用户名", "pwd": "密码"},
]

```
- 安装依赖
```pip3 install  -r requirements.txt```
- 命令启动
```python3 main.py```
- 定时任务启动
```* * * * * cd 对应的目录;python3 main.py```

###测试
```shell
curl -x ip:端口 http://httpbin.org/ip
```
```python
import requests

proxies = {
    "http": f"http://{ip}:{dial_port}",
    "https": f"http://{ip}:{dial_port}"
}

result = requests.get("http://httpbin.org/ip", proxies=proxies)
```