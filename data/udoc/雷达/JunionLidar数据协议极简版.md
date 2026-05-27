---
title: JunionLidar数据协议极简版
description: 
published: true
date: 2025-07-02T10:54:49.470Z
tags: 公开
editor: markdown
dateCreated: 2025-06-09T08:43:40.246Z
---

# Lidar数据协议说明

| 文件名称 | Lidar数据协议说明 |
| -------- | ------------------ |
| 部门     | 软件算法部          |
| 版本     | V1.1               |
| 密级     | 公开               |


## 修改记录

| 版本号 | 修改日期      | 修改人 | 概述 | 详细说明           |
| ------ | ---------- | ----- | ---- | ------------------- |
| V1.0   | 2025-06-10 | 王春晓 | 初稿 |描述雷达Junion01数据帧协议|
| V1.1   | 2025-07-02 | 王春晓 | 编辑wiki | 根据模板编辑wiki|

## 1、停止测距指令

```
0xFA,0xA5,0x5A,0xAF,0x01,0x01,0x00,0x0A,0x00,0x00 //上位机向雷达发送停止测距指令
0xFA,0xA5,0x5A,0xAF,0x01,0x00,0x00,0x0A,0x00,0x00 //雷达回复
```

## 2、扫描测距指令
```
0xFA,0xA5,0x5A,0xAF,0x01,0x01,0x00,0x0A,0x01,0x01 //扫描指令
```

雷达接收指令后，根据雷达已配置参数，如帧率、角度分辨率回波方式等，组织状态包与数据包，数据结构详见下一节。

## 3、数据帧格式说明

> 雷达接收到数据帧指令后，根据雷达已配置参数，如帧率、角度分辨率、角度范围、回波方式等，组织状态包与数据包，其中第一包为状态包，假设总包数为N，每包scandata数为M。

### I. 状态包

指令结构：

| name                     | type   | length | offset | value               | description                               |
| ------------------------ | ------ | ------ | ------ | ------------------- | ----------------------------------------- |
| preamble_code[4]         | uint8  | 4      | 0      | 0xFA,0xA5,0x5A,0xAF |                                           |
| cmd_version              | uint8  | 1      | 4      | 0x01                |                                           |
| flag                     | uint8  | 1      | 5      | 0x01                | lidar to pc                               |
| length                   | uint16 | 2      | 6      | 0x00,0x80           | 状态包长度固定为128字节                   |
| crc                      | uint8  | 1      | 8      |                     | 从crc下一个字节（cmd）开始的累加和        |
| cmd                      | uint8  | 1      | 9      | 0x01                |                                           |
| pkg_index                | uint8  | 1      | 10     | 0x00                | 0表示状态包                               |
| pkg_total_num            | uint8  | 1      | 11     | N                   | 每帧包总数                                |
| frame_id                 | uint32 | 4      | 12     |                     | 帧的编号                                  |
| frame_ver_info           | uint16 | 2      | 16     |                     | 帧格式版本信息                            |
| device_info              | uint8  | 1      | 18     |                     | 设备信息                                  |
| dist_unit                | uint8  | 1      | 19     |                     | 默认为0 表示距离单位mm                    |
| scan_area                | uint8  | 1      | 20     |                     | 0 表示270°水平扫描<br />1表示360°水平扫描 |
| scandata_mode            | uint8  | 1      | 21     |                     | 数据模式：默认为0                         |
| status_code[4]           | uint8  | 4      | 22     |                     | 当前状态信息                              |
| timestamp                | uint32 | 4      | 26     |                     | 时间戳，从上电启动开始，ms单位            |
| frame_frequency          | uint32 | 4      | 30     |                     | 帧率，电机每秒转动次数，（1/1000Hz）      |
| samples_per_sec          | uint32 | 4      | 34     |                     | 采样频率，激光每秒采样次数                |
| samples_per_frame        | uint16 | 2      | 38     |                     | 采样频率，激光每圈采样次数                |
| result_per_frame         | uint16 | 2      | 40     |                     | 每帧数据结果（scandata）个数              |
| first_angle              | int32  | 4      | 42     |                     | 数据结果（scandata）起始角度（1/10000°）  |
| angular_increment        | int32  | 4      | 46     |                     | 角度步长，角分辨率（1/10000°）            |
| <u>filter_info</u>[4]    | uint8  | 4      | 50     |                     | 滤波选项                                  |
| <u>io_info</u>[4]        | uint8  | 4      | 54     |                     | io信息                                    |
| <u>echo_info</u>[4]      | uint8  | 4      | 58     |                     | 回波信息                                  |
| <u>reflector_info</u>[4] | uint8  | 4      | 62     |                     | 反光板信息                                |
| data_info[4]             | uint8  | 4      | 66     |                     | 测量点数据格式信息                        |
| reseverd[58]             | uint8  | 58     | 70     |                     | 保留                                      |

