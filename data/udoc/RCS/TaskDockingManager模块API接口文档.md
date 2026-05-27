# TaskDockingManager API 接口文档

| 文件名称 | TaskDockingManager API 接口文档                   |
| -------- | ---------------------------- |
| 部门     | 软件算法部                   |
| 版本     | 1.0                          |
| 密级     | 限制（部门内公开） |

## 变更记录

| 版本号 | 修改日期 | 修改人 | 概述 | 详细说明 |
| ------ | -------- | ------ | ---- | -------- |
|   1.0     |    2026-04-09      |    杨鑫磊    |   API接口整理   |          |
|        |          |        |      |          |
|        |          |        |      |          |
|        |          |        |      |          |



> 以下接口默认前缀: `/api/[Controller]`

---

## 一、RmsJobController - RMS任务汇报

### 1. ReportFromRms - 叉车执行任务汇报接口

- **接口地址**: `/api/RmsJob/ReportFromRms`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 接收RMS(机器人管理系统)上报的任务执行结果，处理机器人任务汇报信息

**请求示例:**
```json
{
  "robot": "ROBOT001",
  "timing": "before",
  "extra": {
    "target": "PORT001",
    "actions": [
      {
        "command": "CommonArrived",
        "request": {}
      }
    ]
  }
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| robot | string | 是 | 机器人ID |
| timing | string | 是 | 汇报时机(before=执行前, after=执行后) |
| extra | object | 是 | 扩展信息 |
| extra.target | string | 是 | 目标点ID |
| extra.actions | array | 是 | 动作列表 |
| actions[].command | string | 是 | 命令类型(CommonArrived, CommonFinished等) |
| actions[].request | object | 是 | 请求参数 |

**响应示例:**
```json
{
  "result": true
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| result | bool | 任务执行结果(true=成功, false=失败) |

---

## 二、RobotController - 机器人管理

继承自 `ApiBaseController<RobotCore, RobotCoreDto, IBaseRepository<RobotCore>, string>`

### 1. Add (继承) - 新增机器人

- **接口地址**: `/api/Robot/Add`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 新增机器人基础信息

**请求示例:**
```json
{
  "id": "ROBOT001",
  "name": "机器人1",
  "ip": "192.168.1.100",
  "categories": "Fork",
  "enable": true,
  "region": "A区"
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 机器人ID |
| name | string | 否 | 机器人名称 |
| ip | string | 否 | IP地址 |
| categories | string | 否 | 机器人类别(Fork=叉车, Normal=普通AGV) |
| enable | bool | 否 | 是否启用 |
| region | string | 否 | 所属区域 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "id": "ROBOT001",
    "name": "机器人1",
    "ip": "192.168.1.100"
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 新增的机器人对象 |

---

### 2. Update (继承) - 更新机器人

- **接口地址**: `/api/Robot/Update/{id}`
- **请求方式**: PUT
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新机器人信息

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 机器人ID(路径参数) |
| RobotCoreDto | object | 是 | 机器人数据 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 3. AllEnableOrDisable - 全部启用/禁用

- **接口地址**: `/api/Robot/AllEnableOrDisable`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 启用或禁用所有机器人

**请求示例:**
```json
true
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| status | bool | 是 | true=启用, false=禁用 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "操作成功",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 4. CheckIpIsOnly - 确认IP是否唯一

- **接口地址**: `/api/Robot/CheckIpIsOnly/{ip}`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 验证机器人IP是否唯一

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| ip | string | 是 | IP地址(路径参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": 0
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | int | 记录数量(0=不存在,可新增) |

---

### 5. Import - 导入机器人信息

- **接口地址**: `/api/Robot/Import`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量导入或更新机器人信息

**请求示例:**
```json
[
  {
    "id": "ROBOT001",
    "name": "机器人1",
    "ip": "192.168.1.100"
  }
]
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| 数组 | RobotCoreDto[] | 是 | 机器人数据数组 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "导入成功",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 6. BindingUpdate - 更新资源点绑定信息

- **接口地址**: `/api/Robot/BindingUpdate`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新机器人绑定的资源点信息

**请求示例:**
```json
{
  "robotId": "ROBOT001",
  "portIds": ["PORT001", "PORT002", "PORT003"]
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| robotId | string | 是 | 机器人ID |
| portIds | string[] | 是 | 绑定的资源点ID数组 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "更新成功",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 7. BindingImport - 批量导入资源点绑定信息

- **接口地址**: `/api/Robot/BindingImport`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量导入机器人资源点绑定信息

**请求示例:**
```json
[
  {
    "robotId": "ROBOT001",
    "portIds": ["PORT001", "PORT002"]
  },
  {
    "robotId": "ROBOT002",
    "portIds": ["PORT003"]
  }
]
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| 数组 | AssetsBindingInfo[] | 是 | 绑定信息数组 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "导入成功",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 8. BindingDeleteByIds - 批量删除绑定

- **接口地址**: `/api/Robot/BindingDeleteByIds`
- **请求方式**: DELETE
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量删除机器人的资源点绑定

**请求示例:**
```json
["ROBOT001", "ROBOT002"]
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| ids | string[] | 是 | 机器人ID数组 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": ["ROBOT001", "ROBOT002"]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 删除的ID列表 |

---

### 9. BindingDelete - 删除单个绑定

- **接口地址**: `/api/Robot/BindingDelete/{ids}`
- **请求方式**: DELETE
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 删除单个机器人的资源点绑定

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| ids | string | 是 | 机器人ID(路径参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": "ROBOT001"
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | string | 删除的ID |

---

### 10. QueryBindingDataByPage - 分页查询资源点绑定信息

- **接口地址**: `/api/Robot/QueryBindingDataByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询机器人资源点绑定信息

**请求示例:**
```json
{
  "page": 1,
  "pageSize": 20,
  "query": {
    "robotId": ["ROBOT001"],
    "portIds": ["PORT001"]
  }
}
```

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| robotId | array | ["ROBOT001"] | 机器人ID列表(精确匹配) |
| portIds | array | ["PORT001"] | 资源点ID列表(模糊匹配) |

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| page | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| query | object | 否 | 查询条件 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "page": 1,
    "pageSize": 20,
    "total": 10,
    "dataList": [
      {
        "robotId": "ROBOT001",
        "portIds": ["PORT001", "PORT002"]
      }
    ]
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 分页数据 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页数量 |
| data.total | int | 总记录数 |
| data.dataList | array | 数据列表 |
| dataList[].robotId | string | 机器人ID |
| dataList[].portIds | string[] | 绑定的资源点ID数组 |

---

### 11. GetRobotRealInfos - 获取机器人实时信息

- **接口地址**: `/api/Robot/GetRobotRealInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取机器人实时状态信息(从Redis缓存)

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    {
      "id": "ROBOT001",
      "name": "机器人1",
      "ip": "192.168.1.100",
      "status": 1,
      "battery": 85,
      "currentCommand": "goto",
      "currentKey": "a",
      "completeStatus": 1,
      "errorTip": ""
    }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 机器人实时信息列表 |
| data[].id | string | 机器人ID |
| data[].name | string | 机器人名称 |
| data[].ip | string | IP地址 |
| data[].status | int | 状态 |
| data[].battery | int | 电量 |
| data[].currentCommand | string | 当前执行的命令 |
| data[].currentKey | string | 当前步骤Key |
| data[].completeStatus | int | 完成状态 |
| data[].errorTip | string | 错误信息 |

---

### 12. GetRobotInfos - 获取机器人编号信息

- **接口地址**: `/api/Robot/GetRobotInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有机器人的ID和名称列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "id": "ROBOT001", "name": "机器人1" },
    { "id": "ROBOT002", "name": "机器人2" }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 机器人列表(id, name) |

---

### 13. GetRobotBatterySocInfo - 获取机器人电池标定信息

- **接口地址**: `/api/Robot/GetRobotBatterySocInfo?ip={ip}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 根据IP获取机器人电池标定信息

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| ip | string | 是 | 机器人IP地址(查询参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "id": 1,
    "robotName": "机器人1",
    "ip": "192.168.1.100",
    "startBattery": 100,
    "startChargingTime": "2024-01-01T10:00:00",
    "endBattery": 90,
    "startTime": "2024-01-01T10:00:00",
    "endTime": "2024-01-01T11:00:00"
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 电池标定信息 |
| data.id | int | ID |
| data.robotName | string | 机器人名称 |
| data.ip | string | IP地址 |
| data.startBattery | int | 开始电量 |
| data.startChargingTime | DateTime | 开始充电时间 |
| data.endBattery | int | 结束电量 |
| data.startTime | DateTime | 开始时间 |
| data.endTime | DateTime | 结束时间 |

---

### 14. GetRobotTypes - 获取机器人型号

- **接口地址**: `/api/Robot/GetRobotTypes`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有机器人型号枚举列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "key": "Normal", "value": 0 },
    { "key": "Fork", "value": 1 }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 机器人型号枚举数组 |

---

### 15. ResetRobot - 复位机器人

- **接口地址**: `/api/Robot/ResetRobot`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 复位机器人(停止当前任务并重置机器人状态)

**请求示例:**
```json
{
  "id": "ROBOT001",
  "isKeep": false
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 机器人ID |
| isKeep | bool | 否 | 是否保持当前任务 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 16. ExcuteNext - 执行下一步

- **接口地址**: `/api/Robot/ExcuteNext/{id}`
- **请求方式**: POST
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 手动执行任务的下一步骤

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 机器人ID(路径参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 17. UpdateContentAsync - 更新机器人内容

- **接口地址**: `/api/Robot/UpdateContentAsync/{id}`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新机器人的载荷内容

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 机器人ID(路径参数) |
| playload | object | 是 | 载荷内容字典 |

**请求示例:**
```json
{
  "key1": "value1",
  "key2": "value2"
}
```

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 18. UploadMapFile - 上传地图文件

- **接口地址**: `/api/Robot/UploadMapFile`
- **请求方式**: POST
- **请求数据类型**: multipart/form-data
- **响应数据类型**: application/json
- **接口描述**: 上传地图文件到服务器

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| file | file | 是 | 地图文件(.json/.smap) |

**响应示例:**
```json
{
  "fileName": "map.json",
  "fileSize": 1024,
  "filePath": "/Uploads/map.json"
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| fileName | string | 文件名 |
| fileSize | long | 文件大小 |
| filePath | string | 可访问路径 |

---

### 19. UploadMapToRobot - 上传地图到机器人

- **接口地址**: `/api/Robot/UploadMapToRobot`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 将地图文件上传到指定机器人

**请求示例:**
```json
{
  "mapFile": "map.json",
  "robots": ["ROBOT001", "ROBOT002"]
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| mapFile | string | 是 | 地图文件名 |
| robots | string[] | 是 | 机器人ID数组 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": "ROBOT001 Update IsSuccess\nROBOT002 Update IsSuccess"
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | string | 上传结果详情 |

---

### 20. PushMapToRobot - 上传地图到机器人并切换

- **接口地址**: `/api/Robot/PushMapToRobot`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 将地图上传到机器人并切换地图

**请求示例:**
```json
{
  "mapFile": "map.json",
  "robots": ["ROBOT001"]
}
```

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": "ROBOT001 Push Map IsSuccess"
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | string | 上传结果详情 |

---

### 21. HandleTargetEstop - 处理急停信息

- **接口地址**: `/api/Robot/HandleTargetEstop?targetid={targetid}`
- **请求方式**: POST
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 处理目标点的急停信号

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| targetid | string | 是 | 目标点ID(查询参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 22. GetAll (继承) - 获取所有机器人

- **接口地址**: `/api/Robot/GetAll`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有机器人信息列表

**响应参数:** 同 Add 接口响应

---

### 23. Delete (继承) - 删除机器人

- **接口地址**: `/api/Robot/Delete/{id}`
- **请求方式**: DELETE
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 删除指定机器人

**响应参数:** 同 Add 接口响应

---

## 三、JobController - 任务管理

继承自 `ApiBaseController<AgvTask, AgvTask, IBaseRepository<AgvTask>, string>`

### 1. Delete (继承) - 删除任务

- **接口地址**: `/api/Job/Delete/{id}`
- **请求方式**: DELETE
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 删除指定ID的AGV任务(仅限已完成的任务)

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 任务ID(路径参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 2. DeleteByIds (继承) - 批量删除任务

- **接口地址**: `/api/Job/DeleteByIds`
- **请求方式**: DELETE
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量删除多个AGV任务(仅限已完成的任务)

**请求示例:**
```json
["TASK001", "TASK002", "TASK003"]
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| ids | string[] | 是 | 任务ID数组 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": []
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 删除的任务列表 |

---

### 3. CloseJob - 关闭任务

- **接口地址**: `/api/Job/CloseJob?id={id}&isKeep={isKeep}&remark={remark}`
- **请求方式**: PUT
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 强制关闭指定任务(可选择是否保持机器人状态)

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 任务ID(查询参数) |
| isKeep | bool | 否 | 是否保持机器人状态 |
| remark | string | 否 | 备注 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 4. CancelJob - 取消任务

- **接口地址**: `/api/Job/CancelJob`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 外界主动调用取消任务

**请求示例:**
```json
{
  "id": "TASK001"
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 任务ID |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 5. CancelByTarget - 设备取消任务

- **接口地址**: `/api/Job/CancelByTarget`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 设备主动取消指定目标点的任务

**请求示例:**
```json
{
  "target": "PORT001"
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| target | string | 是 | 目标点ID |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 6. GetTaskStepInfos - 获取任务步骤信息

- **接口地址**: `/api/Job/GetTaskStepInfos?jobId={jobId}&robotId={robotId}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 获取任务的步骤详情信息

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| jobId | string | 是 | 任务ID |
| robotId | string | 否 | 机器人ID |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    {
      "jobId": "TASK001",
      "robotId": "ROBOT001",
      "currentKey": "a",
      "currentCommand": "goto",
      "completedStatus": 1,
      "beginTime": "2024-01-01T10:00:00"
    }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 任务步骤列表 |
| data[].jobId | string | 任务ID |
| data[].robotId | string | 机器人ID |
| data[].currentKey | string | 当前步骤Key |
| data[].currentCommand | string | 当前命令 |
| data[].completedStatus | int | 完成状态 |
| data[].beginTime | DateTime | 开始时间 |

---

### 7. QueryDataByPage (继承) - 分页查询任务

- **接口地址**: `/api/Job/QueryDataByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询任务列表

**响应参数:** 同Robot QueryBindingDataByPage

---

## 四、StorageController - 库位管理

继承自 `ApiBaseController<StorageInfo, StorageDto, IBaseRepository<StorageInfo>, string>`

### 1. AllEnableOrDisable - 全部启用/禁用

- **接口地址**: `/api/Storage/AllEnableOrDisable`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 启用或禁用所有库位

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| status | bool | 是 | true=启用, false=禁用 |

**响应参数:** 同 Robot AllEnableOrDisable

---

### 2. Import - 导入库位数据

- **接口地址**: `/api/Storage/Import`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量导入库位数据

**请求示例:**
```json
[
  {
    "id": "STORAGE001",
    "name": "库位1",
    "capacity": 10,
    "currentNumber": 5,
    "region": "A区"
  }
]
```

**响应参数:** 同 Robot Import

---

### 3. GetRmsConfig - 生成RMSPath配置文件

- **接口地址**: `/api/Storage/GetRmsConfig`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 生成RMS外部配置文件(包含对接口的URL和请求信息)

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "externalRequest": [
      {
        "url": "http://192.168.1.100:9099/api/Job/ReportFromRms",
        "requestEntityType": "AdvancedEdge",
        "requestEntity": "STATION1",
        "extra": {
          "actions": [{ "command": "CommonArrived" }],
          "target": "PORT001"
        },
        "timing": "before"
      }
    ]
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | RMS配置数据 |
| data.externalRequest | array | 外部请求配置列表 |

---

### 4. GetStorageInfos - 获取库位编号信息

- **接口地址**: `/api/Storage/GetStorageInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有库位的ID和名称列表

**响应参数:** 同 Robot GetRobotInfos

---

### 5. GetStorageTypes - 获取库位类型列表

- **接口地址**: `/api/Storage/GetStorageTypes`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取库位类型枚举列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "key": "Normal", "value": 0 },
    { "key": "Buffer", "value": 1 }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 库位类型枚举数组 |

---

### 6. GetGroupStorageInfos - 按区域分组获取库位信息

- **接口地址**: `/api/Storage/GetGroupStorageInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 按区域分组获取所有库位信息

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "A区": [
      { "id": "STORAGE001", "name": "库位1", "region": "A区" }
    ],
    "B区": [
      { "id": "STORAGE002", "name": "库位2", "region": "B区" }
    ]
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 按区域分组的库位列表 |

---

### 7. UpdateStorageInfo - 修改料车库位

- **接口地址**: `/api/Storage/UpdateStorageInfo`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 修改料车库位信息(生产内容)

**请求参数:** 同 StorageDto

**响应参数:** 同 StorageDto

---

### 8. GetNormalStorageInfos - 获取普通库位信息

- **接口地址**: `/api/Storage/GetNormalStorageInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有普通类型库位信息

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 普通库位列表 |

---

### 9. UpdateStorageInfoByPDA - PDA更新库位数量

- **接口地址**: `/api/Storage/UpdateStorageInfoByPDA?storageId={storageId}&currentNumber={currentNumber}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: PDA设备更新库位当前数量

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| storageId | string | 是 | 库位ID |
| currentNumber | int | 是 | 当前数量 |

**响应参数:** 同 StorageDto

---

### 10. UnlockStorage - 解锁库位

- **接口地址**: `/api/Storage/UnlockStorage?storageId={storageId}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 解锁指定库位

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| storageId | string | 是 | 库位ID |

**响应参数:** 同 StorageDto

---

### 11. UpdateActiveStorage - 更新有源库位

- **接口地址**: `/api/Storage/UpdateActiveStorage/{storageId}?count={count}`
- **请求方式**: PUT
- **请求数据类型**: URL参数+query
- **响应数据类型**: application/json
- **接口描述**: IoT设备更新有源库位数量

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| storageId | string | 是 | 库位ID(路径参数) |
| count | int | 是 | 数量(查询参数) |

**响应参数:** 同 StorageDto

---

### 12. GetGroupsStorageInfos - 库位概览获取库位数据

- **接口地址**: `/api/Storage/GetGroupsStorageInfos?query={query}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 库位概览界面获取分层级库位数据

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| enable | bool | true | 是否启用 |
| isLocked | bool | false | 是否锁定 |
| id | string | "STORAGE001" | 库位ID(模糊匹配) |
| materialNumber | string | "M001" | 物料号(模糊匹配) |
| materialInfo | string | "物料信息" | 物料信息(模糊匹配) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "A区": {
      "工艺1": [
        {
          "id": "STORAGE001",
          "name": "库位1",
          "currentNumber": 5,
          "capacity": 10,
          "robot": "ROBOT001"
        }
      ]
    }
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 按区域>工艺分层的库位数据 |

---

### 13. UpdateStorageByOverView - 库位概览更新库位

- **接口地址**: `/api/Storage/UpdateStorageByOverView/{id}/{enable}/{isLocked}/{currentNumber}`
- **请求方式**: PUT
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 库位概览界面更新库位状态和数量

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 库位ID(路径参数) |
| enable | bool | 是 | 是否启用(路径参数) |
| isLocked | bool | 是 | 是否锁定(路径参数) |
| currentNumber | int | 是 | 当前数量(路径参数) |

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | bool | 更新结果 |

---

### 14. ClearStoageByIds - 批量清库

- **接口地址**: `/api/Storage/ClearStoageByIds?storageIds={storageIds}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 批量清空指定库位(重置为初始状态)

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| storageIds | string | 是 | 库位ID列表(逗号分隔) |

**响应参数:** 同 Robot AllEnableOrDisable

---

### 15. GetRowsCount (继承) - 确认是否唯一键

- **接口地址**: `/api/Storage/GetRowsCount/{id}`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 验证库位ID是否存在于目标表

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 库位ID(路径参数) |

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | int | 记录数量 |

---

### 16. Add/Update/Delete/GetAll (继承) - CRUD操作

- **接口地址**: `/api/Storage/Add`, `/api/Storage/Update`, `/api/Storage/Delete/{id}`, `/api/Storage/GetAll`
- **请求方式**: POST/POST/DELETE/GET
- **响应数据类型**: application/json
- **接口描述**: 库位的增删改查操作

**响应参数:** 同 Robot Controller 继承接口

---

## 五、RegionManagerController - 区域管理

### 1. ModifyRegion - 更新区域信息

- **接口地址**: `/api/RegionManager/ModifyRegion`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新区域信息(跨区域更新转移口、库位、充电点、停车点的区域)

**请求示例:**
```json
{
  "region": "A区",
  "transferPorts": ["PORT001"],
  "storages": ["STORAGE001"],
  "chargeStations": ["CHARGE001"],
  "parks": ["PARK001"]
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| region | string | 是 | 区域名称 |
| transferPorts | string[] | 否 | 转移口ID列表 |
| storages | string[] | 否 | 库位ID列表 |
| chargeStations | string[] | 否 | 充电点ID列表 |
| parks | string[] | 否 | 停车点ID列表 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

---

### 2. QueryDataByPage - 查询区域信息

- **接口地址**: `/api/RegionManager/QueryDataByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询区域信息列表

**请求示例:**
```json
{
  "page": 1,
  "pageSize": 20,
  "query": {
    "region": "A区"
  }
}
```

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| region | string | "A区" | 区域名称(模糊匹配) |
| robots | array | ["ROBOT001"] | 机器人ID列表 |
| ids | array | ["PORT001"] | 目标点ID列表 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "page": 1,
    "pageSize": 20,
    "total": 5,
    "dataList": [
      {
        "region": "A区",
        "robots": ["ROBOT001"],
        "transferPorts": ["PORT001"],
        "storages": ["STORAGE001"],
        "chargeStations": ["CHARGE001"],
        "parks": ["PARK001"]
      }
    ]
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 分页数据 |
| data.dataList | array | 区域列表 |
| dataList[].region | string | 区域名称 |
| dataList[].robots | string[] | 机器人ID列表 |
| dataList[].transferPorts | string[] | 转移口ID列表 |
| dataList[].storages | string[] | 库位ID列表 |
| dataList[].chargeStations | string[] | 充电点ID列表 |
| dataList[].parks | string[] | 停车点ID列表 |

---

## 六、ContentManagerController - 包号管理

### 1. ModifyContent - 修改包号信息内容

- **接口地址**: `/api/ContentManager/ModifyContent`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量修改目标点的包号内容(生产内容/需求内容)

**请求示例:**
```json
{
  "content": {
    "packageId": "PKG001",
    "batch": "B001"
  },
  "needTransferPorts": ["PORT001"],
  "needStorages": ["STORAGE001"],
  "produceTransferPorts": ["PORT002"],
  "produceStorages": ["STORAGE002"]
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| content | object | 是 | 包号内容字典 |
| needTransferPorts | string[] | 否 | 需求转移口ID列表 |
| needStorages | string[] | 否 | 需求库位ID列表 |
| produceTransferPorts | string[] | 否 | 生产转移口ID列表 |
| produceStorages | string[] | 否 | 生产库位ID列表 |

**响应参数:** 同 ModifyRegion

---

### 2. QueryDataByPage - 查询包号信息分页数据

- **接口地址**: `/api/ContentManager/QueryDataByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询包号信息数据

**请求示例:**
```json
{
  "page": 1,
  "pageSize": 20,
  "query": {
    "content": "{\"packageId\":\"PKG001\"}",
    "ids": ["PORT001"]
  }
}
```

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| content | string | "{\"packageId\":\"PKG001\"}" | 包号内容(JSON字符串) |
| ids | array | ["PORT001"] | 目标点ID列表 |

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 分页数据 |
| data.dataList | array | 包号信息列表 |
| dataList[].content | object | 包号内容 |
| dataList[].needTransferPorts | string[] | 需求转移口 |
| dataList[].needStorages | string[] | 需求库位 |
| dataList[].produceTransferPorts | string[] | 生产转移口 |
| dataList[].produceStorages | string[] | 生产库位 |

---

## 七、MaterialController - 物料管理

继承自 `ApiBaseController<Material, MaterialDto, IBaseRepository<Material>, int>`

### 1. Add (继承) - 新增物料

- **接口地址**: `/api/Material/Add`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 新增物料信息

**请求示例:**
```json
{
  "materialNumber": "M001",
  "materialName": "物料1",
  "belongId": "STORAGE001",
  "index": 1
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| materialNumber | string | 是 | 物料号 |
| materialName | string | 否 | 物料名称 |
| belongId | string | 否 | 所属库位ID |
| index | int | 否 | 库位内序号 |

**响应参数:** 同 Robot Add

---

### 2. Update (继承) - 更新物料

- **接口地址**: `/api/Material/Update/{id}`
- **请求方式**: PUT
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新物料信息

**响应参数:** 同 Robot Update

---

### 3. Import - 导入物料数据

- **接口地址**: `/api/Material/Import`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量导入物料数据

**响应参数:** 同 Robot Import

---

### 4. MaterialTransfer - 物料流转更新

- **接口地址**: `/api/Material/MaterialTransfer?startStorageId={startStorageId}&endStorageId={endStorageId}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 物料流转(从起点库位移动到终点库位)

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| startStorageId | string | 是 | 起点库位ID |
| endStorageId | string | 是 | 终点库位ID |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "物料从库位1-1成功流转到库位2-2",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容(包含流转详情) |
| data | object | 返回数据 |

---

### 5. GetOuterMaterial - 获取最外侧物料

- **接口地址**: `/api/Material/GetOuterMaterial?startStorageId={startStorageId}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/json
- **接口描述**: 获取库位最外侧(可出库)的物料信息

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| startStorageId | string | 是 | 库位ID |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "id": 1,
    "materialNumber": "M001",
    "belongId": "STORAGE001",
    "index": 1
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 物料信息 |

---

### 6. GetAll/Delete (继承) - 获取/删除物料

- **接口地址**: `/api/Material/GetAll`, `/api/Material/Delete/{id}`
- **请求方式**: GET/DELETE
- **响应数据类型**: application/json

---

## 八、PathCreateController - 路径创建

### 1. CreatePath - 创建路径

- **接口地址**: `/api/PathCreate/CreatePath`
- **请求方式**: POST
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 根据库位和对接口信息自动生成路径配置文件

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据 |

> 生成的路径文件保存到服务器 `Path/{区域}.json`

---

### 2. GetTargetsInfo - 获取目标信息

- **接口地址**: `/api/PathCreate/GetTargetsInfo`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有目标点(端口)信息

**响应参数:** 同 Robot GetRobotInfos

---

## 九、BatterySocInfoController - 电池标定管理

继承自 `ApiBaseController<BatterySocInfo, BatterySocInfo, IBaseRepository<BatterySocInfo>, int>`

### 1. Add/GetAll/Update/Delete (继承) - CRUD操作

- **接口地址**: `/api/BatterySocInfo/Add`, `/api/BatterySocInfo/GetAll`, `/api/BatterySocInfo/Update`, `/api/BatterySocInfo/Delete/{id}`
- **请求方式**: POST/GET/POST/DELETE
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 电池标定信息的增删改查操作

**请求示例:**
```json
{
  "robotName": "机器人1",
  "ip": "192.168.1.100",
  "startBattery": 100,
  "startChargingTime": "2024-01-01T10:00:00",
  "endBattery": 90,
  "startTime": "2024-01-01T10:00:00",
  "endTime": "2024-01-01T11:00:00"
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 电池标定信息 |

---

## 附录: 通用响应格式

### 成功响应
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {}
}
```

### 失败响应
```json
{
  "status": 500,
  "isSuccess": false,
  "message": "错误信息",
  "data": null
}
```

### 响应字段说明
| 字段 | 类型 | 描述 |
|------|------|------|
| status | int | 状态码(0=成功,其他=失败) |
| isSuccess | bool | 是否成功 |
| message | string | 消息/错误信息 |
| data | object | 返回数据 |

---

## 附录: 枚举参考

### AgvTaskStatus - 任务状态
| 值 | 名称 | 描述 |
|----|------|------|
| -1 | None | 无 |
| 0 | Pending | 待分配(任务刚创建，未分配机器人) |
| 10 | Assign | 已分配(任务已分配给机器人) |
| 30 | Executed | 已执行(机器人开始执行) |
| 60 | Docking | 对接中(正在与目标点对接) |
| 70 | Transmitting | 传输中(任务执行中) |
| 79 | ToCompletion | 即将完成 |
| 80 | Completed | 已完成(任务成功完成) |
| 89 | ToCancel | 即将取消 |
| 90 | Canceled | 已取消(任务被取消) |
| 100 | ForcedShutdown | 强制关闭 |

### AgvTaskType - 任务类型
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | None | 无 |
| 1 | Get | 取料 |
| 2 | Put | 放料 |
| 3 | Park | 停车 |
| 4 | Charge | 充电 |
| 5 | GetPut | 取放 |

### RobotCategory - 机器人类别
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | Normal | 普通AGV |
| 1 | JunionFork | 窄体叉车 |
| 2 | SeerFork | 仙工叉车 |

### LocationType - 库位类型
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | Normal | 普通库位 |
| 1 | Cache | 缓存库位 |
| 2 | ActiveStorage | 有源库位 |
| 3 | CachePort | 缓存对接口库位 |
| 4 | DeviceStorage | 设备映射库位 |
| 5 | NotLoked | 不锁定库位 |
| 6 | Intelligent | 智能容量库位 |
| 7 | LiftTransfer | 电梯中转库位 |
| 8 | CanPutAnything | 万能放置库位 |


### TargetType - 目标类型
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | Park | 停车点 |
| 1 | Charge | 充电点 |
| 2 | Storage | 存储点 |
| 3 | DockingPort | 对接口 |

### ActionStatus - 动作完成状态
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | None | 无 |
| 1 | Pending | 等待中 |
| 2 | Success | 成功 |
| 3 | Retry | 重试 |
| 4 | WaitToCheck | 等待检查 |
| 5 | WaitToReponse | 等待响应 |