---
title: Mode说明
description: 
published: true
date: 2025-12-17T11:45:47.123Z
tags: mode, 研发说明
editor: markdown
dateCreated: 2025-06-24T07:31:01.236Z
---

# 玖物机器人Mode说明
## head
### 以一定的角速度旋转一定的角度
|参数|类型|含义|
|---|---|---|
|speed|float|旋转速度，单位degree/s，不分正负|
|angle|float|旋转角度，单位degree，根据正负决定旋转方向|
### 返回值
1：旋转结束，已旋转角度与目标角度差在一度之内；或者已选转角度超过了目标角度
### 示例
以30度每秒的角速度旋转90度  
{  
&emsp;"cmd": "head",  
&emsp;"speed": 30,  
&emsp;"angle": 90  
}

## goto
### 机器人自由移动到目标点
|参数|类型|含义|
|---|---|---|
|target|string|只能填写"pose"或者"goal"，"pose"代表移动到指定的(x,y,th)，"goal"代表移动到地图上的某一个点|
|x|int|目标点的x坐标，单位mm|
|y|int|目标点的y坐标，单位mm|
|th|int|目标点的角度，单位degree|
|goal|string|目标点名称，地图上确有该点时方可正常移动|
|time|float|超时时间，单位s|
### 返回值
1：成功移动到位  
0：移动失败，超时；或者找不到目标点；或者指定坐标/目标点无法到达
### 示例
移动到地图上的（3000,3000,90）坐标点  
{  
&emsp;"cmd": "goto",  
&emsp;"target": "pose",  
&emsp;"x": 3000,  
&emsp;"y": 3000,  
&emsp;"th": 90,  
&emsp;"time": 60  
}  
移动到地图上的G1目标点  
{  
&emsp;"cmd": "goto",  
&emsp;"target": "goal",  
&emsp;"goal": "G1",  
&emsp;"time": 60  
}  

## socket
### tcp通讯
|参数|类型|含义|
|---|---|---|
|ip|string|tcp服务端的ip|
|port|int|服务端的端口|
|time|float|超时时间，单位s|
|send|string|发送数据|
|need_reply|bool|是否需要回复|
### 返回值
1：发送成功且need_reply为false  
0：连接失败；发送失败；need_reply为true时，超时未收到回复  
自定义：need_reply为true时，收到回复匹配到自定义返回值
### 示例
往指定的tcp服务端发送数据  
{  
&emsp;"cmd": "socket",  
&emsp;"ip": "192.168.1.100",  
&emsp;"port": 9001,  
&emsp;"time": 5,  
&emsp;"send": "arrived",  
&emsp;"need_reply": true  
}  
need_reply配置在params/service/info.json文件中，"socket"字段  
格式：{ "recv": 2 }  
表示收到了recv则该mode返回2

## wait
### 停止机器人，等待一定时间
|参数|类型|含义|
|---|---|---|
|time|int|等待时间，单位s|
### 返回值
1：等待时间结束  
0：若全局配置task.json中，"wait|check_motor"配置为1，则检查驱动器使能，未使能则返回0
### 示例
等待10s  
{  
&emsp;"cmd": "wait",  
&emsp;"time": 10  
}

## idle
### 停止机器人，使机器人进入空闲状态
|参数|类型|含义|
|---|---|---|
|time|int|等待时间，单位s|
### 返回值
1：等待时间结束
### 示例
进入空闲状态，等待10s  
{  
&emsp;"cmd": "idle",  
&emsp;"time": 10  
}

## set
### 设置机器人状态
|参数|类型|含义|
|---|---|---|
|time|int|等待时间，单位s|
|status|string|状态名称|
### 返回值
1：等待时间结束  
0：若全局配置task.json中，"wait|check_motor"配置为1，则检查驱动器使能，未使能则返回0
### 示例
设置机器人busy状态10s  
{  
&emsp;"cmd": "set",  
&emsp;"status": "busy",  
&emsp;"time": 10  
}

## move
### 机器人前进或者后退一定距离
|参数|类型|含义|
|---|---|---|
|distance|int|移动距离，单位mm|
|speed|float|移动速度，单位mm/s|
|time|float|超时时间，单位s|
### 返回值
1：成功移动超过设定的距离  
0：超时，未移动超过设定的距离
### 示例
前进1米  
{  
&emsp;"cmd": "move",  
&emsp;"distance": 1000,  
}

## arm_pick_up
### 机械臂从机台夹取物料放到机器人的库位上
|参数|类型|含义|
|---|---|---|
|src|string|物料源位置，一般指机台名称，如A1、B1|
|dst|string|指定位置，一般指机器人库位名称，如Z1、Z2、Z3、Z4|
|bar_code|string|将要夹取的物料的条形码|
|max_time|int|该动作运行的最大时间，单位: s，默认为60s|
### 返回值
2：超时，夹取货物超出指定时间max_time
1：成功
0：错误，机械臂有故障或回复信息不匹配
### 示例
从机台A1夹取条形码为“12345678”的货物到机器人自身库位Z1
{  
&emsp;"cmd": "arm_pick_up",  
&emsp;"src": "A1",  
&emsp;"dst": "Z1", 
&emsp;"bar_code": "12345678", 
&emsp;"max_time": 60
}
## arm_drop_down
### 机械臂从机器人的库位夹取物料放到机台上
|参数|类型|含义|
|---|---|---|
|src|string|物料源位置，一般指机器人库位名称，如Z1、Z2、Z3、Z4|
|dst|string|指定位置，一般指机台名称，如A1、B1|
|bar_code|string|将要夹取的物料的条形码|
|max_time|int|该动作运行的最大时间，单位: s，默认为60s|
### 返回值
2：超时，夹取货物超出指定时间max_time
1：成功
0：错误，机械臂有故障或回复信息不匹配
### 示例
从机器人自身库位Z1夹取条形码为“12345678”的货物放到机台A1
{  
&emsp;"cmd": "arm_drop_down",  
&emsp;"src": "A1",  
&emsp;"dst": "Z1", 
&emsp;"bar_code": "12345678",
&emsp;"max_time": 60
}
## arm_iventory_check
### 检查机器人自身库位，并记录库位上物料的条形码信息
|参数|类型|含义|
|---|---|---|
|to_send|string|动作，默认为robot-readcode|
|max_time|int|该动作运行的最大时间，单位: s，默认为60s|
### 返回值
2：超时
1：成功
0：错误，机械臂有故障
### 示例
检查机器人自身库位信息
{  
&emsp;"cmd": "arm_iventory_check",  
&emsp;"to_send": "robot-readcode",
&emsp;"max_time": 60
}