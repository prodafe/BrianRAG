---
title: Modbus功能介绍
description: 
published: true
date: 2026-04-01T07:20:18.989Z
tags: 公开, modbus, 功能介绍
editor: markdown
dateCreated: 2026-03-20T01:30:50.132Z
---

# Modbus功能介绍
  
| 文件名称 | Modbus功能介绍  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 公开 |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2026-03-31 | 张宜行  | Modbus功能介绍 |  |
# 一.Modbus简介

Modbus 是工业自动化领域最经典且普及的开放通信协议，核心是主从请求 - 响应模型，用于设备间互联与数据读写。  主从架构就是主站（Master）发起请求，从站（Slave） 回数据响应，可以理解为从站是服务器，主站是客户端。

Modbus包含四种寄存器，各寄存器都有独立的地址；四种寄存器分别为线圈（Coils；功能码1/5/15），离散输入（Discrete Inputs；功能码2）， 输入寄存器（Input Registers；功能码4）， 保持寄存器（Holding Registers；功能码3/6/16）；其中从站(服务器)可以读写四种寄存器，主站(客户端)可以读四种寄存器，但只能向线圈和保持寄存器写入值；

当前支持的是Modbus TCP（把 Modbus 协议跑在以太网 TCP/IP 上），支持的车型是全向舵轮车；

<font style="color:#DF2A3F;">如果在新项目中，客户不支持以以下方式部署Modbus，需要再与研发同事商议。</font>



# 二.Modbus在现场的部署及应用

以下结合宇晶现场为例进行说明。在本项目中，玖物机器人底盘作为从站（服务器），创建并维护寄存器，宇晶机械臂上装作为主站（客户端），获取机器人实时状态或通过修改寄存器的值给底盘下发任务，以下做详细说明：

1.获取机器人的状态

离散输入寄存器各地址位含义：

