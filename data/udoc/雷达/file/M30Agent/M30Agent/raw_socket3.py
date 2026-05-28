# !/usr/bin/python
import binascii
import socket
import sys

# Lidar
# 雷达的以太网的IP
LIDAR_ETH_IP = "10.8.8.222" #----------注意ip
# 雷达的以太网连接机器人端端口
LIDAR_ETH_PORT = 8089


# ROBOT 机器人的wlan网段ip
ROBOT_WLAN_IP = "" #ROBOT_WLAN_IP = sys.argv[1]
# 机器人的wlan网段端口，默认为20000（这个端口和刘战杨确认过机器人那边不会用）
ROBOT_WLAN_PORT = 20000
ROBOT_WLAN_CONTROL_PORT = 20001
# PC 同一wifi下的PC的IP
PC_WLAN_IP = "" #PC_WLAN_IP = sys.argv[2]
PC_WLAN_PORT = 20000 # 同一wifi下的PC的端口

# 这部分内容不用管，解析用的。
BIG_ENDIAN = 'big'
LITTLE_ENDIAN = 'little'

# 这部分内容不用管，包头解析用的。
ETH_P_ALL = 0x3
ETH_P_IP = 0x0800
ETH_P_ARP = 0x0806
ETH_P_RARP = 0x8035
ETH_P_IPV6 = 0x086dd
ETH_TYPE_MAP = {
    ETH_P_IP: 'IP',
    ETH_P_ARP: 'ARP',
    ETH_P_RARP: 'RARP',
    ETH_P_IPV6: 'IPv6'
}

# 指令集
cmd_keli_01 = b'\xFA\x5A\xA5\xAA\x00\x02\x01\x01'
cmd_keli_02 = b'\xFA\x5A\xA5\xAA\x00\x02\x02\x02'
cmd_test_47 = b'\x02\x55\x4E\x00\x47\x00\x00\x00\x00\x03'
cmd_test_00 = b'\x02\x55\x4E\x00\x00\x00\x00\x00\x00\x03'
cmd_junion01 = b'\xFA\xA5\x5A\xAF\x01\x01\x00\x0A\x01\x01'
cmd_00H = b'\xFA\xA5\x5A\xAF\x01\x01\x00\x0A\x00\x00'
# MAC地址
class MACAddress:
    def __init__(self, addr):
        self.addr = addr

    def __str__(self):
        return ':'.join(f'{a:02x}' for a in self.addr.to_bytes(6, BIG_ENDIAN))

    def __repr__(self):
        return self.__str__()

# 以太网包头基础类
class EthernetHeader:
    def __init__(self, dst_mac, src_mac):
        self.dst_mac = dst_mac
        self.src_mac = src_mac

    def describe(self):
        return {
            'src_mac': MACAddress(self.src_mac),
            'dst_mac': MACAddress(self.dst_mac)
        }
# 以太网二代协议包头
class EthernetIIHeader(EthernetHeader):
    def __init__(self, dst_mac, src_mac):
        self.dst_mac = dst_mac
        self.src_mac = src_mac
        super(EthernetIIHeader, self).__init__(dst_mac, src_mac)
        self.eth_type = 0

    def describe(self):
        dct = super(EthernetIIHeader, self).describe()
        dct['eth_type'] = self._describe_eth_type(self.eth_type)
        return dct

    @staticmethod
    def _describe_eth_type(eth_type):
        if eth_type in ETH_TYPE_MAP:
            return ETH_TYPE_MAP[eth_type]
        return f'Unknown protocol {eth_type}'

# 以太网802.3版协议包头类
class Ethernet802_3Header(EthernetHeader):
    def __init__(self, dst_mac, src_mac):
        super(Ethernet802_3Header, self).__init__(dst_mac, src_mac)
        self.length = 0
        self.llc = 0
        self.snap = 0

    def describe(self):
        dct = super(Ethernet802_3Header, self).describe()
        dct['length'] = self.length
        dct['llc'] = self.llc
        dct['snap'] = self.snap
        return dct

