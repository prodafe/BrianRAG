---
title: 0408_对外交互_申请锁点API
description: 
published: true
date: 2025-07-02T11:08:40.790Z
tags: 公开, path
editor: markdown
dateCreated: 2025-07-02T08:22:29.167Z
---

# 申请锁点 API

| 文件名称 | 申请锁点 API |
| ---- | -------- |
| 部门   | 软件算法部    |
| 版本   | 2.0      |
| 密级   | 公开       |

## 修改记录

| 版本号 | 修改日期       | 修改人 | 概述     | 详细说明             |
| --- | ---------- | --- | ------ | ---------------- |
| 1.0 | 2024-10-11 | 林祥序 | 新增文档   |                  |
| 2.0 | 2025-07-02 | 林祥序 | 归档线上仓库 | 格式整理，补充规范 header |


---

## 一、概述

本文件介绍了申请锁点 API 的使用方法，旨在为外部系统提供锁定路径节点的接口能力。文档包含申请与释放锁点的接口地址、请求与响应参数说明、调用示例，以及程序运行所需的相关配置项。该接口可用于实现路径控制、区域占用管理等功能，确保机器人调度过程中的安全性与协调性。

## 二、申请锁点

### 2.1 接口地址

`POST` [http://localhost:9000/request](http://localhost:9000/request)  

Content-Type: `application/json`

### 2.2 请求参数（JSON Body）

|字段名|类型| 含义        | 说明                    |
|---|---|-----------|-----------------------|
|name|string| 机器人名称     | 外部系统识别的机器人 ID       |
|action|string| 请求类型      | 固定为 `"request_point"` |
|id|long| 请求编号      | 每次请求需唯一标识             |
|points|string[]| 请求锁定的点位列表 | 一次可申请多个点              |
示例：
```json
{
  "name": "exbot-001",
  "action": "request_point",
  "id": 1234567890,
  "points": ["p1", "p2", "p3"]
}
```

### 2.3 响应参数（JSON Body）

| 字段名    | 类型      | 含义      | 说明                       |
| ------ | ------- | ------- | ------------------------ |
| result | boolean | 是否锁定成功  | `true` 表示成功，`false` 表示失败 |
| msg    | string  | 错误或提示信息 | 详情说明                     |
| action | string  | 请求类型    | 与请求中保持一致                 |
| id     | long    | 请求编号    | 与请求中保持一致                 |
##### 响应示例
申请失败：当前节点被占用
```json
{
  "result": false,
  "msg": "Reject pointRequest 1234567890 from exbot-001 point p1 occupied by ubot-002",
  "action": "request_point",
  "id": 1234567890
}
```

申请失败：当前请求无法解析（字段缺失或错误）
```json
{
    "result": false,
    "msg": "parse http request failed"
}
```

申请成功
```json
{
    "result": true,
    "msg": "Accept request_point [p1, p2, p3], id: 1234567890 from exbot-001",
    "action": "request_point",
    "id": 1234567890
}
```

## 三、释放锁点

### 3.1 接口地址

`POST` [http://localhost:9000/request](http://localhost:9000/request)  

Content-Type: `application/json`

注：申请和释放锁点共用同一个接口地址 `/request`，通过 `action` 字段区分行为。

### 3.2 请求参数（JSON Body）

| 字段名    | 类型       | 含义    | 说明                    |
| ------ | -------- |-------|-----------------------|
| name   | string   | 机器人名称 | 外部系统识别的机器人 ID         |
| action | string   | 请求类型  | 固定为 `"release_point"` |
| id     | long     | 请求编号  | 每次请求需唯一标识             |

示例：
```json
{
  "name": "exbot-001",
  "action": "release_point",
  "id": 1234567890
}
```

注：机器人辆名称和请求编号要和 `request_point` 请求时匹配，才能释放对应的锁点。

### 3.3 响应参数（JSON Body）

| 字段名    | 类型      | 含义       | 说明       |
| ------ | ------- | -------- | -------- |
| result | boolean | 是否收到释放请求 | 恒为`true` |
| msg    | string  | 错误或提示信息  | 详情说明     |
| action | string  | 请求类型     | 与请求中保持一致 |
| id     | long    | 请求编号     | 与请求中保持一致 |
示例：
```json
{
    "result": true,
    "msg": "exbot-001 release point [p1, p2, p3] (id: 1234567890)",
    "action": "release_point",
    "id": 1234567890
}
```

## 四、程序配置

1. 参考【机器人请求】开启锁点功能
2. 配置公共区路径节点 `commonZonePoints`，外部系统只能申请锁定公共区域内的路径节点。

| 参数名称                     | 单位   | 参数说明                     |
| ------------------------ | ---- | ------------------------ |
| ***common_zone_points*** | 节点名称 | 公共区域节点名称集合，例子：“p1,p2,p3" |
