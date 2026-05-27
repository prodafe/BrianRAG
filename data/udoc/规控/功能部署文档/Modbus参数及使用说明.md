---
title: Modbus参数及使用说明
description: 
published: true
date: 2026-04-01T07:19:39.441Z
tags: 使用说明, 公开, modbus
editor: markdown
dateCreated: 2026-01-28T01:29:07.556Z
---

# Modbus参数及使用说明
  
| 文件名称 | Modbus功能介绍  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 公开 |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2026-03-31 | 张宜行  | Modbus参数及使用说明 |  |
# 一.机器人主/从站选择

说明：根据项目要求中，机器人做主站还是从站，配置相应的参数；

+ **<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">主站</font>**<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">：拥有</font>**<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">通信发起权</font>**<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">，主动轮询 / 指令从站，决定通信时序、数据交互的时机和内容，可管理多个从站，是通信网络的 “指挥中心”；</font>
+ **<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">从站</font>**<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">：无主动通信权，仅在</font>**<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">接收到主站指令后被动响应</font>**<font style="color:rgb(31, 35, 41);background-color:rgba(0, 0, 0, 0);">，完成数据上传（如采集的传感器数据）或下载（如执行主站的控制指令），一个从站通常只对应一个主站（多主站场景除外）。</font>



## 1.机器人做调度rms从站(服务器)

文件位置及参数

```json
/usr/local/urobot/params/service/rms.json
```

```json
"rms_modbus_slave":{
    "enable": true,											// 是否开启RMS从机
		"device_name": "rms_modbus_slave", 	// RMS从站名称(必须写为"rms_modbus_slave")
		"protocol": "tcp",									// (暂未使用此参数)
		"listen_ip": "0.0.0.0", 						// 监听IP地址
		"listen_port": 1502, 								// 监听端口号(需要大于1024)(需要根据实际情况配置)
		"slave_id": -1, 										// 从站ID
		"coil_addr": 0, 										// 线圈寄存器起始地址(从站可读写线圈寄存器)(功能码01 05 15)(需要根据实际情况配置)
		"coil_count": 2000, 								// 线圈寄存器数量(需要根据实际情况配置)
		"holding_register_addr": 0, 				// 保持寄存器起始地址(从站可读写保持寄存器)(功能码03 06 16)(需要根据实际情况配置)
		"holding_register_count": 2000, 		// 保持寄存器数量(需要根据实际情况配置)
		"discrete_input_addr": 0, 					// 离散输入寄存器起始地址(从站可读写离散输入寄存器)(功能码02)(需要根据实际情况配置)
		"discrete_input_count": 2000, 			// 离散输入寄存器数量(需要根据实际情况配置)
		"input_register_addr": 0, 					// 输入寄存器起始地址(从站可读写输入寄存器)(功能码04)(需要根据实际情况配置)
		"input_register_count": 2000, 			// 输入寄存器数量(需要根据实际情况配置)
		"byte_order": "HighWordFirst" 			// 字节顺序，HighWordFirst高端对齐，LowWordFirst低端对齐(默认值："LowWordFirst")
},
"modbus_status_params":{
		"enable":true, 					// 是否开启Modbus状态上报
		"heart_interval":1000 	// 机器人心跳间隔，即机器人心跳信号改变一次的时间，-1表示不开启(单位：ms)(整数类型)
},
"modbus_task_params":{
		"enable":true, 								// 是否开启Modbus任务
		"machine_heart_interval":-1, 	// 上装机构心跳间隔时间，即信号改变一次的时间，-1表示不开启(单位：ms)(整数类型)
		"rms_heart_interval":1000 		// RMS心跳间隔时间，即信号改变一次的时间，-1表示不开启(单位：ms)(整数类型)
}
```



## 2.机器人做主站(客户端)

①文件位置及参数：配置modbus_master.json文件位置

```json
/usr/local/urobot/params/params.json
```

```json
"modbus_master": {
		"params_type": "file",
		"params_path": "device/modbus_master.json"
}
```



②文件位置及参数：配置主站参数

```json
/usr/local/urobot/params/device/modbus_master.json
```

