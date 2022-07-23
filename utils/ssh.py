import re
import socket
import paramiko

from config import settings
from utils.log import get_log

log = get_log("ssh")


def connent(hostname, port, username, password):
    for i in range(10):
        try:
            # 实例化ssh客户端
            ssh = paramiko.SSHClient()
            # 创建默认的白名单
            policy = paramiko.AutoAddPolicy()
            # 设置白名单
            ssh.set_missing_host_key_policy(policy)
            # 链接服务器
            ssh.connect(
                hostname=hostname,  # 服务器的ip
                port=port,  # 服务器的端口
                username=username,  # 服务器的用户名
                password=password  # 用户名对应的密码
            )

            return ssh
        except:
            continue

    log.error(f"服务器:{hostname};连接失败")
    raise Exception("连接服务器失败")


def socket_ssh(hostname, port, username, password):
    """
    使用Transport(流)的方式链接服务器
    :param hostname:
    :param port:
    :param username:
    :param password:
    :return:
    """
    for i in range(10):
        try:
            t = paramiko.Transport(sock=(hostname, port))
            t.connect(username=username, password=password)
            chan = t.open_session()
            chan.settimeout(60)
            chan.get_pty()
            chan.invoke_shell()
            return t, chan
        except:
            continue
    log.error(f"服务器:{hostname};连接失败")
    raise Exception("连接服务器失败")


def bash(ssh, code):
    # 远程执行命令
    stdin, stdout, stderr = ssh.exec_command(code)
    # exec_command 返回的对象都是类文件对象
    # stdin 标准输入 用于向远程服务器提交参数，通常用write方法提交
    # stdout 标准输出 服务器执行命令成功，返回的结果  通常用read方法查看
    # stderr 标准错误 服务器执行命令错误返回的错误值  通常也用read方法
    # 查看结果，注意在Python3 字符串分为了：字符串和字节两种格式，文件返回的是字节

    # 按字节返回结果
    success_result = stdout.read().decode('utf8')
    error_result = stderr.read().decode('utf8')
    return success_result, error_result


def run_cmd(host, port, username, pwd, cmd):
    """
    运行命令
    :param host:
    :param port:
    :param username:
    :param pwd:
    :param cmd:
    :return:
    """
    ssh = connent(host, port, username, pwd)
    try:
        return bash(ssh, cmd)
    except socket.timeout:
        pass
    finally:
        ssh.close()


def get_ip(hostname, port, username, password):
    """
    获取当前拨号获取的IP地址
    :param hostname:
    :param port:
    :param username:
    :param password:
    :return:
    """
    ssh = connent(hostname, port, username, password)
    try:
        success, error = bash(ssh, "ifconfig")
        ip = re.search(settings.dial_network_name + ": .*?inet(.*?)netmask ", success, re.S)
    finally:
        ssh.close()
    if ip:
        return ip.group(1).strip()


def get_log(chan):
    """
    使用Transport链接服务器，执行需要长时间等待的命令时，可以获取屏幕输出的日志
    :param chan:
    :return:
    """
    end_flag_re = re.compile(r"^\[.*?\]#$")
    recover = False
    while not recover:
        result = chan.recv(65535).decode('utf-8')
        if "\r" not in result: continue
        for line in result.split("\r\n"):
            if end_flag_re.match(line.strip()):
                recover = True
                break
            log.debug(line.strip())
            yield line.strip()


def install(hostname, port, username, password, cmd):
    """
    用于执行安装命令
    :param hostname:
    :param port:
    :param username:
    :param password:
    :param cmd:
    :return:
    """
    ssh, chan = socket_ssh(hostname, port, username, password)
    try:
        chan.send(cmd)
        for line in get_log(chan):

            if "Complete!" == line.strip():
                return True
    finally:
        chan.close()
        ssh.close()


