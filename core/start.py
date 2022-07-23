import os
import time
import requests

from utils import ssh, log, red
from config.settings import servers, dial_port

logger = log.getLogger("start")


def check_init(host, port, username, pwd):
    """
    检查服务器是否需要初始化
    :return:
    """
    install = ssh.check_install(host, port, username, pwd)
    if not install:
        # 没有安装squid，需要初始化
        ssh.init(host, port, username, pwd)
    active = ssh.check_active(host, port, username, pwd)
    if not active:
        # 没有启动squid，需要启动squid
        logger.info(f"服务器:{host};开始设置 squid 的开机默认启动")
        ssh.run_cmd(host, port, username, pwd, 'systemctl restart squid\n')
        ssh.run_cmd(host, port, username, pwd, 'systemctl enable squid\n')


def check_proxies(host, ip):
    # ip = ssh.get_ip(host, port, username, pwd)

    proxies = {
        "http": f"http://{ip}:{dial_port}",
        "https": f"http://{ip}:{dial_port}"
    }
    for i in range(5):
        logger.info(f"服务器:{host};检测代理IP:{ip}:{dial_port}是否可用。次数:{i}")
        try:
            res = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=5)
            print(res.text)
            logger.info(f"服务器:{host};代理IP:{ip}:{dial_port}可用。次数:{i}")
            return True
        except:
            logger.error(f"服务器:{host};代理IP:{ip}:{dial_port}无效。次数:{i}")
            continue

    return False


def redis_clear(host, port, username, pwd):
    ip = ssh.get_ip(host, port, username, pwd)
    red.clearCurrentIp(host, ip + f":{dial_port}")


def run():
    if os.path.isfile("p"):
        return
    try:
        pid = os.getpid()
        with open("p", "wt", encoding="utf8") as f:
            f.write(str(pid))
        for server in servers:
            host = server.get("host")
            port = server.get("port")
            username = server.get("username")
            pwd = server.get("pwd")
            try:
                # 检测服务器是否需要初始化
                check_init(host, port, username, pwd)
                # 将当前服务器的代理在redis中删除
                redis_clear(host, port, username, pwd)
                # 拨号
                while True:
                    ip = ssh.dial(host, port, username, pwd)
                    # 检测IP是否可用
                    if check_proxies(host, ip):
                        break
                red.addCurrentIp(host, ip + f":{dial_port}")
            except Exception:
                continue
            finally:
                time.sleep(10)
    finally:
        os.remove("p")