```json
{
"modbus_master_1":{
  "enable": true,										// 是否开启主站
	"device_name": "modbus_master_1", // 主站名称(若有多个主站，命名分别为"modbus_master_1"/"modbus_master_2"……)
	"protocol": "tcp",								// (暂未使用此参数)
	"listen_ip": "10.8.8.100", 				// 监听IP地址
	"listen_port": 1502, 							// 监听端口号(需要大于1024)(需要根据实际情况配置)
	"slave_id": 1, 										// 从站ID
	"coil_addr": 0, 									// 线圈寄存器起始地址(主站可读写线圈寄存器)(功能码01 05 15)(需要根据实际情况配置)
	"coil_count": 2000, 							// 线圈寄存器数量
	"holding_register_addr": 0, 			// 保持寄存器起始地址(主站可读写保持寄存器)(功能码03 06 16)(需要根据实际情况配置)
	"holding_register_count": 2000, 	// 保持寄存器数量
	"discrete_input_addr": 0, 				// 离散输入寄存器起始地址(主站只可读离散输入寄存器)(功能码02)(需要根据实际情况配置)
	"discrete_input_count": 2000, 		// 离散输入寄存器数量
	"input_register_addr": 0, 				// 输入寄存器起始地址(主站可读写输入寄存器)(功能码04)(需要根据实际情况配置)
	"input_register_count": 2000, 		// 输入寄存器数量
	"byte_order": "HighWordFirst", 		// 字节顺序，HighWordFirst高端对齐，LowWordFirst低端对齐(默认值："LowWordFirst")
  "plc_type": "***"									// plc类型(默认值为空)
},
"modbus_master_2":{
  ……
},
……
}
```



## 3.modbus_slave(暂未使用)

①文件位置及参数：配置modbus_slave.json文件位置

```json
/usr/local/urobot/params/params.json
```

```json
"modbus_slave": {
		"params_type": "file",
		"params_path": "device/modbus_slave.json"
}
```

②文件位置及参数：配置从站参数

```json
/usr/local/urobot/params/device/modbus_slave.json
```

```json
{
  "enable": true,		// 是否开启从机
	"device_name": "robot_controller", // 机器人控制器
	"protocol": "tcp",	// (未使用)
	"listen_ip": "0.0.0.0", // 监听IP地址
	"listen_port": 1502, // 监听端口号,大于1024
	"slave_id": -1, // 从站ID
	"coil_addr": 0, // 线圈寄存器起始地址，读写，功能码01 05 15
	"coil_count": 2000, // 线圈寄存器数量，读写，功能码01 05 15
	"holding_register_addr": 0, // 保持寄存器起始地址，读写，功能码03 06 16
	"holding_register_count": 2000, // 保持寄存器数量，读写，功能码03 06 16
	"discrete_input_addr": 0, // 离散输入寄存器起始地址，只读，功能码02
	"discrete_input_count": 800, // 离散输入寄存器数量，只读，功能码02
	"input_register_addr": 0, // 输入寄存器起始地址，只读，功能码04
	"input_register_count": 800, // 输入寄存器数量，只读，功能码04
	"byte_order": "HighWordFirst" // (未使用)字节顺序，HighWordFirst高端对齐，LowWordFirst低端对齐
}
```







# 二.routes任务配置

## 说明