def dial(hostname, port, username, password):
    """
    拨号
    :param hostname:
    :param port:
    :param username:
    :param password:
    :return:
    """
    log.info(f"服务器:{hostname}开始拨号")
    ssh = connent(hostname, port, username, password)
    try:
        bash(ssh, settings.dial_cmd)
        ip = get_ip(hostname, port, username, password)
        log.info(f"服务器:{hostname}拨号完成,ip:{ip}")
        return ip
    except socket.timeout:
        log.error(f"服务器:{hostname}拨号失败,链接超时")
    finally:
        ssh.close()


def ping(hostname, port, username, password):
    """
    通过ping命令来查看服务器是否有网络
    :param hostname:
    :param port:
    :param username:
    :param password:
    :return:
    """
    packet_loss_re = re.compile("(\d+)% packet loss")
    ssh, chan = socket_ssh(hostname, port, username, password)
    try:
        chan.send(b"ping -c 3 www.baidu.com\n")
        for line in get_log(chan):
            if packet_loss_re.search(line):
                num = packet_loss_re.search(line).group(1)
                if num == "0":
                    return True
    finally:
        chan.close()
        ssh.close()


def check_network(host, port, username, pwd):
    """
    检查网络是否畅通，如果网络不通自动拨号
    :param host:
    :param port:
    :param username:
    :param pwd:
    :return:
    """
    log.info(f"服务器:{host};检查网络")
    if not ping(host, port, username, pwd):
        log.info(f"服务器:{host};网络不通")
        dial(host, port, username, pwd)
        check_network(host, port, username, pwd)
    else:
        log.info(f"服务器:{host};网络通畅")
        return


def check_install(hostname, port, username, password):
    """
    检查squid软件是否安装
    :param hostname:
    :param port:
    :param username:
    :param password:
    :return:
    """
    success, error = run_cmd(hostname, port, username, password, "ls -l /etc/squid/squid.conf\n")
    if error:
        # 说明没有安装
        return False
    return True


def check_active(hostname, port, username, password):
    """
    检查squid服务是否启动
    :param hostname:
    :param port:
    :param username:
    :param password:
    :return:
    """
    success, error = run_cmd(hostname, port, username, password, "systemctl status squid\n")
    if "Active: active (running)" in success:
        return True
    return False


def init(host, port, username, pwd):
    """
    初始化搭建服务器
    :param host:
    :param port:
    :param username:
    :param pwd:
    :return:
    """
    log.info(f"服务器:{host};开始初始化")
    # 检查网络
    check_network(host, port, username, pwd)
    # 安装软件
    while not check_install(host, port, username, pwd):
        log.info(f"服务器:{host};开始安装squid")
        if install(host, port, username, pwd, "yum -y install squid\n"):
            break
        log.error(f"服务器:{host};安装squid失败，开始重试")
    # # 记录hosts
    # log.info(f"服务器:{host};开始记录hosts")
    # run_cmd(host, port, username, pwd, 'echo "127.0.0.1   $HOSTNAME" >> /etc/hosts\n')
    # 备份 squid.conf 文件
    log.info(f"服务器:{host};开始备份 squid.conf 文件")
    run_cmd(host, port, username, pwd, 'cp /etc/squid/squid.conf /etc/squid/squid.conf.bak\n')
    # 清空squid.conf 文件
    log.info(f"服务器:{host};开始清空 squid.conf 文件")
    run_cmd(host, port, username, pwd, '> /etc/squid/squid.conf\n')
    # 写入squid.conf 文件
    log.info(f"服务器:{host};开始写入 squid.conf 文件")
    f = open("./utils/squid.conf", "rt", encoding="utf8")
    conf = f.read().format(dial_port=settings.dial_port)
    f.close()
    run_cmd(host, port, username, pwd, 'echo "{conf}"  > /etc/squid/squid.conf\n'.format(conf=conf))
    # 设置 squid 的开机默认启动
    log.info(f"服务器:{host};开始设置 squid 的开机默认启动")
    run_cmd(host, port, username, pwd, 'systemctl restart squid\n')
    run_cmd(host, port, username, pwd, 'systemctl enable squid\n')
    log.info(f"服务器:{host};初始化完成")
