---
title: 0405_对外交互_pathFindingAPI
description: 
published: true
date: 2025-07-02T11:10:12.929Z
tags: 公开, path
editor: markdown
dateCreated: 2025-07-02T08:27:36.157Z
---

# RmsPath Path Finding API

| 文件名称 | RmsPath Path Finding API |
| ---- | ------------------------ |
| 部门   | 软件算法部                    |
| 版本   | 2.0                      |
| 密级   | 公开                       |

## 修改记录

| 版本号 | 修改日期       | 修改人 | 概述     | 详细说明             |
| --- | ---------- | --- | ------ | ---------------- |
| 1.0 | 2025-03-24 | 林祥序 | 新增文档   |                  |
| 2.0 | 2025-07-02 | 林祥序 | 归档线上仓库 | 格式整理，补充规范 header |


---

## 一、概述

本文件介绍了 Pathfinding API 的使用方法，该接口用于获取指定机器人的路径信息。通过传入参数，系统返回对应的路径数据，可用于路径规划或验证地图连通性。文档提供了 API 地址、请求参数说明、调用示例以及响应格式，帮助开发者快速集成与调试该接口功能。

## 二、API 地址

- URL: /pathfinding
- Method: GET

## 三、请求参数

| 参数名               | 类型     | 是否必填 | 说明                  |
| ----------------- | ------ | ---- | ------------------- |
| start             | String | 是    | 起点节点                |
| end               | String | 是    | 终点目标点               |
| robot             | String | 否    | 机器人名称               |
| DisableConstraint | String | 否    | 是否要考虑屏蔽节点，默认值：false |

## 四、请求示例

获取机器人的完整路径

```
GET /pathfinding?start=p438&end=A-RF04_put&robot=uBot-907
```

## 五、响应格式

- Content-Type: application/json

### 5.1 示例：成功响应

```json
{    
	"status": "success",
	"paths": [
	
	]
}
```

### 5.2 示例：错误响应


1. 无效的机器人名称

	- HTTP 状态码: 400 Bad Request
	- 响应体：

```json
{
	"status": "error",
	"message": "Invalid name: <robotName>"
}
```

2. 服务器内部错误
	- HTTP 状态码: 500 Internal Server Error
	- 响应体：

```json
{
	"status": "error",
	"message": "An error occurred: 错误信息"
}
```