---
title: 双舵轮-move参数说明
description: 
published: true
date: 2025-12-17T11:17:47.556Z
tags: 双舵轮, 参数说明, move
editor: markdown
dateCreated: 2025-09-02T06:02:30.899Z
---

# 双舵轮-move参数说明
  
| 文件名称 | 双舵轮-move参数说明  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 保密（部门内部公开） |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2025-09-02 | Fan Xie  | 双舵轮-move | 双舵轮-move中使用的参数的含义 |

## 一、概述
简单解释双舵轮-move中会用到的参数的含义。通用参数通常在task.json，不同任务对应的专用参数则在routes.json中配置，如果一个参数同时出现在task.jsonh和routes.json中，则以routes.json为准。
安全参数说明参考[安全相关参数](/规控/参数说明文档/安全相关参数)

## 二、参数
| 参数 | 数据类型 | 默认值 | 概述 | 
| :---: | :----------: | :--------: | --------- | 
| distance | int | 0 | move距离，单位毫米 | 
| speed | double | 0 | move速度，单位毫米每秒 | 
| move_angle | double | 0 | move方向，单位度，如左移就是90，一般使用场景优先配置direction就可以，除非需要沿非前后左右四个方向移动的场景 |
| direction | String | "" | move方向，可以设置为"left","L“，”right“,"R","front","F","back","B"，若设置了direction，则move_angle将会被覆盖 |
| time | double | -1 | 任务执行时间，默认为无限制 |
| use_io | bool | false | 用于基于 IO 信号的任务状态判断与控制 |
| io | int | 0 | 需要监测的 IO 位在输入字符串中的位置（偏移量），仅仅use_io为true时有效 |
| flag | String | "1" | 定义 “预期的 IO 状态”，作为判断任务是否达到目标状态的基准值，仅仅use_io为true时有效 |
| log | bool | false |  |
| front_obs_warn_dist | double | -1 | 距离终点只有多少时警铃报警 |
| path_list | String | "" | 获取并处理需要锁定的途经点列表 |
**用于在move过程中忽略特殊区域激光障碍物点的相关参数** 
| :---: | :----------: | :--------: | --------- | 
| need_ignore | bool | false | 在特定条件下分区域忽略障碍物信息，一般情况下不使用 |
| ignore_direction | String | "hor" | 用来判断忽略哪个方向的激光数据，分为水平方向（"hor"）和竖直方向（非"hor"），只有当need_ignore为true时，参数才能生效 |
| side_ignore_topic | String | "box" | 当需要忽略竖直方向的激光点时，该参数需要配置成对应的话题名称，才能使忽略指令生效 |
| up_ignore_topic | String | "box" | 当需要忽略水平方向的激光点时，该参数需要配置成对应的话题名称，才能使忽略指令生效 |
| ignore_front | double | 1 | 需要忽略的立方体区域，最前方坐标在机器人坐标系x轴的数值 |
| ignore_back | double | -1 | 需要忽略的立方体区域，最后方坐标在机器人坐标系x轴的数值 |
| ignore_left | double | 1 | 需要忽略的立方体区域，最左方坐标在机器人坐标系y轴的数值 |
| ignore_right | double | -1 | 需要忽略的立方体区域，最右方坐标在机器人坐标系y轴的数值 |
| ignore_top | double | 1 | 需要忽略的立方体区域，最上方坐标在机器人坐标系z轴的数值 |
| ignore_down | double | -1 | 需要忽略的立方体区域，最下方坐标在机器人坐标系z轴的数值 |