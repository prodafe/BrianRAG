---
title: 二维码对接参数说明文档
description: 
published: true
date: 2025-12-17T11:37:20.908Z
tags: tag, 参数说明, 对接, 二维码
editor: markdown
dateCreated: 2025-06-11T07:24:47.928Z
---

# 二维码对接参数说明文档
  
| 文件名称 | 二维码对接参数说明文档  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 保密（部门内部公开） |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2025-06-10 | caopan  | tag omni | 基本参数说明 |

# 1.功能介绍
该功能用于向相机识别程序发送开始结束信号，然后利用识别结果进行移动的功能

Mode最终返回1，表示成功，机器人可以执行下一步，

Mode返回0表示对接失败，需要根据现场routes进行失败报警，或者重新对接。

Mode返回2表示刚开始对接就拿不到结果，需要根据现场routes进行失败报警。

# 2.参数介绍
## 2.1 通用参数（task.json）
通用参数写在<span style="color:#DF2A3F;">task.json</span>的tag_omni大括号中

### 2.1.1 对接时的避障相关参数
参数主要用于指定对接过程中的避障参数，当避障缩减区生效时，则使用地图中的缩减区参数

```json
  "clearance_back_max": 500,//单位 mm
  "clearance_back_min": 200,//单位 mm
  "clearance_front_max": 500,//单位 mm
  "clearance_front_min": 200,//单位 mm
  "clearance_left_side_max": 500,//单位 mm 暂时未使用
  "clearance_left_side_min": 100,//单位 mm 暂时未使用
  "clearance_right_side_max": 500,//单位 mm 暂时未使用
  "clearance_right_side_min": 100,//单位 mm 暂时未使用
  "clearance_side_max": 500,//单位 mm
  "clearance_side_min": 100,//单位 mm
  "use_avoid_area" : true,
```
| 参数名称 | 参数含义 |
| --- | --- |
| clearance_back_max | 对接时的最大后方避障区，机器人进入该区域后开始限制前后最大速度 |
| clearance_back_min | 对接时的最小后方避障区，机器人进入该区域后会避障停车 |
| clearance_front_max | 对接时的最大前方避障区，机器人进入该区域后开始限制前后最大速度 |
| clearance_front_min | 对接时的最小前方避障区，机器人进入该区域后会避障停车 |
| clearance_side_max | 对接时的最大侧方避障区，机器人进入该区域后开始限制左右最大速度 |
| clearance_side_min | 对接时的最小侧方避障区，机器人进入该区域后会避障停车 |
| use_avoid_area | 是否使用避障缩减区，有些狭窄的对接场景，直接用通用避障参数可能会卡避障，这就需要把参数改为true，然后在地图上同步加避障缩减区 |


### 2.1.2 移动相关参数
用于规定对接时的运动速度

```json
  "speed" : 100,//单位 mm/s
  "angle_speed" : 20,//单位 度/s
  "min_speed" : 10,//单位 mm/s
  "min_angle_speed" : 1,//单位 度/s
```
| 参数名称 | 参数含义 |
| --- | --- |
| speed | 移动过程中的最大线速度 |
| angle_speed | 旋转过程中的最大角速度 |
| min_speed | 移动过程中的最小线速度，当精度要求高时，参数写小一些，提高停车精度，当精度要求低时，参数写大一些，提高运行效率 |
| min_angle_speed | 旋转过程中的最小角速度，原理同min_speed |


### 2.1.3 多车一致性参数
用于统一车与车之间的差异性，当误差要求不高时，只需要一台车标定机台，其他车可以直接配合一致性参数使用相同的对接参数

```json
  "offset_addt" : 0,//单位 度
  "offset_addx" : 0,//单位 mm
  "offset_addy" : 0,//单位 mm
```
| 参数名称 | 参数含义 |
| --- | --- |
| offset_addx | 多车一致性参数，当现场按照第一台车对接完所有机台后，发现第二台车用相同参数都前后偏5mm，则通过该参数使机器人在所有机台停车位置移动5mm<br/>靠近机台为正，远离机台为负。<br/>由于改参数只需要修改一次就对所有机台生效，所以使用时要确认要所有机台同时修改，轻易不要使用 |
| offset_addy | 作用同offset_addx<br/>左正右负 |
| offset_addt | 作用同上<br/>逆时针为正，顺时针为负 |


### 2.1.4 防错参数
用于防止一次定位不准或者机台发生移动，机器人走到两个机台中间，会识别到错误的机台

