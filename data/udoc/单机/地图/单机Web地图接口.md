---
title: 单机Web地图接口
description: 
published: true
date: 2025-07-02T11:05:25.711Z
tags: 公开
editor: markdown
dateCreated: 2025-06-12T07:39:02.826Z
---

# 单机Web地图接口

| 文件名称 | 单机Web地图接口             |
| -------- | -------------------- |
| 部门     | 软件算法部           |
| 版本     | 3.0                  |
| 密级     | 保密（部门内部公开） |

## 修改记录

| 版本号 | 修改日期   | 修改人      | 概述      | 详细说明              |
| ------ | ---------- | ----------- | --------- | --------------------- |
| 1.0    | 2025-06-12 | 朱静怡        | 单机Web地图相关接口说明 |  |

---

## 地图相关接口
### 1. 地图查询
- **接口描述**：查询返回机器人当前使用的规划地图文件数据（点拟合成线段后的数据）
- **接口地址**：http://{{url}}/ctrl/map_file
- **请求方式**：GET
- **请求数据类型**：application/json
- **响应数据类型**：application/json
- **响应示例**
```json
{
	"code":200,
	"data":{
		"Header" : "umcl-map",
        "MapRes" : 20,
        "MaxPose" : "43832 103133",
        "MinPose" : "-278809 -81824",
        "NumLines" : 0,
        "NumPoints" : 1643599,
        "Objs" : {
        	"Goal" : [{
				"name" : "TJ0035-1",
				"pose" : "-105689.00 74534.00 0.00"
			}],
        	"GoalWithHeading" : [{
				"name" : "QP228-up",
				"pose" : "-28515.00 -54250.00 90.00"
			}],
        	"PathPoint" : [{
				"costs" : [ 1, 1 ],
				"name" : "p4850",
				"pose" : "-13969.00 59936.00 0.00",
				"vertex" : "p4851 p2877"
			}],
        },
        "ObsLines" : [],
		"ObsPoints" : []
	}
}
```

### 2. 地图文件列表查询
- **接口描述**：查询返回当前机器人所有的地图文件列表，包括文件名、文件路径、更新时间、文件大小、是否为当前使用地图
- **接口地址**：http://{{url}}/map/list
- **请求方式**：GET
- **请求数据类型**：application/json
- **响应数据类型**：application/json
- **响应示例**
```json
{
	"code":200,
	"data":{
		"map_list":[{
			"file_name": "map.json",	//文件名
			"file_dir": "/user/local/urobot/map",	//文件所在目录
			"update_time": "2024-08-10 13:22:53",	//文件最新修改时间
            "file_size": "32110",	//文件大小，单位KB
            "is_used": true		//是否为当前使用地图
		}]
	}
}
```

### 3. 地图上传
- **接口描述**：上传本地地图文件至机器人
- **接口地址**：http://{{url}}/map/upload
- **请求方式**：POST
- **请求数据类型**：multipart/form-data
- **请求示例**
```
Content-Type: multipart/form-data; boundary=WebAppBoundary
Authorization: xxxxx

--WebAppBoundary
Content-Disposition: form-data; name="file"; filename="junion7p-1.json"
Content-Type: application/json

#文件地址(与.http文件同目录同级或者后续二进制流)
< junion7p-1.json

--WebAppBoundary--
```
- **响应数据类型**：application/json

### 4. 地图应用
- **接口描述**：切换当前机器人所用地图至所选文件
- **接口地址**：http://{{url}}/map/apply
- **请求方式**：POST
- **请求数据类型**：multipart/form-data
- **请求示例**
```json
{
    "name":"junion7p.json"	//需使用的地图文件名
}
```
- **响应数据类型**：application/json

### 5. 地图下载
- **接口描述**：根据地图文件名返回文件流，下载所选地图文件至本地
- **接口地址**：http://{{url}}/map/download/{{filename.json}}
- **请求方式**：GET

### 6. 地图删除
- **接口描述**：切换当前机器人所用地图至所选文件
- **接口地址**：http://{{url}}/map/delete/{{filename.json}}
- **请求方式**：DELETE
