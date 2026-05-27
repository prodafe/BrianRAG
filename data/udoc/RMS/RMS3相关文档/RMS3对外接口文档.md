# 1.任务创建接口
## 1.1 单目标点创建任务

**接口地址**：http://ip:8200/api/AgvTask/CreateSingleJob

**请求方式**：post

**请求数据类型**：application/json

**响应数据类型**：application/json

**请求参数**：

| 参数名称          | 类型     | 是否必须 | 说明                            |
|---------------|--------| ---- |-------------------------------|
| id            | string | 是    | 请求唯一标识，必须唯一                   |
| target        | string | 是    | 目标                            |
| taskType      | int    | 是    | 任务类型，1-接料 2-送料                |
| isAllowRepeat | bool   | 否    | 是否允许重复创建，默认是false             |
| callTime      | string | 是    | 呼叫时间，yyyy-MM-dd HH:mm:ss格式    |
| source        | int    | 否    | 请求来源：0代表设备呼叫，1代表MES创建，2代表手动创建 |
| remark        | string | 否    | 备注信息                          |
| extraInfo     | object | 是    | 物料包号，json类型，不已 * 开头的key将参与物料匹配 |

**请求示例**：

``` json
{
    "id": "10002",
    "target": "D001",
    "taskType": 1,
    "extraInfo": {
        "key1": "用于匹配接送任务的键值对",
        "key2": "key不以*开始的键值对都会参与任务匹配",
        "*key3": "key以*开始的键值对用于触发其他逻辑",
        "*storage": "true"
        "*key4": "*storage为true,表示调度自行按照包号和任务类型选择起点/终点"
    },
    "callTime": "2025-02-10 10:00:00",
    "isAllowRepeat": false,
    "source": 1,
    "remark": ""
}
```


**响应参数**：

| 参数名称                        | 类型     | 是否必须 | 说明         |
|-----------------------------|--------| ---- |------------|
| status                      | int    | 是    | 0或者200表示成功 |
| isSuccess                   | bool   | 是    | 是否调用成功     |
| data                        | object | 否    | 业务数据       |
| &nbsp;&nbsp; &nbsp;id       | int    | 是    | rms系统任务id  |
| &nbsp;&nbsp; &nbsp;taskType | int    | 是    | 任务类型,1-接料 2-送料      |
| message                     | string | 是    | 错误说明       |

**示例响应**:
```json
{
    "status": 0,
    "isSuccess": true,
    "data": {
	    "id": 1,
	    "taskType": 1
    },
    "message": "success"
}
```


## 1.2 双目标点创建任务

**接口地址**：http://ip:8200/api/AgvTask/CreatePairTask

**请求方式**：post

**请求数据类型**：application/json

**响应数据类型**：application/json

**请求参数**：

| 参数名称          | 类型     | 是否必须 | 说明                                         |
|---------------|--------| ---- | ------------------------------------------ |
| id            | string | 是    | 请求唯一标识，必须唯一                                |
| start         | string | 是    | 任务接料点                                      |
| end           | string | 是    | 任务送料点                                      |
| isAllowRepeat | bool   | 否    | 是否允许重复创建，默认是false                          |
| callTime      | string | 是    | 呼叫时间，yyyy-MM-dd HH:mm:ss格式                 |
| source        | int    | 否    | 请求来源：0代表设备呼叫，1代表MES创建，2代表手动创建 |
| remark        | string | 否    | 备注信息                                       |
| extraInfo     | object | 否    | 物料包号，json类型，不已 * 开头的key将参与物料匹配             |

**请求示例**：

```json
{
    "id": "10001",
    "start": "D001",
    "end": "D002",
    "extraInfo": {
        "key1": "用于匹配接送任务的键值对",
        "key2": "key不以*开始的键值对都会参与任务匹配",
        "*key3": "key以*开始的键值对用于触发其他逻辑"
    },
    "callTime": "2025-02-10 10:00:00",
    "source": 1,
    "remark": ""
}
```
**响应参数**：

| 参数名称                        | 类型     | 是否必须 | 说明        |
|-----------------------------|--------| ---- |-----------|
| status                      | int    | 是    | 0或200表示成功 |
| isSuccess                   | bool   | 是    | 是否调用成功    |
| data                        | object | 否    | 业务数据      |
| &nbsp;&nbsp; &nbsp;id       | int    | 是    | rms系统任务id |
| &nbsp;&nbsp; &nbsp;taskType | int    | 是    | 任务类型,1-接料 2-送料     |
| message                     | string | 是    | 错误说明      |

**示例响应**:

```json
{
    "status": 0,
    "isSuccess": true,
    "data": [{
	    "id": 1,
	    "taskType": 1
    },{
	    "id": 2,
	    "taskType": 2
    }],
    "message": "success"
}
```

# 2.任务取消接口
## 2.1 按id取消

**接口地址**：http://ip:8200/api/Job/cancelJob/{id}

**请求方式**：post

**请求数据类型**：url path param

**响应数据类型**：application/json

**请求参数**：

| 参数名称 | 类型    | 是否必须 | 说明        |
| ---- | ----- | ---- | --------- |
| id   | url参数 | 是    | rms系统任务id |

**响应参数**：

| 参数名称      | 类型     | 是否必须 | 说明        |
|-----------|--------| ---- | --------- |
| status    | int    | 是    | 0或200表示成功 |
| isSuccess | bool   | 是    | 是否调用成功    |
| data      | object | 否    | 业务数据      |
| message   | string | 是    | 错误说明      |

**示例响应**:

```json
{
    "status": 0,
    "isSuccess": true,
    "data": null,
    "message": "success"
}
```