# TaskAssignManager API 接口文档

| 文件名称 | TaskAssignManager API 接口文档                   |
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

## 一、AgvTaskController - 任务管理

继承自 `ApiBaseController<AgvTask, AgvTaskDto, IBaseRepository<AgvTask>, string>`

### 1. CreatePairJob - 创建配对任务

- **接口地址**: `/api/AgvTask/CreatePairJob`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 创建起始任务（配对任务：取料+放料）

**请求示例:**
```json
{
  "id": "唯一标识",
  "start": "起点料口ID",
  "end": "终点料口ID",
  "extraInfo": {},
  "callTime": "2024-01-01T00:00:00",
  "source": 0,
  "remark": "备注"
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 唯一标识呼叫信息 |
| start | string | 是 | 起点料口ID |
| end | string | 是 | 终点料口ID |
| extraInfo | Dictionary<string,string> | 否 | 额外的包号信息 |
| callTime | DateTime? | 否 | 呼叫时间 |
| source | TaskSource | 否 | 任务来源(默认0=DeviceCall) |
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
| data | object | 返回数据(新增成功的任务数量) |

---

### 2. CreateSingleJob - 创建单点任务

- **接口地址**: `/api/AgvTask/CreateSingleJob`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 创建单点任务（取料或放料）

**请求示例:**
```json
{
  "id": "唯一标识",
  "target": "目标料口ID",
  "taskType": 0,
  "extraInfo": {},
  "callTime": "2024-01-01T00:00:00",
  "isAllowRepeat": false,
  "source": 0,
  "remark": "备注"
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 唯一标识呼叫信息 |
| target | string | 是 | 目标料口ID |
| taskType | AgvTaskType | 是 | 任务类型(0=Get取料, 1=Put放料) |
| extraInfo | Dictionary<string,string> | 否 | 额外的包号信息 |
| callTime | DateTime? | 否 | 呼叫时间 |
| isAllowRepeat | bool | 否 | 是否允许重复呼叫 |
| source | TaskSource | 否 | 任务来源 |
| remark | string | 否 | 备注 |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": "Success"
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 返回数据(新增成功的任务数量) |

---

### 3. CreateMultiSingleJob - 设备呼叫创建多任务

- **接口地址**: `/api/AgvTask/CreateMultiSingleJob`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 设备呼叫创建多个单点任务

**请求示例:**
```json
[
  {
    "id": "唯一标识1",
    "target": "目标料口ID1",
    "taskType": 0,
    "isAllowRepeat": false
  },
  {
    "id": "唯一标识2",
    "target": "目标料口ID2",
    "taskType": 1,
    "isAllowRepeat": false
  }
]
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| 数组 | List<CallInfo> | 是 | 多个单点呼叫信息 |

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
| data | object | 返回数据(新增成功的任务数量) |

---

### 4. GetTaskStatus - 获取任务状态列表

- **接口地址**: `/api/AgvTask/GetTaskStatus`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有任务状态枚举列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "key": "Pending", "value": 0 },
    { "key": "Assigned", "value": 1 },
    { "key": "Executing", "value": 2 },
    { "key": "Completed", "value": 3 },
    { "key": "Cancelled", "value": 4 }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 任务状态枚举数组(key=名称, value=值) |

---

### 5. GetTaskType - 获取任务类型列表

- **接口地址**: `/api/AgvTask/GetTaskType`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有任务类型枚举列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "key": "Get", "value": 0 },
    { "key": "Put", "value": 1 }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 任务类型枚举数组(key=名称, value=值) |

---

### 6. GetTaskSource - 获取任务来源列表

- **接口地址**: `/api/AgvTask/GetTaskSource`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有任务来源枚举列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "key": "DeviceCall", "value": 0 },
    { "key": "ManualCreate", "value": 1 },
    { "key": "SystemCall", "value": 2 }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 任务来源枚举数组(key=名称, value=值) |

---

### 7. UpdateTaskPriority - 更新任务优先级

- **接口地址**: `/api/AgvTask/UpdateTaskPriority/{id}/{priority}`
- **请求方式**: PUT
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 更新指定任务的优先级

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 任务ID(路径参数) |
| priority | int | 是 | 优先级(路径参数) |

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

### 8. QueryRealTaskByPage - 分页查询实时任务

- **接口地址**: `/api/AgvTask/QueryRealTaskByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询未完成的任务（实时任务，状态 < Completed）

**请求示例:**
```json
{
  "page": 1,
  "pageSize": 20,
  "orderBy": "CreateTime",
  "isDes": true,
  "query": {
    "target": "PORT001",
    "region": "A区",
    "status": 0
  }
}
```

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| target | string | "PORT001" | 目标点ID (模糊匹配) |
| region | string | "A区" | 区域 (模糊匹配) |
| status | number | 0 | 任务状态 (精确匹配) |
| type | number | 0 | 任务类型 (精确匹配) |
| source | number | 1 | 任务来源 (精确匹配) |
| priority | number | 1 | 优先级 (精确匹配) |
| robotId | string | "ROBOT001" | 机器人ID (模糊匹配) |
| agvType | string | "AGV01" | AGV类型 (模糊匹配) |
| beginTime | array | ["2024-01-01", "2024-12-31"] | 创建时间范围 |
| completeTime | array | ["2024-01-01", "2024-12-31"] | 完成时间范围 |
| id | string | "TASK001" | 任务ID (模糊匹配) |
| groupId | string | "GROUP001" | 任务组ID (模糊匹配) |
| content | string | "包号001" | 任务内容 (模糊匹配) |

> 注意: 时间范围查询值为数组格式 `["开始时间", "结束时间"]`，其他字段为精确匹配或模糊匹配

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| page | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| orderBy | string | 否 | 排序字段 (如 CreateTime, Priority, Status) |
| isDes | bool | 否 | 是否降序 (true=降序, false=升序) |
| query | JObject | 否 | 查询条件 (键值对，见上表) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "page": 1,
    "pageSize": 20,
    "total": 100,
    "dataList": [
      {
        "id": "TASK001",
        "target": "PORT001",
        "targetName": "料口1",
        "groupId": "GROUP001",
        "order": 1,
        "robotId": "ROBOT001",
        "status": 0,
        "type": 0,
        "content": "包号001",
        "region": "A区",
        "agvType": "AGV01",
        "source": 1,
        "priority": 1,
        "createTime": "2024-01-01T10:00:00",
        "beginTime": null,
        "confirmTime": null,
        "allowEntryTime": null,
        "loadOrUnLoadTime": null,
        "completeTime": null,
        "cancelTime": null,
        "remark": null
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
| data | object | 分页数据对象 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页数量 |
| data.total | int | 总记录数 |
| data.dataList | array | 数据列表 |
| dataList[].id | string | 任务ID |
| dataList[].target | string | 目标点ID |
| dataList[].targetName | string | 目标点名称 |
| dataList[].groupId | string | 任务组ID |
| dataList[].order | int | 任务顺序 |
| dataList[].robotId | string | 执行机器人ID |
| dataList[].status | int | 任务状态 |
| dataList[].type | int | 任务类型 |
| dataList[].content | string | 任务内容 |
| dataList[].region | string | 区域 |
| dataList[].agvType | string | 可用机器人类型 |
| dataList[].source | int | 任务来源 |
| dataList[].priority | int | 优先级 |
| dataList[].createTime | DateTime | 创建时间 |
| dataList[].beginTime | DateTime? | 开始执行时间 |
| dataList[].confirmTime | DateTime? | 握手时间 |
| dataList[].allowEntryTime | DateTime? | 允许进入时间 |
| dataList[].loadOrUnLoadTime | DateTime? | 载卸货时间 |
| dataList[].completeTime | DateTime? | 任务完成时间 |
| dataList[].cancelTime | DateTime? | 任务取消时间 |
| dataList[].remark | string | 备注 |

---

### 9. QueryDataByPage - 分页查询历史任务

- **接口地址**: `/api/AgvTask/QueryDataByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询历史任务记录（包含已完成的任务，支持跨表查询历史数据）

**请求示例:**
```json
{
  "page": 1,
  "pageSize": 20,
  "orderBy": "CreateTime",
  "isDes": true,
  "query": {
    "target": "PORT001",
    "region": "A区",
    "status": 3,
    "type": 0,
    "source": 1,
    "beginTime": ["2024-01-01", "2024-12-31"],
    "completeTime": ["2024-01-01", "2024-12-31"],
    "agvType": "AGV01"
  }
}
```

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| target | string | "PORT001" | 目标点ID (模糊匹配) |
| region | string | "A区" | 区域 (模糊匹配) |
| status | number | 0,1,2,3,4 | 任务状态 (精确匹配) |
| type | number | 0,1 | 任务类型 (精确匹配) |
| source | number | 0,1,2 | 任务来源 (精确匹配) |
| priority | number | 1 | 优先级 (精确匹配) |
| robotId | string | "ROBOT001" | 机器人ID (模糊匹配) |
| agvType | string | "AGV01" | AGV类型 (模糊匹配) |
| beginTime | array | ["2024-01-01", "2024-12-31"] | 创建时间范围 |
| completeTime | array | ["2024-01-01", "2024-12-31"] | 完成时间范围 |
| id | string | "TASK001" | 任务ID (模糊匹配) |
| groupId | string | "GROUP001" | 任务组ID (模糊匹配) |
| content | string | "包号001" | 任务内容 (模糊匹配) |

> 注意: 
> - 时间范围查询值为数组格式 `["开始时间", "结束时间"]`
> - 其他字段为精确匹配或模糊匹配
> - 历史任务查询会根据配置的TaskExpireDays自动合并历史表数据

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| page | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| orderBy | string | 否 | 排序字段 (如 CreateTime, Priority, Status, CompleteTime) |
| isDes | bool | 否 | 是否降序 (true=降序, false=升序) |
| query | JObject | 否 | 查询条件 (键值对，见上表) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "page": 1,
    "pageSize": 20,
    "total": 100,
    "dataList": [
      {
        "id": "TASK001",
        "target": "PORT001",
        "targetName": "料口1",
        "groupId": "GROUP001",
        "order": 1,
        "robotId": "ROBOT001",
        "status": 3,
        "type": 0,
        "content": "包号001",
        "region": "A区",
        "agvType": "AGV01",
        "source": 1,
        "priority": 1,
        "createTime": "2024-01-01T10:00:00",
        "beginTime": "2024-01-01T10:05:00",
        "confirmTime": "2024-01-01T10:06:00",
        "allowEntryTime": "2024-01-01T10:07:00",
        "loadOrUnLoadTime": "2024-01-01T10:10:00",
        "completeTime": "2024-01-01T10:15:00",
        "cancelTime": null,
        "remark": "任务完成"
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
| data | object | 分页数据对象 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页数量 |
| data.total | int | 总记录数 |
| data.dataList | array | 数据列表 |
| dataList[].id | string | 任务ID |
| dataList[].target | string | 目标点ID |
| dataList[].targetName | string | 目标点名称 |
| dataList[].groupId | string | 任务组ID |
| dataList[].order | int | 任务顺序 |
| dataList[].robotId | string | 执行机器人ID |
| dataList[].status | int | 任务状态 (0=Pending,1=Assigned,2=Executing,3=Completed,4=Cancelled) |
| dataList[].type | int | 任务类型 (0=Get取料,1=Put放料) |
| dataList[].content | string | 任务内容 |
| dataList[].region | string | 区域 |
| dataList[].agvType | string | 可用机器人类型 |
| dataList[].source | int | 任务来源 (0=设备呼叫,1=手动创建,2=系统呼叫) |
| dataList[].priority | int | 优先级 |
| dataList[].createTime | DateTime | 创建时间 |
| dataList[].beginTime | DateTime? | 开始执行时间 |
| dataList[].confirmTime | DateTime? | 握手时间 |
| dataList[].allowEntryTime | DateTime? | 允许进入时间 |
| dataList[].loadOrUnLoadTime | DateTime? | 载卸货时间 |
| dataList[].completeTime | DateTime? | 任务完成时间 |
| dataList[].cancelTime | DateTime? | 任务取消时间 |
| dataList[].remark | string | 备注 |

---

### 10. GetRowsCount - 确认目标点是否存在

- **接口地址**: `/api/AgvTask/GetRowsCount/{id}`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 验证目标点ID是否存在于数据库

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 目标点ID(路径参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": 1
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | int | 记录数量(>0表示存在) |

---

## 二、SystemParameterController - 系统参数

### 1. GetSystemParameter - 获取所有系统参数

- **接口地址**: `/api/SystemParameter/GetSystemParameter`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取当前系统所有参数配置

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "maxPower": 100,
    "minPower": 20,
    "middlePower": 50,
    "dangerPower": 15,
    "availableStatus": "Online",
    "isRegionCheck": true,
    "enableMultiCharge": false,
    "waitTime": 30,
    "isParkControl": true,
    "isPositionCheck": true,
    "isLocationMutual": false,
    "offlineTime": 300,
    "allowableDeviation": 50,
    "isBindingAssign": false,
    "withMaterialChargeRobot": null,
    "withMaterialParkRobot": null,
    "isDelayReleasePark": false,
    "delayReleaseParkTime": 0,
    "isDelayReleaseDock": false,
    "delayReleaseDockTime": 0,
    "calibrationTimeInterval": 3600,
    "isIgnoreNotice": false,
    "isCalibration": false,
    "calibrationDuration": 300,
    "forkUdpPort": 5000,
    "udpPort": 5001,
    "normalTcpServerPort": 8000,
    "forkTcpServerPort": 8001,
    "stringParameter": {},
    "intParameter": {},
    "booleanParameter": {}
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 系统参数对象 |
| data.maxPower | int | 最大电量 |
| data.minPower | int | 最小电量 |
| data.middlePower | int | 中等电量(去Park点) |
| data.dangerPower | int | 危险电量 |
| data.availableStatus | string | 可用状态 |
| data.isRegionCheck | bool | 是否区域校验 |
| data.enableMultiCharge | bool | 是否启用多充电 |
| data.waitTime | int | 等待时间(秒) |
| data.isParkControl | bool | 是否管控停车点 |
| data.isPositionCheck | bool | 是否位置校验 |
| data.isLocationMutual | bool | 位置互斥是否打开 |
| data.offlineTime | int | 机器人离线判断时间(秒) |
| data.allowableDeviation | int | 机器人到对接口允许偏差值 |
| data.isBindingAssign | bool | 是否开启资源点绑定 |
| data.withMaterialChargeRobot | string | 带料停车的机器人类型 |
| data.withMaterialParkRobot | string | 带料充电的机器人类型 |
| data.isDelayReleasePark | bool | 是否延迟释放停车点 |
| data.delayReleaseParkTime | int | 延迟释放停车点时间(秒) |
| data.isDelayReleaseDock | bool | 是否延迟释放充电点 |
| data.delayReleaseDockTime | int | 延迟释放充电点时间(秒) |
| data.calibrationTimeInterval | int | 校准时间间隔(秒) |
| data.isIgnoreNotice | bool | 是否忽略通知 |
| data.isCalibration | bool | 是否校准 |
| data.calibrationDuration | int | 校准持续时间(秒) |
| data.forkUdpPort | int | 叉车UDP端口 |
| data.udpPort | int | 非叉车UDP端口 |
| data.normalTcpServerPort | int | 普通TCP服务器端口 |
| data.forkTcpServerPort | int | 叉车TCP服务器端口 |
| data.stringParameter | Dictionary | 字符串参数 |
| data.intParameter | Dictionary | 整数参数 |
| data.booleanParameter | Dictionary | 布尔参数 |

---

### 2. UpdateSystemParameter - 更新系统参数

- **接口地址**: `/api/SystemParameter/UpdateSystemParameter`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新系统参数配置(写入配置文件)

**请求示例:**
```json
{
  "maxPower": 100,
  "minPower": 20,
  "middlePower": 50,
  "dangerPower": 15,
  "availableStatus": "Online",
  "isRegionCheck": true,
  "enableMultiCharge": false,
  "waitTime": 30,
  "isParkControl": true,
  "isPositionCheck": true,
  "isLocationMutual": false,
  "offlineTime": 300,
  "allowableDeviation": 50,
  "isBindingAssign": false,
  "withMaterialChargeRobot": null,
  "withMaterialParkRobot": null,
  "isDelayReleasePark": false,
  "delayReleaseParkTime": 0,
  "isDelayReleaseDock": false,
  "delayReleaseDockTime": 0,
  "calibrationTimeInterval": 3600,
  "isIgnoreNotice": false,
  "isCalibration": false,
  "calibrationDuration": 300,
  "forkUdpPort": 5000,
  "udpPort": 5001,
  "normalTcpServerPort": 8000,
  "forkTcpServerPort": 8001,
  "stringParameter": {},
  "intParameter": {},
  "booleanParameter": {}
}
```

**请求参数:**
同 GetSystemParameter 响应参数

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

## 三、RmsPathBindingController - 交管信息管理

继承自 `ApiBaseController<RmsPathBindingInfo, RmsPathBindingInfoDto, IBaseRepository<RmsPathBindingInfo>, int>`

### 1. Update - 更新机器人绑定信息

- **接口地址**: `/api/RmsPathBinding/Update`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新交管服务器绑定的机器人信息

**请求示例:**
```json
{
  "id": 1,
  "serverIP": "192.168.1.100",
  "region": "A区",
  "port": 8080,
  "robotIds": ["Robot001", "Robot002", "Robot003"]
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | int | 是 | ID身份标志 |
| serverIP | string | 是 | 交管服务器IP |
| region | string | 是 | 所属区域 |
| port | int | 是 | 交管服务器端口 |
| robotIds | string[] | 是 | 绑定机器人ID数组 |

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

### 2. GetLicenseDate - 获取证书日期

- **接口地址**: `/api/RmsPathBinding/GetLicenseDate`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取许可证日期信息

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "expiryDate": "2025-12-31",
    "licenseKey": "XXX-XXX-XXX"
  }
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | object | 许可证信息 |
| data.expiryDate | string | 过期日期 |
| data.licenseKey | string | 许可证密钥 |

---

### 3. Add (继承) - 新增交管绑定

- **接口地址**: `/api/RmsPathBinding/Add`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 新增交管服务器绑定信息

**请求示例:**
```json
{
  "serverIP": "192.168.1.100",
  "region": "A区",
  "port": 8080,
  "robotIds": ["Robot001"]
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| serverIP | string | 是 | 交管服务器IP |
| region | string | 是 | 所属区域 |
| port | int | 是 | 交管服务器端口 |
| robotIds | string[] | 是 | 绑定机器人ID数组 |

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

### 4. Delete (继承) - 删除交管绑定

- **接口地址**: `/api/RmsPathBinding/Delete/{id}`
- **请求方式**: DELETE
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 删除指定交管绑定信息

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | int | 是 | 交管绑定ID(路径参数) |

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

### 5. GetAll (继承) - 获取所有交管绑定

- **接口地址**: `/api/RmsPathBinding/GetAll`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有交管绑定信息列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    {
      "id": 1,
      "serverIP": "192.168.1.100",
      "region": "A区",
      "port": 8080,
      "robotIds": ["Robot001", "Robot002"]
    },
    {
      "id": 2,
      "serverIP": "192.168.1.101",
      "region": "B区",
      "port": 8081,
      "robotIds": ["Robot003"]
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
| data | array | 交管绑定列表 |
| data[].id | int | 交管绑定ID |
| data[].serverIP | string | 交管服务器IP |
| data[].region | string | 所属区域 |
| data[].port | int | 交管服务器端口 |
| data[].robotIds | string[] | 绑定机器人ID数组 |

---

## 四、CommonFacilityController - 通用设施管理

继承自 `ApiBaseController<CommonFacility, CommonFacilityDto, IBaseRepository<CommonFacility>, string>`

### 1. CheckOnly - 确认IP是否唯一

- **接口地址**: `/api/CommonFacility/CheckOnly/{id}`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 验证设施ID是否唯一

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 设施ID(路径参数) |

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

### 2. AllEnableOrDisable - 全部启用/禁用

- **接口地址**: `/api/CommonFacility/AllEnableOrDisable`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 启用或禁用所有设施

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

### 3. Import - 导入料口数据

- **接口地址**: `/api/CommonFacility/Import`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 批量导入或更新料口数据(存在则更新,不存在则新增)

**请求示例:**
```json
[
  {
    "id": "PORT001",
    "name": "料口1",
    "remark": "备注",
    "group": "A组",
    "process": "工艺1",
    "isLocked": false,
    "enable": true,
    "region": "A区",
    "xPosition": 100.5,
    "yPosition": 200.3,
    "agvType": "AGV01",
    "type": "0",
    "isUsed": false,
    "robot": null,
    "feature": null,
    "description": "描述",
    "mapStation": null,
    "needContent": null
  }
]
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| 数组 | CommonFacilityDto[] | 是 | 料口数据数组 |

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

### 4. GetParkInfos - 获取所有停车点信息

- **接口地址**: `/api/CommonFacility/GetParkInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有停车点(Park类型)信息

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "id": "PARK001", "name": "停车点1" },
    { "id": "PARK002", "name": "停车点2" }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 停车点列表 |
| data[].id | string | 停车点ID |
| data[].name | string | 停车点名称 |

---

### 5. GetChargeInfos - 获取所有充电点信息

- **接口地址**: `/api/CommonFacility/GetChargeInfos`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有充电点(Charge类型)信息

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "id": "CHARGE001", "name": "充电点1" },
    { "id": "CHARGE002", "name": "充电点2" }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 充电点列表 |
| data[].id | string | 充电点ID |
| data[].name | string | 充电点名称 |

---

### 6. GetAllPortsInfo - 获取所有料口资源点信息

- **接口地址**: `/api/CommonFacility/GetAllPortsInfo`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有料口资源点(BasicPort)信息

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    { "id": "PORT001", "name": "料口1" },
    { "id": "PORT002", "name": "料口2" }
  ]
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | array | 料口列表 |
| data[].id | string | 料口ID |
| data[].name | string | 料口名称 |

---

### 7. GetRowsCount - 确认目标点是否唯一

- **接口地址**: `/api/CommonFacility/GetRowsCount/{id}`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 验证目标点ID是否存在于T_Targets表

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 目标点ID(路径参数) |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": 1
}
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| status | int | 状态码(0=成功) |
| isSuccess | bool | 是否成功 |
| message | string | 消息内容 |
| data | int | 记录数量(>0表示存在) |

---

### 8. Add (继承) - 新增设施

- **接口地址**: `/api/CommonFacility/Add`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 新增通用设施信息

**请求示例:**
```json
{
  "id": "FACILITY001",
  "name": "设施1",
  "remark": "备注信息",
  "group": "A组",
  "process": "工艺1",
  "isLocked": false,
  "enable": true,
  "region": "A区",
  "xPosition": 100.5,
  "yPosition": 200.3,
  "agvType": "AGV01",
  "type": "0",
  "isUsed": false,
  "robot": null,
  "feature": null,
  "description": "描述信息",
  "mapStation": null,
  "needContent": null
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 设施ID |
| name | string | 否 | 设施名称 |
| remark | string | 否 | 备注 |
| group | string | 否 | 分组(定义特性,如叉车中发给不同的交管信息) |
| process | string | 否 | 所属工艺 |
| isLocked | bool | 否 | 是否锁住 |
| enable | bool | 否 | 是否启用(默认true) |
| region | string | 否 | 所属区域 |
| xPosition | float | 否 | X坐标 |
| yPosition | float | 否 | Y坐标 |
| agvType | string | 否 | AGV类型 |
| type | string | 否 | 类型(0=AGV, 1=AGV组) |
| isUsed | bool | 否 | 是否使用中 |
| robot | string | 否 | 机器人信息 |
| feature | string | 否 | 特性 |
| description | string | 否 | 描述 |
| mapStation | string | 否 | 地图站点 |
| needContent | string | 否 | 需求内容 |

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

### 9. Update (继承) - 更新设施

- **接口地址**: `/api/CommonFacility/Update`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 更新通用设施信息

**请求示例:**
```json
{
  "id": "FACILITY001",
  "name": "设施1(更新)",
  "remark": "更新后的备注",
  "group": "B组",
  "enable": false
}
```

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 设施ID(唯一标识) |
| name | string | 否 | 设施名称 |
| remark | string | 否 | 备注 |
| group | string | 否 | 分组 |
| process | string | 否 | 所属工艺 |
| isLocked | bool | 否 | 是否锁住 |
| enable | bool | 否 | 是否启用 |
| region | string | 否 | 所属区域 |
| xPosition | float | 否 | X坐标 |
| yPosition | float | 否 | Y坐标 |
| agvType | string | 否 | AGV类型 |
| type | string | 否 | 类型 |
| isUsed | bool | 否 | 是否使用中 |
| robot | string | 否 | 机器人信息 |
| feature | string | 否 | 特性 |
| description | string | 否 | 描述 |
| mapStation | string | 否 | 地图站点 |
| needContent | string | 否 | 需求内容 |

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

### 10. Delete (继承) - 删除设施

- **接口地址**: `/api/CommonFacility/Delete/{id}`
- **请求方式**: DELETE
- **请求数据类型**: URL参数
- **响应数据类型**: application/json
- **接口描述**: 删除指定设施信息

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| id | string | 是 | 设施ID(路径参数) |

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

### 11. GetAll (继承) - 获取所有设施

- **接口地址**: `/api/CommonFacility/GetAll`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: application/json
- **接口描述**: 获取所有通用设施信息列表

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": [
    {
      "id": "FACILITY001",
      "name": "设施1",
      "remark": "备注",
      "group": "A组",
      "process": "工艺1",
      "isLocked": false,
      "enable": true,
      "region": "A区",
      "xPosition": 100.5,
      "yPosition": 200.3,
      "agvType": "AGV01",
      "type": "0",
      "isUsed": false,
      "robot": null,
      "feature": null,
      "description": "描述",
      "mapStation": null,
      "needContent": null
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
| data | array | 设施列表 |
| data[].id | string | 设施ID |
| data[].name | string | 设施名称 |
| data[].remark | string | 备注 |
| data[].group | string | 分组 |
| data[].process | string | 所属工艺 |
| data[].isLocked | bool | 是否锁住 |
| data[].enable | bool | 是否启用 |
| data[].region | string | 所属区域 |
| data[].xPosition | float | X坐标 |
| data[].yPosition | float | Y坐标 |
| data[].agvType | string | AGV类型 |
| data[].type | string | 类型(0=AGV, 1=AGV组) |
| data[].isUsed | bool | 是否使用中 |
| data[].robot | string | 机器人信息 |
| data[].feature | string | 特性 |
| data[].description | string | 描述 |
| data[].mapStation | string | 地图站点 |
| data[].needContent | string | 需求内容 |

---

## 五、LogController - 日志管理

### 1. Test - 测试接口

- **接口地址**: `/api/Log/Test`
- **请求方式**: GET
- **请求数据类型**: -
- **响应数据类型**: text/plain
- **接口描述**: 测试服务是否正常运行

**响应示例:**
```
task-assign
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| - | string | 返回纯文本 "task-assign" |

---

### 2. QueryDataByPage - 分页查找日志

- **接口地址**: `/api/Log/QueryDataByPage`
- **请求方式**: POST
- **请求数据类型**: application/json
- **响应数据类型**: application/json
- **接口描述**: 分页查询系统日志文件

**请求示例:**
```json
{
  "page": 1,
  "pageSize": 20,
  "orderBy": "UpdateTime",
  "isDes": true,
  "query": {
    "name": "2024-01",
    "createTime": ["2024-01-01", "2024-01-31"],
    "updateTime": ["2024-01-01", "2024-01-31"]
  }
}
```

**Query 参数说明 (键值对):**
| 键名 | 值类型 | 示例值 | 说明 |
|------|--------|--------|------|
| name | string | "2024-01" | 文件名关键字 (模糊匹配) |
| createTime | array | ["2024-01-01", "2024-01-31"] | 创建时间范围 |
| updateTime | array | ["2024-01-01", "2024-01-31"] | 更新时间范围 |

> 注意: 时间范围查询值为数组格式 `["开始时间", "结束时间"]`

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| page | int | 是 | 页码 |
| pageSize | int | 是 | 每页数量 |
| orderBy | string | 否 | 排序字段 (如 UpdateTime, CreateTime) |
| isDes | bool | 否 | 是否降序 (true=降序, false=升序) |
| query.name | string | 否 | 文件名关键字 |
| query.createTime | array | 否 | 创建时间范围 [开始, 结束] |
| query.updateTime | array | 否 | 更新时间范围 [开始, 结束] |

**响应示例:**
```json
{
  "status": 0,
  "isSuccess": true,
  "message": "",
  "data": {
    "page": 1,
    "pageSize": 20,
    "total": 50,
    "dataList": [
      {
        "fileName": "log20240101.txt",
        "filePath": "Logs/log20240101.txt",
        "fileSize": 1024,
        "createTime": "2024-01-01T00:00:00",
        "updateTime": "2024-01-01T23:59:59"
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
| data | object | 分页数据对象 |
| data.page | int | 当前页码 |
| data.pageSize | int | 每页数量 |
| data.total | int | 总记录数 |
| data.dataList | array | 数据列表 |
| dataList[].fileName | string | 日志文件名 |
| dataList[].filePath | string | 文件完整路径 |
| dataList[].fileSize | long | 文件大小(字节) |
| dataList[].createTime | DateTime | 文件创建时间 |
| dataList[].updateTime | DateTime | 文件最后更新时间 |

---

### 3. DownFile - 下载日志

- **接口地址**: `/api/Log/DownFile?path={path}`
- **请求方式**: GET
- **请求数据类型**: query参数
- **响应数据类型**: application/zip
- **接口描述**: 下载指定的日志文件(打包成zip)

**请求参数:**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| path | string | 是 | 日志文件路径(查询参数) |

**响应示例:**
```
Content-Type: application/zip
Content-Disposition: attachment; filename=log20240101.zip
```

**响应参数:**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| Content-Type | string | 响应类型(application/zip) |
| Content-Disposition | string | 文件下载声明 |

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
| 0 | Pending | 待分配(任务刚创建，未分配机器人) |
| 1 | Assigned | 已分配(任务已分配给机器人) |
| 2 | Executing | 执行中(机器人正在执行任务) |
| 3 | Completed | 已完成(任务成功完成) |
| 4 | Cancelled | 已取消(任务被取消) |

### AgvTaskType - 任务类型
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | None | 无(未指定) |
| 1 | Get | 取料(从目标点取货) |
| 2 | Put | 放料(向目标点送货) |
| 3 | Park | 停车(前往停车点) |
| 4 | Charge | 充电(前往充电点) |
| 5 | GetPut | 取放(同时取货和送货) |

### TaskSource - 任务来源
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | DeviceCall | 设备呼叫(外部设备触发) |
| 1 | MESCreate | MES创建(MES系统创建) |
| 2 | ManualCreate | 手动创建(人工创建任务) |
| 3 | SystemCreate | 系统创建(系统自动触发) |
| 10 | Others | 其他来源 |

### TargetType - 目标类型
| 值 | 名称 | 描述 |
|----|------|------|
| 0 | Park | 停车点(AGV停车位置) |
| 1 | Charge | 充电点(AGV充电位置) |
| 2 | Storage | 存储点(仓库/料仓) |
| 3 | DockingPort | 对接口(料口/工位) |