<!-- 这是一张图片，ocr 内容为：备注 数据类型 地址位 功能 根据RMS.JSON文件 中"MODBUS_STATUS_PARAMS"的"HEART_INTERVAL" 机器人心跳 BOOL (心跳间隔)在0和1交替 是否在充电 BOOL 3 2机器人移动中遇到障碍物会急停 是否急停 BOOL 4 3 是否抱闸 BOOL 5 手动:底盘会先减速,控制舵轮先旋转到指定角度,再移动; 6 手动状态 BOOL 5 自动:需要上位机计算控制减速旋转速度; 7 自动状态 BOOL MODBUS抢占控制状态 是否处于上装抢占控制状态 8 BOOL 机器人处于"STOP" 机器人停止 6 BOOL 机器人初始化完成 机器人准备好 10 BOOL 机器人运行中 机器人不处于"STOP"或"IDLE" 11 BOOL 12 13 14 101 检测到上装心跳异常时为1(COIL地址0异常) 上装心跳异常 15 BOOL 102检查到调度心跳异常时为1(COIL地址200异常) 调度心跳异常 BOOL 16 103检查到PATH心跳异常时为1(COIL地址400异常) PATH心跳异常 17 BOOL 18 19 20 21 请求上装工作 200 BOOL -->
![](https://cdn.nlark.com/yuque/0/2026/png/35951869/1773640508425-20b7bf65-6204-4666-a6de-b020937ce95f.png)

输入寄存器各地址位含义：

<!-- 这是一张图片，ocr 内容为：备注 是否实现该地址 数据类型 单位 地址位 功能 机器人坐标 0M FLOAT32 2 FLOAT32 机器人Y坐标 2M 3 范围-PI~PI 机器人角度坐标 FLOAT32 4  RAD 机器人VX速度 FLOAT32 M/S FLOAT32 8 M/S 机器人VY速度 6 机器人角速度 FLOAT32 10 RAD/S 0定位失败,1定位正确,2正在重定位 UINT16 机器人定位状态 7244 8 机器人定位置信度 UINT16 0-1000 6 HINAAZ4033480080002244 电池电量 0-100 UINT16 10 FLOAT32 摄氏度 11 电池温度 NO FLOAT32 电池电压 12 电池电流 FLOAT32 13 NO 电池充放电次数 FLOAT32 14 NO 电池寿命 FLOAT32 15 NO 控制器温度 16 FLOAT32 NO 控制器湿度 FLOAT32 17 NO 控制器电压 FLOAT32 18 NO FLOAT32 NO 控制器温度 19 控制器湿度 FLOAT32 NO 20 控制器电压 FLOAT32 NO 21 FLOAT32 总里程 22 FLOAT32 23 累计运行时间 NO FATAL 错误码 UINT16 24 NO 25 ERROR 错误码 UINT16 NO ERROR 错误码集合 26 UINT16 NO WARNING 错误码 27 UINT16 NO 0为无任务,或者任务ID非数字; 机器人当前任务号 80 28 UINT32 对应MODBUS_TASK.JSON中相应目标站点的"JOB ID" 0或者与当前任务号不匹配为未完成; 82 机器人完成的任务点号 可以在ROUTES任务的最后一个小任务中,通过MODE将该地址位改为 UINT32 29 当前任务点号,表示任务完成 30 31 0为下降,1为顶升,2为顶生下降中 机器人顶升状态 100 UINT16 -->
![](https://cdn.nlark.com/yuque/0/2026/png/35951869/1773640547064-c20c8cc9-74fe-496a-9ae1-b9089b8e9b0a.png)

玖物机器人底盘（从站/服务器）会将各状态值写到"离散输入寄存器"和"输入寄存器"固定的地址位，其中离散输入寄存器保存的是boll类型的值，输入寄存器可以保存"int32"/"uint32"/"float32"/"int16"/"uint16"类型的值；

主站（客户端）可以通过读取这些地址位的数据，获得底盘的实时数据；





2.主站（客户端）通过修改寄存器的值给底盘下发任务

线圈各地址位含义：

<!-- 这是一张图片，ocr 内容为：地址位 数据类型 备注 功能 上装心跳 0 根据RMSJSON文件"MODBUS TASK PARAMS"中的'MACHINE HEART INTERVAL"(心跳间隔]在0和1交替 2 BOOL 812345 上装准备好 BOOL 上装抢占机器人移动控制权:0为机器人自动,1为上装手动控制机器人移动 上装抢占控制权 4 BOOL 上装故障 5 BOOL 上装非急停/上装安全 TRUE表示上装处于安全状态 6 BOOL 上装上下料中 7 BOOL 8 6 10 200 根据RMSJSON文件"MODBUS TASK PARAMS"中的"RMS HEART INTERVAL(调度心跳间隔)在0和1交替 调度心跳 BOOL 11 调度准备好 201 BOOL 12 13 14 H作们侣 1000  1000及以下地址位用户自定义 上料台准备好 BOOL 上料台允许取料 1001 BOOL 上料台故障中 1002 BOOL -->
![](https://cdn.nlark.com/yuque/0/2026/png/35951869/1773640833466-bfec0807-16e1-409e-8792-baac125324f5.png)

保持寄存器各地址位含义：

<!-- 这是一张图片，ocr 内容为：数据类型 功能 地址位 单位 备注 0 M/S 上装抢占控制权后生效;速度范围为[-0.5,0.5] 手动X方向速度 FLOAT32 2 上装抢占控制权后生效;速度范围为[-0.5,0.5] 手动Y方向速度 FLOAT32 3 M/S 上装抢占控制权后生效;速度范围为[-0.1745,0.1745] 手动旋转速度 FLOAT32 RAD/S 4 68 上装抢占控制权后生效 FLOAT32 自动任务速度 5 M/S 开环下发机器人舵角(机器人坐标系) 上装抢占控制权后生效 FLOAT32 6 RAD 7 需要播放的语音的名字 播放音频 30 UINT16 10 11 12 13 机器人要执行的任务号,详细说明见"二.ROUTES任务配置" 机器人目标站点 14 200 UINT32 15 16 748 上装1位物料状态 1000及以下地址位用户自定义 1000 上装2#位物料状态 1001 19 上装3#位物料状态 1002 20 -->
![](https://cdn.nlark.com/yuque/0/2026/png/35951869/1773640856914-49e7a4e6-6b49-4868-ac50-3c2afb402d8e.png)

注：1000及之后的地址位由客户自定义；



①抢占底盘控制权，控制机器人底盘移动

主站（客户端）通过把线圈的2地址位置为true，设置上装抢占控制权模式，然后再通过修改保持寄存器的0/2/4地址位控制底盘移动或旋转；



②主站给底盘下发任务

主站（客户端）通过修改保持寄存器中地址200的值，修改机器人目标站点(该参数取值范围是1/2/3……之类的正数)，玖物机器人在读取到该值非零后，就会执行相应的routes任务，示例如下：

玖物机器人底盘（从站/服务器）读取到机器人目标站点的值为"1"，就会查找"1"对应的routes任务；如下表所示，"1"对应routes任务是"test1"中的"a"任务，

```json
{
  // "机器人目标站点"(正数)对应的任务；如"机器人目标站点"的值为1，则机器人会执行"1"任务
	"1": {
		"routes_name": "test1", 	// 需要触发routes文件中的任务名称
		"key": "a", 								// 从"routes_1"任务中的哪个小任务开始执行(默认为"a")
		"job_id": 1 								// 任务的id号(需要是大于0的整数)(默认为"机器人目标站点"的值)(每个任务的id号不能相同！)
	}
}
```

接着机器人底盘就会从"test1"的"a"任务开始执行（任务执行的顺序是a->a1->……->a1111），同时将保持寄存器中地址200的值置为0；

在"test1"大任务的最后，通过"modbus_set"小任务，将输入寄存器的的地址位82置为当前任务的机器人目标站点"1"，表示已完成任务；主站（客户端）可以通过读取该地址位的值，判断是否已完成当前任务；

```json
"test1":{
		"a": {
			"cmd": "rms_goto",
			"goal": "Target1",
			"target": "goal",
			"safe": false
		},
    ……
		"a1111": {
			"cmd": "modbus_set",									// 设置寄存器的值
      "register_type": "input_registers",		// 寄存器类型：输入寄存器
      "device_name": "rms_modbus_slave",		// 设置/获取值的是哪个设备，如"调度从机"
      "addr": ***,													// 设置/获取值的地址
      "val_type": "uint32",									// "val"值的类型
      "val": ***														// 为要设置的值
		}
}
```

示例：以下为宇晶现场实例

宇晶机械臂上装（主站/客户端）在将保持寄存器中地址200的值设置为"1"后，玖物底盘（从站/服务器）读取到该值并查找到1对应的routes任务为"yj_test"的"a"；

```json
{
  // "机器人目标站点"(正数)对应的任务；如"机器人目标站点"的值为1，则机器人会执行"1"任务
	"11": {
		"routes_name": "yj_test", 	// 需要触发routes文件中的任务名称
		"key": "a", 								// 从"routes_1"任务中的哪个小任务开始执行(默认为"a")
		"job_id": 11 								// 任务的id号(需要是大于0的整数)(默认为"机器人目标站点"的值)(每个任务的id号不能相同！)
	}
}
```

机器人在routes.json中查找到"yj_test"的"a"任务，并开始执行，执行流程如下

```json
"yj_test":{
		"a":{
			"cmd": "modbus_set",
			"register_type": "input_registers",
			"addr": 82,
			"val_type": "uint32",
			"device_name": "rms_modbus_slave",
			"val": 0
		},
		"a1": {
			"cmd": "goto",
			"target": "goal",
			"goal": "G6"
		},
		"a11": {
			"cmd": "tag_omni",
			"camName_check": "cam1",
			"bundleName_check": "SideA",
			"sensor_name": "cam1",
			"bundle_name": "SideA",
			"max_err_check": 30,
			"use_robot_center": true,
			"online_dis" : 60,
			// side docking param | offset_x: -780.785517, offset_y: -105.686107, offset_t: -0.213729
			//设个offset_t是解决旋转的，57*需要旋转的距离mm，减小是顺时针，增加是逆时针
			"offset_x": -780.785517,
			"offset_y": -105.686107,
			"offset_t": -0.213729,
			"permit_errort": 16,
      "max_error_x": 4,
			"max_error_y": 4,
			"max_error_t": 0.4,
			"is_check_pose": true,
			"safe": true,
			"ID": "3",
			"readID": false,
			"safety_reduction_distance": 1,
			"stret_light_io": 1,
			"is_check_id": false
		},
		"a111":{
			"cmd": "modbus_set",
			"register_type": "input_registers",
			"addr": 82,
			"val_type": "uint32",
			"device_name": "rms_modbus_slave",
			"val": 11
		},
		"a110":{
			"cmd": "b"
		},
		"a112":{
			"cmd": "move_omni",
			"move_angle": 0,
			"distance": -230,
			"direction": "back",
			"speed": -100
		},
		"a1121":{
			"cmd": "a1"
		}
}
```

![画板](https://cdn.nlark.com/yuque/0/2026/jpeg/35951869/1773646795147-2d9c1f89-4eb2-4baa-91c7-607567f2d6e9.jpeg)