机器人会读取<font style="color:rgb(51, 51, 51);">holding register寄存器地址位为200("机器人目标站点")的值，并执行该目标站点中"routes_name"在routes文件中对应的任务；</font>
<font style="color:rgb(51, 51, 51);"></font>
![画板](https://cdn.nlark.com/yuque/0/2026/jpeg/35951869/1772263817148-cb7984b7-28d5-42b0-b218-feba800bab02.jpeg)

## <font style="color:rgb(51, 51, 51);">参数</font>

1.文件位置及参数：配置modbus_task.json文件位置

```json
/usr/local/urobot/params/params.json
```

```json
"modbus_task": {
    "params_type": "file",
    "params_path": "routes/modbus_task.json"
}
```



2.文件位置及参数：配置机器人目标站点对应的routes中的任务

```json
usr/local/urobot/params/routes/modbus_task.json
```

```json
{
  // "机器人目标站点"(正数)对应的任务；如"机器人目标站点"的值为1，则机器人会执行"1"任务
	"1": {
		"routes_name": "routes_1", 	// 需要触发routes文件中的任务名称
		"key": "a", 								// 从"routes_1"任务中的哪个小任务开始执行(默认为"a")
		"job_id": 1 								// 任务的id号(需要是大于0的整数)(默认为"机器人目标站点"的值)(每个任务的id号不能相同！)
	},
	"2": {
		"routes_name": "routes_2", 	// 需要触发routes文件中的任务名称
		"key": "a", 								// 从"routes_2"任务中的哪个小任务开始执行(默认为"a")
		"job_id": 2 								// 任务的id号(需要是大于0的整数)(默认为"机器人目标站点"的值)(每个任务的id号不能相同！)
	},
  ……
}
```

注：机器人目标站点(该参数取值范围是1/2/3……之类的正数)

<!-- 这是一张图片，ocr 内容为：MODBUS地址含义表 提醒直阅 快捷工具 视图 插入数据公式 开始 Y图冻结"乏求和"白 田田 默认字体  换行 自动化通知 R 收集表单 常规 表格样式 @AI分类总结 翻条件格式 三 筛选弘排序数据保护 I 图合并 % OPP.0 B 生成仪表盘 数据分组 川 页面设置打印 插入 E11 功能 备注 第一阶段是否做 单位 地址位 数据类型 手动X方向速度 上装抢占控制权后生效;有最大速度限制 2 FLOAT32 0 M/S 上装抢占控制权后生效;有最大速度限制 手动Y方向速度 3 2 M/S FLOAT32 上装抢占控制权后生效;有最大速度限制 手动旋转速度 4 RAD/S 4 FLOAT32 上装抢占控制权后生效 5 FLOAT32 6  M/S 自动任务速度 开环下发机器人舵角(机器人坐标系) 上装抢占控制权后生效 6 FLOAT32 8 RAD 7 8 需要播放的语音的名字, 播放音频 30 6 UINT16 10 11 机器人目标站点 12 UINT32 200 13 14 上装1#位物料状态 以下客户自定义 15 1000 上装2#位物料状态 16 1001 17 1002 上装3位物料状态 上装4#位物料状态 18 1003 上装抓手物料状态 19 1004 20 上装1#位物料编码 1010 21 上装2#位物料编码 1030 上装3#位物料编码 22 1050 23 上装4位物料编码 1070 24 上装抓手物料编码 1090 25 26 27 COIL线圈功能码1515 + S HOLDING REGISTER 功能码3 6 16 ~ DISCRETE INPUT 离散输入功能码2 INPUTS 输入奇存器 功能码4 134% -->
![](https://cdn.nlark.com/yuque/0/2025/png/35951869/1766366476277-58ff0107-9ec0-4e7e-8b9f-de11ba0df480.png)

3.举例说明

如在modbus_task.json中做如下配置

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

当机器人读取到机器人<font style="color:rgb(51, 51, 51);">holding register寄存器地址位为200的值为1时，会执行routes.json文件中名为"test1"任务的"a"(即"rms_goto"任务)</font>

```json
"test1":{
		"a": {
			"cmd": "rms_goto",
			"goal": "Target1",
			"target": "goal",
			"safe": false
		},
		"b": {
			"cmd" : "move",
			"distance" : 1600,
			"speed" : 150
		}
}
```







# 三.通过mode控制寄存器的值

## 说明

本任务用于读/写寄存器的值；

从站：可以读/写四种寄存器；

主站：可以读四种寄存器；只能写"线圈寄存器"和"保持寄存器"；



## 参数

```json
"cmd": "modbus_set"/"modbus_check",		// 设置寄存器的值/获取寄存器的值
"register_type": "coils"/"holding_registers"/"discrete_inputs"/"input_registers",		// 寄存器类型：线圈寄存器/保持寄存器/离散输入寄存器/输入寄存器
"device_name": "rms_modbus_slave"/"modbus_master_1"/"modbus_master_2"……,		// 设置/获取值的是哪个设备，如"调度从机"/"主机1"/"主机2"……
"addr": ***,		// 设置/获取值的地址
"val_type": "int32"/"uint32"/"float32"/"int16"/"uint16"/"bool",			// "val"值的类型
"val": ***			// 当"cmd":"modbus_set"时，"val"为要设置的值，当"cmd":"modbus_check"，"val"为预期从寄存器读取到的值；当"type":"bool"时，"val"的值为true/false；
```





# <font style="color:rgb(51, 51, 51);">四.四种寄存器说明</font>

从站：可以读/写四种寄存器；

主站：可以读四种寄存器；只能写"<font style="color:rgb(51, 51, 51);">coil</font>线圈寄存器"和"<font style="color:rgb(51, 51, 51);">holding register</font>保持寄存器"；

## 1.coil线圈(功能码1/5/15)

| 功能               | 地址位 | 备注                                                         | 是否实现该地址位 |
| ------------------ | ------ | ------------------------------------------------------------ | ---------------- |
| 上装心跳           | 0      | 根据rms.json文件"modbus_task_params"中的"machine_heart_interval"(心跳间隔)在0和1交替 |                  |
| 上装准备好         | 1      |                                                              |                  |
| 上装抢占控制权     | 2      | 上装抢占机器人移动控制权：0为机器人自动，1为上装手动控制机器人移动 |                  |
| 上装故障           | 3      |                                                              |                  |
| 上装急停           | 4      |                                                              |                  |
| 上装上下料中       | 5      |                                                              |                  |
|                    |        |                                                              |                  |
|                    |        |                                                              |                  |
|                    |        |                                                              |                  |
| 调度心跳           | 200    | 根据rms.json文件"modbus_task_params"中的"rms_heart_interval"(调度心跳间隔)在0和1交替 |                  |
| 调度准备好         | 201    |                                                              |                  |
|                    |        |                                                              |                  |
|                    |        |                                                              |                  |
|                    |        |                                                              |                  |
| 上料台准备好       | 1000   | 1000及以下地址位用户自定义                                   |                  |
| 上料台允许取料     | 1001   |                                                              |                  |
| 上料台故障中       | 1002   |                                                              |                  |
| 备用               | 1003   |                                                              |                  |
| 备用               | 1004   |                                                              |                  |
| 工作切片机准备好   | 1005   |                                                              |                  |
| 工作切片机允许进入 | 1006   |                                                              |                  |
| 工作切片机故障中   | 1007   |                                                              |                  |



## 2.holding register寄存器(功能码3/6/16)

| 功能                               | 数据类型 | 地址位 | 单位  | 备注                                                | 是否实现该地址位 |
| ---------------------------------- | -------- | ------ | ----- | --------------------------------------------------- | ---------------- |
| 手动x方向速度                      | float32  | 0      | m/s   | 上装抢占控制权后生效；速度范围为[-0.5,0.5]          |                  |
| 手动y方向速度                      | float32  | 2      | m/s   | 上装抢占控制权后生效；速度范围为[-0.5,0.5]          |                  |
| 手动旋转速度                       | float32  | 4      | rad/s | 上装抢占控制权后生效；速度范围为[- 0.1745 , 0.1745] |                  |
| 自动任务速度                       | float32  | 6      | m/s   | 上装抢占控制权后生效                                |                  |
| 开环下发机器人舵角（机器人坐标系） | float32  | 8      | rad   | 上装抢占控制权后生效                                |                  |
|                                    |          |        |       |                                                     |                  |
|                                    |          |        |       |                                                     |                  |
|                                    |          |        |       |                                                     |                  |
| 播放音频                           | uint16   | 30     |       | 需要播放的语音的名字                                |                  |
|                                    |          |        |       |                                                     |                  |
|                                    |          |        |       |                                                     |                  |
|                                    |          |        |       |                                                     |                  |
| 机器人目标站点                     | uint32   | 200    |       | 机器人要执行的任务号，详细说明见"二.routes任务配置" |                  |
|                                    |          |        |       |                                                     |                  |
|                                    |          |        |       |                                                     |                  |
|                                    |          |        |       |                                                     |                  |
| 上装1#位物料状态                   |          | 1000   |       | 1000及以下地址位用户自定义                          |                  |
| 上装2#位物料状态                   |          | 1001   |       |                                                     |                  |
| 上装3#位物料状态                   |          | 1002   |       |                                                     |                  |
| 上装4#位物料状态                   |          | 1003   |       |                                                     |                  |
| 上装抓手物料状态                   |          | 1004   |       |                                                     |                  |
| 上装1#位物料编码                   |          | 1010   |       |                                                     |                  |
| 上装2#位物料编码                   |          | 1030   |       |                                                     |                  |
| 上装3#位物料编码                   |          | 1050   |       |                                                     |                  |
| 上装4#位物料编码                   |          | 1070   |       |                                                     |                  |
| 上装抓手物料编码                   |          | 1090   |       |                                                     |                  |

注：手动移动机器人的速度方向说明

<!-- 这是一张图片，ocr 内容为：X正方向 旋转速度为负 旋转速度为正 刀 车头 Y正方向 -->
![](https://cdn.nlark.com/yuque/0/2026/png/35951869/1769651681611-52f24d1d-4d48-4d10-b334-c21a48be0596.png)



## 3.discrete input离散输入(功能码2)

| 功能               | 地址位 | 备注                                                         | 是否实现该地址位 | 问题                                                         |
| ------------------ | ------ | ------------------------------------------------------------ | ---------------- | ------------------------------------------------------------ |
| 机器人心跳         | 0      | 根据rms.json文件 中"modbus_status_params"的"heart_interval" (心跳间隔)在0和1交替 |                  |                                                              |
| 是否在充电         | 1      |                                                              |                  |                                                              |
| 是否急停           | 2      | 机器人移动中遇到障碍物会急停                                 |                  |                                                              |
| 是否抱闸           | 3      |                                                              |                  |                                                              |
| 手动状态           | 4      | 手动：底盘会先减速，控制舵轮先旋转到指定角度，再移动；       |                  | 手动和自动状态互斥，此处手动为下位机的机械手动模式，部分机器人无手动模式 |
| 自动状态           | 5      | 自动：需要上位机计算控制减速旋转速度；                       |                  |                                                              |
| modbus抢占控制状态 | 6      | 是否处于上装抢占控制状态                                     |                  |                                                              |
| 机器人停止         | 7      | 机器人处于"stop"                                             |                  |                                                              |
| 机器人准备好       | 8      | 机器人初始化完成                                             |                  |                                                              |
| 机器人运行中       | 9      | 机器人不处于"stop"或"idle"                                   |                  |                                                              |
|                    |        |                                                              |                  |                                                              |
|                    |        |                                                              |                  |                                                              |
|                    |        |                                                              |                  |                                                              |
| 上装心跳异常       | 101    | 检测到上装心跳异常时为1（coil地址0异常）                     |                  |                                                              |
| 调度心跳异常       | 102    | 检查到调度心跳异常时为1（coil地址200异常）                   |                  |                                                              |
| path心跳异常       | 103    | 检查到path心跳异常时为1（coil地址400异常）                   |                  |                                                              |
|                    |        |                                                              |                  |                                                              |
|                    |        |                                                              |                  |                                                              |
|                    |        |                                                              |                  |                                                              |
| 请求上装工作       | 200    |                                                              |                  |                                                              |



## 4.inputs输入寄存器(功能码4)

| 功能                 | 数据类型 | 地址位 | 单位   | 备注                                                         | 是否实现该地址位 |
| -------------------- | -------- | ------ | ------ | ------------------------------------------------------------ | ---------------- |
| 机器人x坐标          | float32  | 0      | m      |                                                              |                  |
| 机器人y坐标          | float32  | 2      | m      |                                                              |                  |
| 机器人角度坐标       | float32  | 4      | rad    | 范围-pi～pi                                                  |                  |
| 机器人 VX 速度       | float32  | 6      | m/s    |                                                              |                  |
| 机器人 VY 速度       | float32  | 8      | m/s    |                                                              |                  |
| 机器人角速度         | float32  | 10     | rad/s  |                                                              |                  |
| 机器人定位状态       | uint16   | 12     |        | 0 定位失败，1定位正确，2 正在重定位                          |                  |
| 机器人定位置信度     | uint16   | 13     |        | 0-1000                                                       |                  |
| 电池电量             | uint16   | 14     |        | 0-100                                                        |                  |
| 电池温度             | float32  | 16     | 摄氏度 |                                                              | no               |
| 电池电压             | float32  | 18     |        |                                                              |                  |
| 电池电流             | float32  | 20     |        |                                                              | no               |
| 电池充放电次数       | float32  | 22     |        |                                                              | no               |
| 电池寿命             | float32  | 24     |        |                                                              | no               |
| 控制器温度           | float32  | 30     |        |                                                              | no               |
| 控制器湿度           | float32  | 32     |        |                                                              | no               |
| 控制器电压           | float32  | 34     |        |                                                              | no               |
| 控制器温度           | float32  | 36     |        |                                                              | no               |
| 控制器湿度           | float32  | 38     |        |                                                              | no               |
| 控制器电压           | float32  | 40     |        |                                                              | no               |
| 总里程               | float32  | 50     |        |                                                              |                  |
| 累计运行时间         | float32  | 52     |        |                                                              | no               |
| Fatal 错误码         | uint16   | 70     |        |                                                              | no               |
| Error 错误码         | uint16   | 71     |        |                                                              | no               |
| Error 错误码集合     | uint16   | 72     |        |                                                              | no               |
| Warning 错误码       | uint16   | 73     |        |                                                              | no               |
| 机器人当前任务号     | uint32   | 80     |        | 0为无任务，或者任务id非数字； 对应modbus_task.json中相应目标站点的"job_id" |                  |
| 机器人完成的任务点号 | uint32   | 82     |        | 0或者与当前任务号不匹配为未完成； 可以在routes任务的最后一个小任务中，通过mode将该地址位改为当前任务点号，表示任务完成 |                  |
|                      |          |        |        |                                                              |                  |
| 机器人顶升状态       | uint16   | 100    |        | 0为下降，1为顶升，2为顶生下降中                              |                  |




