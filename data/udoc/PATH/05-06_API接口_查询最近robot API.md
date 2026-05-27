---
title: 0506_API接口_查询最近robot API
description:
published: true
date: 2026-03-24T10:00:00+08:00
tags: 公开, path
editor: markdown
dateCreated: 2025-08-07T10:00:00+08:00
---

# 查询最近robot API

| 文件名称 | 查询最近robot API |
| ---- | ---- |
| 部门 | 软件算法部 |
| 版本 | 2.0 |
| 密级 | 公开 |

## 修改记录

| 版本号 | 修改日期 | 修改人 | 概述 | 详细说明 |
| --- | --- | --- | --- | --- |
| 1.0 | 2025-08-07 | 何进 | 新增文档 |  |
| 2.0 | 2026-03-24 | 林祥序 | 归档线上仓库 | 格式整理，归档接口说明 |

---

## 一、概述

本文档介绍查询最近 robot API 的用途与调用方式。该接口用于在给定候选 robot 列表中，按指定目标点或路径点计算并返回最近的 robot，便于外部系统在任务分配、调度决策和状态展示场景中快速选择合适车辆。文档包含接口地址、请求方式、参数定义、请求示例与返回示例，便于直接集成调用。

## 二、接口说明

- 接口名称：查询最近robot
- 请求方式：`POST`
- Content-Type：`application/json`
- 地址：`http://ip address:9000/findNearestRobot`

## 三、输入参数

| 参数名 | 类型 | 是否必须 | 参数说明 |
| --- | --- | --- | --- |
| idType | string | Y | 枚举值：`point`（按路径点查）、`goal`（按目标点查） |
| id | string | Y | 路径点/目标点名称 |
| robots | array | Y | 待选的robot列表 |

## 四、示例请求

按目标点：

```json
{
  "idType": "goal",
  "id": "PHCZZ01",
  "robots": ["ubot-001", "ubot-002", "ubot-003"]
}
```

按路径点：

```json
{
  "idType": "point",
  "id": "p5007",
  "robots": ["ubot-001", "ubot-002", "ubot-003"]
}
```

## 五、输出参数

| 参数名 | 类型 | 是否必须 | 参数说明 |
| --- | --- | --- | --- |
| result | bool | Y | 是否成功 |
| msg | string | N | 错误说明 |
| robot | string | Y | 最近的robot名称 |

## 六、示例返回

```json
{
  "result": true,
  "msg": null,
  "robot": "ubot-001"
}
```