# 协议解析，成功则返回包内容和包头，失败则返回ValueError
def unpack(packet):
    dst_mac = int.from_bytes(packet[:6],'big') #int(packet[:6].encode("hex"), 16)
    src_mac = int.from_bytes(packet[6:12],'big')#int(packet[6:12].encode("hex"), 16)
    type_or_length = int.from_bytes(packet[12:14],'big')#int(packet[12:14].encode("hex"), 16)
    if type_or_length < 1500:
        hdr = Ethernet802_3Header(dst_mac, src_mac)
        hdr.length = type_or_length
        hdr.llc = int.from_bytes(packet[14:17],'big')#int(packet[14:17].encode("hex"), 16)
        hdr.snap = int.from_bytes(packet[17:22],'big')#int(packet[17:22].encode("hex"), 16)
        return hdr, packet[22:]
    elif type_or_length >= 1536:
        hdr = EthernetIIHeader(dst_mac, src_mac)
        hdr.eth_type = type_or_length
        return hdr, packet[14:]
    else:
        raise ValueError(type_or_length)

# 1，从以太网网卡抓包
# 2，协议解析后，去除包头部，仅转发包内容
# 3，将包内容基于wlan发送至指定IP、端口
def GetDataFromEth0():
    global ROBOT_WLAN_IP, ROBOT_WLAN_PORT, PC_WLAN_IP, PC_WLAN_PORT
    #print(ROBOT_WLAN_IP,PC_WLAN_IP)
    raw_sock = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_IP))
    wlan_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    wlan_s.bind((ROBOT_WLAN_IP, ROBOT_WLAN_PORT))
    wlan_s.settimeout(2)
    while True:
        try:
            packet, packet_info = raw_sock.recvfrom(1500)
            eth_header, payload = unpack(packet)
            # 若一台机器人上连接的雷达设备过多，有两种方法可以做IP识别
            # 第一种，在抓包脚本端解析过滤IP，该方法需要通过解析IP过滤出指定IP设备
            # 目标雷达IP一般在payload头部，具体下标记不清了，到时候实操的时候打印出来就知道了
            # 第二种，带着包头全部发送给目标PC，在PC端进行识别，该方法可以用于多雷达同步检测
            wlan_s.sendto(payload[28:], (PC_WLAN_IP, PC_WLAN_PORT))
            #print datetime.datetime.now(),": Recv Data Length:",len(payload[28:])
            #print binascii.b2a_hex(payload[28:])
            #print(eth_header.describe(), payload[28:])
        except KeyboardInterrupt:
            print('------------------------------------------------')
            break
        #except ValueError as e:
        #    print 'unpack failed', e

# 该模块用于 当需要不拆下雷达从而实现监听别的指令时使用
def RecvCMDFromPC(cmdType):
    global ROBOT_WLAN_IP, ROBOT_WLAN_CONTROL_PORT, PC_WLAN_IP, PC_WLAN_PORT, LIDAR_ETH_IP,LIDAR_ETH_PORT
    print(ROBOT_WLAN_IP, ROBOT_WLAN_CONTROL_PORT, PC_WLAN_IP, PC_WLAN_PORT, LIDAR_ETH_IP,LIDAR_ETH_PORT,cmdType)
    wlan_r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    lidar = (LIDAR_ETH_IP,LIDAR_ETH_PORT)
    wlan_r.bind((ROBOT_WLAN_IP, ROBOT_WLAN_CONTROL_PORT))
    #wlan_r.settimeout(2)
    wlan_r.sendto(cmd_00H,lidar)
    wlan_r.sendto(cmd_test_00, lidar)
    wlan_r.sendto(cmd_keli_02, lidar)
    if cmdType == "47":#---------对应监听需要解析，对接集成软件需要绕过deviceNode，防火墙/socket发随便包给机器人
        wlan_r.sendto(cmd_test_47, lidar)
    elif cmdType =='junion01':
        wlan_r.sendto(cmd_junion01, lidar)
        print('send junion01======================================',binascii.b2a_hex(cmd_junion01))
    else:
        wlan_r.sendto(cmd_keli_01, lidar)
        print('send keli======================================',binascii.b2a_hex(cmd_keli_01))

#print sys.argv
# 脚本入口
if (len(sys.argv) < 3):
    print('Error Format')
if (len(sys.argv) == 4):
    ROBOT_WLAN_IP = sys.argv[1]
    PC_WLAN_IP = sys.argv[2]
    cmdType = sys.argv[3]
    RecvCMDFromPC(cmdType)
    GetDataFromEth0()
else:
    ROBOT_WLAN_IP = sys.argv[1]
    PC_WLAN_IP = sys.argv[2]
    GetDataFromEth0()