【说明】：
        下划线标注参数属于雷达内部参数，不做说明，用户可通过雷达配套软件参数配置界面进行查看和修改。
【data_info[4]说明】
- data_info[0]：测量点字节数
- data_info[1]：测量点距离bit位数
- data_info[2]：测量点反射强度bit位数
- data_info[3]：测量点距离-强度排列顺序：bit0：0，距离在前，强度在后；1，强度在前，距离在后

### II. 数据包

> 第2包至最后一包为数据包，假设总包数为N，每包scandata数为M。

| name               | type   | length | offset | value               | description                        |
| ------------------ | ------ | ------ | ------ | ------------------- | ---------------------------------- |
| preamble_code[4]   | uint8  | 4      | 0      | 0xFA,0xA5,0x5A,0xAF |                                    |
| cmd_version        | uint8  | 1      | 4      | 0x01                |                                    |
| flag               | uint8  | 1      | 5      | 0x01                | lidar to pc                        |
| length             | uint16 | 2      | 6      |                     | 数据包长度为16+4*M                 |
| crc                | uint8  | 1      | 8      |                     | 从crc下一个字节（cmd）开始的累加和 |
| cmd                | uint8  | 1      | 9      | 0x01                |                                    |
| pkg_index          | uint8  | 1      | 10     | X                   | X为1至（N-1)                       |
| pkg_total_num      | uint8  | 1      | 11     | N                   | 每帧包总数                         |
| frame_id           | uint32 | 4      | 12     |                     | 帧的编号                           |
| scan_data(320\*X)  |        |        |        |                     |                                    |
| scan_data(320\*X+1)|        |        |        |                     |                                    |
| ……                 |        |        |        |                     |                                    |
| scan_data(320\*X+M-1) |     |        |        |                     |                                    |

- 若X=1至N-2,M=320(即每包最大包括320个点云数据)
- 若X=N-1,M<=320

其中

1. M30Dmini/M30B 每个测量点（scan_data）占4字节：2字节距离值+2字节强度值；

    | name      | type   | length | description      |
    | --------- | ------ | ------ | ---------------- |
    | distance  | uint16 | 2      | 测量点距离值     |
    | amplitude | uint16 | 2      | 测量点反射强度值 |


2. M04B_V6 每个测量点（scan_data）占2字节(16bit)：2bit强度值+14bit距离值；

    | name      | type | length | description      |
    | --------- | ---- | ------ | ---------------- |
    | amplitude | Bit  | 2      | 测量点反射强度值 |
    | distance  | Bit  | 14     | 测量点距离值     |

   

示例：

- 以M30B为例，扫描一圈360°，若雷达角分辨率为0.5°，则产生721个测量点，那么一帧数据包括以下4个udp包：
  - 状态包(pkg_index = 0)：128字节
  - 数据包(pkg_index = 1)：1296字节=16字节+320测量点*4字节
  - 数据包(pkg_index = 2)：1296字节=16字节+320测量点*4字节
  - 数据包(pkg_index = 3)：340字节  =16字节+81测量点*4字节

- 以M04B_V6为例，扫描一圈270°，若雷达角分辨率为0.5°，则产生541个测量点，那么一帧数据包括以下3部分：
  - 状态包(pkg_index = 0)：128字节
  - 数据包(pkg_index = 1)：656字节=16字节+320测量点*2字节
  - 数据包(pkg_index = 2)：458字节=16字节+221测量点*2字节

