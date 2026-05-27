---
title: 3机器人任务调度协议(TCP)
description: 
published: true
date: 2025-12-17T11:42:58.099Z
tags: 协议, 单机, 调度
editor: markdown
dateCreated: 2025-06-23T05:50:44.637Z
---

# 机器人任务调度协议(TCP)（未完成，待重新整理）

| 文件名称 | 机器人任务调度协议(TCP) |
| -------- | ----------------------- |
| 部门     | 软件算法部              |
| 版本     | 2.0                     |
| 密级     | 保密(部门内公开)                    |

## 修改记录

| 版本号 | 修改日期   | 修改人 | 概述               | 详细说明                                             |
| ------ | ---------- | ------ | ------------------ | ---------------------------------------------------- |
| 1.0    | 2025-03-10 | 周嘉星 | RmsTask 模块说明   | 描述数据包格式，发送/取消任务等指令，以及 UDP 状态包 |
| 2.0    | 2025-06-21 | Gary   | 机器人任务调度协议 | 描述现有协议以及后续增加协议                         |

---

## 一、概述

该协议主要描述调度系统给机器人发送任务的协议，通信通过 TCP 进行，用 Socket 连上机器人后，通过指令+数据的包格式与机器人进行通信。

## 二、数据包格式

整个数据包分为包头、长度、分隔符、数据、包尾五个部分。如下所示：

|      |        |       |      |      |
| ---- | ------ | ----- | ---- | ---- |
| $#   | LEN    | ##    | DATA | $~   |
| head | length | split | {…}  | tail |

1. 包头为 2 个字节，值为 ASCII 码 ‘$#’，即十六进制 0x24 和 0x23。
2. 长度数据不限字节数，值为分隔符 ‘##’ 和尾部 ‘$~’ 之间的数据长度，值以字符串的形式来表示，如：如果 data 的长度为 5，那么长度的数据为 ASCII 码‘5’，即十六进制 35H，如果长度为 12，那么长度的数据为字符串 “12”，即十六进制 3132H。
数据为 json 格式字符串，数据中有 1 个必须要有的值：
	- `action`：指令，表示当前数据包是要机器人做什么，如 `send_map` 指令、`motor` 命令等。
其他json中的数据为指令的一些附带参数。

3. 分隔符为 2 个字节，值为 ASCII 码 ‘##’，用于判断长度字符串的结束以及数据的开始。
4. 包尾为 2 个字节，值为 ASCII 码 ‘$~’。

## 三、连接过程

![流程示例](<./3机器人任务调度协议(TCP)/机器人任务调度协议-仅图示.png>)

1️⃣ 发送任务数据包:`$#64##{"action":"send_map","mapname":"test.json"}$~`
2️⃣ 机器人返回任务接收情况: TODO `$#108##{"#CMD#":"UmConnect","commands":[],"msg":"Connect Succeed: login as test, group contains: all","state":true}$~`

如上所示，在 Socket 连接成功之后根据后续章节描述的“指令+数据”的方式发送数据包给机器人，机器人会返回相应的处理结果。

## 四、指令

发送给机器人的指令由`action`指定，目前支持的指令有:`send_map`,`motor`,`send_job`,`query_sensor`,`job`,`cancel_job`,`cancel_job2`,`change_monitor`。
TODO: 把这些名称都规整一下，应该是有重复的

### 1. 发送任务(send_job)

`action`为`send_job`时表示向机器人发送任务，发送支持四种形式，使用`job_type`字段区分，IGV 目前能识别 3 种任务类型:

- route_content: 直接下发任务完整内容，机器人端不需要预先准备好 route，这种方式下发的数据量较大，机器人端的任务完全由调度系统控制，可以任意配置和组合
- route_name: 仅下发任务的名称，机器人必须已经准备好完整的 route，这种方式下发的数据量比较小，但是任务流程是已经确定好的，适合大规模任务流程固定的情况
- template_name: 下发任务的模版名称，另外附带一些任务模版需要的参数，机器人端必须准备好 route 模版，下发的参数必须能完整包含模版所需的参数，这种方式是前两种方式的组合。
    < - device_dock: 对接口充电任务 -- 该方式隐藏，为公司内部专用方式>

#### 1.1. route_content

该任务包含任务的所有子 route，IGV 按照如下数据包内容进行执行和跳转，示例如下:

```json
{

       "ID": "",
       "action": "send_job",       // 必填项:action关键字
       "job_id": 3063546,          // 必填项:任务id
       "job_type": "route_content",// 必填项:任务类型
       "path": "empty",
       "readID": true,
       "ID/qrCode":"qrcode"        // 选填:二维码id
       "checkQr":false,            // 选填:是否上报二维码
       "readId":false,             // 选填, 与checkQr字段搭配使用
                                   // 1. checkQr: false, 不读取且不上报二维码
                                   // 2. checkQr:true + readId:true,读取且上报二维码
                                   // 3. checkQr:true + readId:false,读取二维码id但不校验不上报id
       "route_content": {          // 必填项: routes内容
            "a": {                 // key需要以"a"开始, 成功执行"a1", 识别执行"a0"
                     "note": 1,
                     "routes": "set_empty_params",
                     "back": true,
                     "cmd": "jump",
                     "key": "a"
              }
              "a1": {
                     "note": 1,
                     "goal": "Park0015",
                     "max_vel": 1500,
                     "cmd": "rms_goto",
                     "target": "goal"
              },
              "a11": {
                     "cmd": "set",
                     "status": "Parked"
              }
       }

}
```

如果 IGV 可以执行当前任务则向发送方进行如下应答:

```json
{"result":"success"}
```

如果 IGV 不可以执行当前任务则向发送方进行如下应答: TODO:差 message，失败原因

```json
{"result":"fail"}
```

#### 1.2. route_name

该任务只包含任务的名称, IGV 需要从本地 routes 配置文件种查找对应的 routes 内容,示例如下:

```json
{

       "ID": "",
       "action": "send_job",             // 必填项:action关键字
       "job_id": 3063283,                // 必填项: 任务id
       "job_type": "route_name",         // 必填项: 任务类型
       "path": "empty",                  // 可选项
       "ID/qrCode":"qrcode",             // 参考route_content字段内容
       "readID": false,                  // 参考route_content字段内容
       "route_name": "Q009-up-N"         // 必填项: routes名称
}
```

如果 IGV 可以执行当前任务则向发送方进行如下应答:

```json
{"result":"success"}
```

如果 IGV 不可以执行当前任务则向发送方进行如下应答: TODO:差 message

```json
{"result":"fail"}
```

#### 1.3. template_name

IGV 支持服务器发送模板任务, 如果服务器中有对应 routes 的参数则使用服务器参数, 否则使用 IGV 本地配置的默认参数, 以适配多种工作环境,格式如下:

```json
{
		"action":"send_job",           // 必填项
		"job_type":"template_name",    // 必填项
		"route_name":"Q009-up-N",      // 必填项, IGV根据该内容在本地配置文件中进行匹配查找
		"job_id":3063284
		...
		"$Target": "A"  // 替换的模版参数
}
```

如果 IGV 可以执行当前任务则向发送方进行如下应答:

```json
{"result":"success"}
```

如果 IGV 不可以执行当前任务则向发送方进行如下应答:TODO:差 message

```json
{"result":"failed"}
```

#### 1.4. 拒接任务

以下几种情况 IGV 是不接任务的

- IGV 在不接任务区
- IGV 处于 EStop 状态
- IGV 当前未启动完成
  IGV 拒接任务时会向服务器发送"{“result”:"fail"}"进行应答

### 2. 任务取消(cancel_job)

IGV 支持任务取消功能, 但如果该任务进入对接状态或则正在执行任务的 mode 中 note 值为负数的话，则是不允许取消的。示例如下:

```json
{
	"action": "cancel_job"       // 比填项:取消IGV正在执行的任务
	"job_id":3063284             // 必填项
}
```

如果 IGV 可以执行当前任务则向发送方进行如下应答:

```json
{"result":"success"}
```

任务取消成功后,IGV 进入 idle 状态以随时接收新的任务

如果 IGV 不可以执行当前任务则向发送方进行如下应答，TODO：拒绝取消需要在`message`中附带信息

```json
{"result":"failed"}
```

任务取消失败有以下 2 种情况:

- 服务器取消的任务 id 与 IGV 正在执行的 id 不一致
- 当前任务未设置 note 字段
- 当前任务的 note 值小于 0 或则 note 值大于 10

### 3. 发送动作

#### 3.1. pause_robot

该动作类型用于暂停机器人移动

```json
{
	"action":"pause_robot",          // 必填项
	"job_type":"act",     // 必填项
}
```

如果 IGV 可以执行当前动作则向发送方进行如下应答:

```json
{"result":"success"}
```

如果 IGV 不可以执行当前动作则向发送方进行如下应答:

```json
{"result":"failed"}
```

#### 3.2. resume_robot

该动作类型用于恢复机器人移动

```json
{
	"action":"resume_robot",          // 必填项
	"job_type":"act",     // 必填项
}
```

如果 IGV 可以执行当前动作则向发送方进行如下应答:

```json
{"result":"success"}
```

如果 IGV 不可以执行当前动作则向发送方进行如下应答:

```json
{"result":"failed"}
```

#### 3.3 拒绝动作

以下几种情况 IGV 会拒绝响应动作

- IGV 在不接任务区
- IGV 处于 EStop 状态
- IGV 当前未启动完成
  IGV 拒接动作时会向服务器发送"{“result”:"fail"}"进行应答
