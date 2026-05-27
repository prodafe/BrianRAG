---
title: 0406_对外交互_xManager配置
description: 
published: true
date: 2025-07-02T11:09:55.644Z
tags: 公开, path
editor: markdown
dateCreated: 2025-06-11T08:00:23.970Z
---

# xManager 相关配置

| 文件名称 | xManager 相关配置 |
| ---- | ------------- |
| 部门   | 软件算法部         |
| 版本   | 2.0           |
| 密级   | 公开            |

## 修改记录

| 版本号 | 修改日期       | 修改人 | 概述       | 详细说明             |
| --- | ---------- | --- | -------- | ---------------- |
| 1.0 | 2024-05-26 | 林祥序 | 新增文档     |                  |
| 2.0 | 2025-07-02 | 林祥序 | 归档线上仓库   | 格式整理，补充规范 header |
| 2.1 | 2025-07-21 | 林祥序 | 新增低速区    |                  |
| 2.2 | 2025-12-24 | 林祥序 | 新增提前下发区  |                  |
| 2.3 | 2025-03-31 | 林祥序 | 新增安装问题收录 |                  |


---

## 一、概述

本文件介绍了 xManager 的配置方法与使用说明，内容包括程序安装包的部署、自定义区域的配置流程，以及区域参数的定义。通过本指南，用户可完成 xManager 的基础安装与区域功能的个性化设定，为后续地图设计与功能配置提供支持。

## 二、程序安装

- 下载安装 [`xManager`](https://drive.weixin.qq.com/s?k=AJMABQdxAA8MNvvYBvAUUAnwYqAKM)（以最新版本为准）
- 负责人：白鹏
### 安装问题收录

1. 目录路径不要有中文字
2. 如果点击没反应，尝试安装包里的 `vc_redist.x64`
3. 如果提示没有授权，提供 `cpu_id` 给研发进行软件授权

## 三、区域配置

1. 打开配置文件 `./xManager_<version>/cache/settings/settings_map.json`
2. 找到 `map_regions`，为软件中显示的各个区域，可自定义添加（各个新增区域的参数查看下文）。

3. 添加过程中注意文件格式

4. 添加完成后，对 `settings_map.json` 文件进行保存，重启 `xManager` 应用新的配置

5. 区域中出现新的配置即设定成功

### 3.1 旋转限制区

>适配版本：v7.02

```json
{    
	"chn": "旋转角度限制区",
	"color": "#9d6910",
	"id": "RotationLimitArea",
	"ext": [
		{
			"name": "rotationLimit",
			"type": "double"
		}    
	]
}
```

### 3.2 新版单机区

>适配版本：v7.01.4

```json
{
	"chn": "单机区",
	"color": "#7AC5CD",
	"id": "SingleZone",
	"ext": [
		{
			"name": "bufferType",
			"type": "string"
		},
		{
			"name": "allocationTiming",
			"type": "string"
		}
	]
}
```

### 3.3 低速区

```json
{
	"chn": "低速区",
	"color": "#9eb34d",
	"id": "LowSpeedArea",
	"ext": [
		{
			"name": "length",
			"type": "int"
		}
	]
}
```

### 3.4 提前下发区

```json
{
	"chn": "提前下发区",
	"color": "#ee6590",
	"id": "EarlyAllocationArea"
}
```