```json
"need_check_init" : false,//料车对接使用，二维码对接默认false
"permit_errort" : 10,//单位 度
"permit_errorx" : 1200,//单位 mm
"permit_errory" : 300,//单位 mm
```
| 参数名称 | 参数含义 |
| --- | --- |
| need_check_init | 是否打开起点的误差检测 |
| permit_errorx | 当机器人开始对接二维码时，利用识别到的第一帧数据，计算机器人距离终点的前后偏差，超过设定值认为识别到的二维码不是任务对应的二维码 |
| permit_errory | 同理，左右偏差超出阈值也认为识别有误 |
| permit_errort | 同理，角度大于阈值也认为识别有误 |


### 2.1.5 增加起点处的上线功能
增加起点附近先调整横向误差和角度误差的功能，提高对接稳定性

```json
  "online_dis" : 10,//单位 mm
  "online_angle" : 1,//单位 度
```
| 参数名称 | 参数含义 |
| --- | --- |
| online_dis | 起点处先横移到中心线的阈值，如果小车对接要进入窄通道，就需要把值设置的很小，只要起步误差大于该阈值，就先会横移到中心线，如果对接不要求起步处的误差，可以适度放大阈值，以便减少对接动作 |
| online_angle | 起点处先原地旋转，消除角度误差的阈值，功能和online_dis类似 |


### 2.1.6 其他参数
```json
  "record_bag" : true,
  "is_check_pose" : false,
  "odom_dis1" : 100，//单位 mm
  "use_robot_center" : false,//对接参数的参考坐标是不是机器人中心
  "start_check_cam" : false//料车对接使用，二维码对接默认false
```
| 参数名称 | 参数含义 |
| --- | --- |
| record_bag | 在二维码对接模式下，该参数没有意义 |
| is_check_pose | 是否将最后的二维码精校验步骤集成在当前mode中，默认为false |
| odom_dis1 | 二维码对接过程中，允许偶尔没有定位结果，靠里程计预测进行位姿递推，该参数表示允许的没有定位结果的最长距离 |
| use_robot_center | 对接参数是否以机器人中心为基准 |
| start_check_cam | 二维码对接，改参数必须是false |


## 2.2 专用参数(routes.json)
机台参数需要写在<span style="color:#DF2A3F;">routes.json</span>中

### 2.2.1 二维码对接指令
```json
"cmd": "tag_omni"
```

### 2.2.2 定义对接相机及二维码名称
这部分参数决定了对接用到的相机及二维码名称

```json
"sensor_name": "cam0",//识别二维码带用到的相机
"bundle_name": "bundle0",//识别的二维码带名称            
"sensor_name_check": "cam0",//默认与sensor_name相同，除非需要连续切换两个相机
"bundle_name_check": "bundle0"//默认与bundle_name相同，除非需要连续切换两个码
```
| 参数名称 | 参数含义 |
| --- | --- |
| sensor_name | 识别二维码对应的相机，一般默认<br/>cam0向前<br/>cam1 向上<br/>cam3 向右<br/>cam4  向后<br/>cam5 向下 |
| bundle_name | 对接用到的二维码名称，需要和视觉配置文件对应 |
| sensor_name_check | 默认与sensor_name相同 |
| bundle_name_check | 默认与bundle_name相同 |


### 2.2.3 配置停车位置参数
该部分参数，决定可以机器人对接时的移动方向，以及机器人最终的停车位置

```json
"use_robot_center": true,//以机器人中心为控制中心
"anglePathdiff" : 0,//单位 度
"odom_dis": 480,//单位 mm
"offset_x": 0,//单位 mm
"offset_y": 0,//单位 mm
"offset_t": 90,//单位 度          
```
| 参数名称 | 参数含义 |
| --- | --- |
| use_robot_center | 定义的停车点参数是否以机器人中心为参考基准 |
| anglePathdiff | 机器人对接时，相对于二维码的移动方向，接近二维码为0度，看着二维码后退为180度，与二维码平行左移为90度，右移为负90度 |
| offset_x | 靠识别二维码移动停在二维码坐标系下的x方向的坐标，二维码粘贴时，一般将x轴指向机台 |
| offset_y | 靠识别二维码移动停在二维码坐标系下的y方向的坐标,左正右负 |
| offset_t | 靠识别二维码移动停在二维码坐标系下的x方向的坐标，逆时针为正，顺时针为负 |
| odom_dis | 一般默认为0，当最终的停车位置无法完全依靠二维码进行引导时，需要通过（offset_x，offset_y，offset_t）确定一个可以依靠二维码实现引导的点，在此基础上额外增加出的一段移动距离 |


