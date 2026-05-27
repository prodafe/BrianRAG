---
title: 4机器人UDP状态协议
description: 
published: true
date: 2025-12-17T11:42:09.396Z
tags: 协议, 单机, 状态
editor: markdown
dateCreated: 2025-06-23T05:50:46.448Z
---

# 机器人 UDP 状态协议

| 文件名称 | 机器人 UDP 状态协议 |
| -------- | ------------------- |
| 部门     | 软件算法部          |
| 版本     | 3.1                 |
| 密级     |保密(部门内公开)                |

## 修改记录

| 版本号 | 修改日期   | 修改人 | 概述                             | 详细说明                            |
| ------ | ---------- | ------ | -------------------------------- | ----------------------------------- |
| 1.0    | 2022-11-14 | Gary   | 机器人向外部单播自己的状态的说明 | 描述数据包格式                      |
| 2.0    | 2025-03-10 | 周嘉星 | 详细描述完整 UDP 数据包格式      | 在 rms_task 模块说明中描述 UDP 协议 |
| 3.0    | 2025-06-22 | Gary   | 整合后改为 markdown 格式         | 描述现有协议以及增加示例            |
| 3.1    | 2025-06-27 | 吴勇毅/Gary   | 增加vy和复合机器人载物信息         |            |
| 3.2    | 2025-07-14 | 吴勇毅   | 增加机器人在不在非任务区字段         |            |
| 3.3    | 2025-08-01 | 吴勇毅   | 增加机器人急停来源等状态         |            |

---

## 一、概述

该协议主要描述机器人给调度系统发送自身状态的数据，通信通过 UDP 进行。

## 二、数据包解析

默认情况下机器人每间隔 1s 向外发送一次 UDP 状态包, 根据 UDP 中包含信息对可以分析当前机器人的坐标、状态、任务等信息, 以下是 UDP 数据包示例:

```json
{
	// 机器人ID相关
	"name": "bot-001",    // str，机器人名称
	"ip": "192.168.1.2",  // str，机器人ip
	// 任务
	"mode": "Stop",       // str，机器人工作模式
	"status": "stopped",  // str，机器人状态
	"rms_status": "busy_3400975",	// 供rms服务器识别IGV当前任务状态  
	"note": 2,            // 当前mode中的note
	// 位置
	"x": 0,               // int, 机器人全局坐标x，单位mm
	"y": 0,               // int, 机器人全局坐标y，单位mm
	"theta": 0,           // double，朝向，角度值deg(-180,180]
	// 速度
	"vf": 0,              // double，线速度, mm/s
	"vr": 0,              // double，角速度, deg/s
	"vy": 0,              // double, 横向速度, mm/s
	// 其他关键信息
	"motor_state": 1,     // int, 1使能 or 0急停
	"battery": 100,       // int，电量, [0-100]
	"is_lost": false,     // 定位是否丢失
  "is_charged": false,  // true:充电中 false:非充电
  "in_no_task_area": false,// true:在非任务区 false:不在非任务区
  "goto_charge": false, //true:去充电的路上 false:非去充电的路上
  "manual_state": false,// 手自动模式状态 true:手动模式 false:自动模式
  "last_goal_name": "A",// 上次goto的目标点
  "charge_station": "dock", //充电点名称
  "estop_from": "bump", //bump:防撞条 button:按键 software:软件 bump,button:防撞条和按钮都触发
	// 统计信息
	"distance": 123.2,    // IGV累计移动里程，单位m
	"power_on_time": "2025-01-08 13:30:34.319",	// IGV开机时间
	// 机型相关的其他信息
	"lift_state": 1,      // 顶升状态, 0:未顶升;1:顶升;2:顶升中
  "carrier": { 					//条形码信息
		"storage1": "ABC",  // carrier id:ABC
		"storage2": "",     // empty
		"storage3": "",
		"storage4": "",
		"arm": ""				    // arm carrier id
	},
  "arm_program_running":false //true:ur机械臂程序正在运行 false:ur机械臂程序停止运行
}
```

rms_status 为机器人一些列信息整合后给调度系统参考的状态数据,用来表示以下几个状态的区分

- avaliable: 表示当前机器人处于无任务并且可以接任务的状态
- busy_id: busy 后接 id 编号，表示机器人正处于执行某个任务(任务号为后接的 id 值)的过程中
- interrupted: 表示机器人处于任务被打断的状态

| status                        | motor   | job_id | rms_status     | detail                                                           |
| :---------------------------- | :------ | :----- | :------------- | :--------------------------------------------------------------- |
| Stopped                       |         |        | interrupted    | 服务器识别到该状态对之前任务进行处理,并对该 IGV 标记为不可用状态 |
| Idle                          |         |        | avaliable      | IGV 处于空闲状态,可以接任务                                      |
| charging                      |         | 空     | avaliable      | IGV 可以接新任务                                                 |
| FinishedRoute/Parked/charging |         | 非空   | finished_jobid | 当前 jobid 完成                                                  |
| FailedRoute                   |         | 非空   | failed_jobid   | 当前 jobid 失败                                                  |
| 非以上状态                    |         | 非空   | busy_id        | 正在执行当前 jobid 任务                                          |
| 非以上状态                    |         | 空     | unknown        |                                                                  |
|                               | Disable | 空     | interrupted    |                                                                  |
|                               | Disable | 非空   | busy_jobid     |                                                                  |
