---
title: 叉车Routes路径以及通用指令说明
description: 
published: true
date: 2025-12-17T11:48:08.738Z
tags: 部署说明, 公开, 叉车
editor: markdown
dateCreated: 2025-06-26T02:57:18.968Z
---

# 叉车Routes路径以及通用指令说明
本文讨论了玖物叉车路径系统及通用指令说明，包括路径书写格式、模板路径特点和多种指令的作用、参数等，还提及非叉车机器人用法及注意事项。关键要点包括：
1. 路径系统书写格式：路径主要在Path.json文件书写，每个路径有名称，含多个步骤，步骤有指令。指令以大写字母开头，参数关键字小写。接料、送料等路径有特定结尾。
2. 模板路径系统特点：同类型设备路径执行步骤大致相同，编号开头相同，地图编号与设备编号相同，按特定格式书写。
3. 常用指令说明：Goto命令机器人到目标点；Route导航并做动作，可控制货叉多种动作；CommonArrived/CommonFinished通知设备到达或离开；还有Storage相关指令用于库位操作等。
4. 其他指令功能：Sound让机器人播放音乐，SetDo设置机器人输出IO，CheckIO检查IO等，各有对应参数。
5. 非叉车机器人用法：通过特定格式如$ Check|groupName/PortId|变量名|值 等进行操作，不同指令有不同格式要求。
6. 自定义指令要点：xxxArrived属于自定义指令，目标点一般是target，不同现场可能有不同自定义指令，开发需与售后沟通。 


| 版本    |   编撰人   | 编辑日期     | 备注         | 
| -------| --------- | ------------| -----------   | 
| 初稿   |杨鑫磊      | 2023/08/02  |               | 
|        |           |             |                |
## 一.路径系统说明
路径主要在Path.json这个文件里书写,主要格式如下:
```json
{
  
    "P001-G": {
      "a": {
        "cmd": "Goto",
        "goal": "LM62",
        "coordinate": [1.0,22.1,9.0]
      },
      "a1": {
        "cmd": "Arrived",
        "target": "P001"
      },
      "a2": {
        "cmd": "Navi",
        "params": {
          "id": "AP68",
          "source_id": "LM62",
          "operation": "ForkLoad",
          "start_height": 0.1,
          "end_height": 1.0
        }


      },
      "a3": {
        "cmd": "Route",
        "goal": "AP68"
      },
      "a4": {
        "cmd": "Finished",
        "target": "P001"
      }
    }

  
}  
```
![图1.png](/RCS/叉车Routes路径以及通用指令说明/图1.png) 

每个路径有一个名称，例如上面的  P001, 每个路径下面有N个步骤，步骤按照序号来 例如a0-a4，每个步骤有一个指令，具体详细的指令后面会介绍。  
整体格式如下: 

注意以下：
- 所有的指令必须以大写字母开头，第二个单词也是大写字母开头。
- 指令类的参数的关键字都是小写的。
- 接料的路径以 -G结尾，送料的 -P，充电的以-C结尾，停车的以-T，例如上面的P001-G就是去P001目标点接料，如果是送料就是P001-P，如果是充电就是P001-C 如果是停车点就是P001-T。
- 为了防错 尤其是叉车在接料的时候，最后判断下车上有没有物料，可以在接料的第一步 a 是 CheckIO 或者 CheckHeight 。
## 二.模板路径系统说明
由于每个目标点都需要一个接和送的路径，所以路径会写很多，为了方便路径系统的写法，提供了模板路径系统，模板路径比较简单，需要遵守以下几个特点：
- 同一种类型的设备路径执行步骤大致相同，例如玻璃机，取料都是到目标点取料，抬升，然后离开。
- 同一种类型的设备编号开头必须相同，例如 玻璃机都是以BL开头这样。
- 图上的LM AP编号，必须和设备的编号相同，例如 BL001 的前置点是 LM001，接料位置点必须是  AP001。
遵循以上步骤后，那么模板的路径的写法如下：
```json
{
  
    "$BL-G": {
      "a": {
        "cmd": "Goto",
        "goal": "LM$"      
        },
      "a1": {
        "cmd": "Arrived",
        "target": "P$"
      },
      "a2": {
        "cmd": "Route",
        "goal": "AP$"
      },
      "a4": {
        "cmd": "Finished",
        "target": "BL$"
      }
    }

  
}
```
## 二. 指令说明
### Goto指令
- 作用: 命令机器人从当前位置去某个目标点。
- 发送目标：调度服务器。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | Goto   |
|goal    |string    |前往的目标点| √      |地图上的站点或者路径等 |
|coordinate|float[] |目标点坐标|          |地图上点的坐标，主要是x,y,angle |
```json
"a": {
      "cmd": "Route",
      "goal": "LM23"
}
```
## Route指令
- 作用: 机器人导航并做动作。
- 发送目标：调度服务器。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | Route   |
|params  |string    |参数指示，下面的数据为参数可选值，具体参看下面。| √ | |
|id   |string |前往的目标点| √ |地图上的站点或者路径等 |
|operation|string |到达目标点后需要做的叉车动作| √ |具体参考仙工文档 |
|start_height|float |货叉起步前的举升高度|    |      |
|end_height  |float |货叉到点后的举升高度|    |      |
|begin_operation|string |离开当前目标点后叉的动作，会在第一段路作为“operation”参数传给车|    |      |
|begin_end_height|float |与“begin_operation”配合使用。效果与end_height类似    | | |
|begin_start_height|float|与“begin_operation”配合使用。效果与start_height类似|  | |
例如下面的路径:
```json
{
 "cmd": "route",
  "param":{
  "id": "LM1",
  "operation": "ForkLoad",
  "start_height": 0.1,
  "end_height": 0.5,
  "begin_operation":"ForkHeight",
  "begin_end_height":0.2
  }
 ```
控制货叉设备的动作，支持的动作：
- ForkLoad（货叉加载货物，会将叉车状态变成载货中）
- ForkUnload(货叉卸载货物，会将叉车的状态变成非载货中)
- ForkHeight(货叉顶高)
- ForkForward(货叉前移）
- Wait(不做动作)

以上面的请求为例，假设任务分派给Fork1,Fork1当前点位LM4，目标点位是LM1   路径为LM4-LM3-LM2-LM1。那么他会执行如下步骤，到LM4起步前高度升为0.1，到LM3高度升为0.2,到 LM1高度升为0.5。
## CommonArrived/CommonFinished指令
- 作用: 通知设备到达或者通知设备离开，除了做通知到达请求，离开请求，有些设备也可以直接作为完成通知，等对方回复收到后，回复收到再离开。可以灵活理解和运用。
- 发送目标：机器设备。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | CommonArrived/CommonFinished   |
|target  |string    |料口的编号| √ | |
|noticeValue |string |通知值|  |默认是 true 或者1 ，根据变量的请求、请求离开进入的数据类型来，非必须的可以不写 |
|checkValue|string |检查设备值|  |默认是 true 或者1 ，根据变量的允许进入、允许离开 的数据类型来的，非必须的可以不写 |
```json
"a1": {
      "cmd": "Arrived",
      "target": "P002",
      "noticeValue":"1",
       "CheckValue":"1"
    }
```
## SimpleArrived/SimpleFinished指令
- 作用: 通知调度任务开始对接  /通知调度任务完成。
- 发送目标：机器设备。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | SimpleArrived/SimpleFinished|
|target  |string    |料口的编号| √ | |
```json
"a1": {
      "cmd": "SimpleArrived", //或者SimpleFinished
      "target": "P002",
       }
```
## StorageArrived指令
- 作用: 到库位前后，需要发的目标信息。
- 发送目标：机器设备。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | StorageArrived   |
|target  |string    |具体库位编号| √ | |
|params  |string    | | √ | |
|id   |string |具体库位名称| √ |  |
|source_id|string |站前点名称|√ |      |
|operation|string |ForkLoad叉举动作| √ |  |
|start_height  |float |叉举前高度|  √   |      |
|end_height  |float |到目标点叉举的高度|  √   |      |
```json
  "a1": {
      "cmd": "StorageArrived",
      "target": "P002",
      "params":{
        "id": "LM1",
         "operation": "ForkLoad",
         "start_height": 0.1,
          "end_height": 0.5,
          "operation":"ForkLoad" 
      }
    }
```
## StorageFinished指令
- 作用: 叉举完成退出库位，更新库位。
- 发送目标：机器设备。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | StorageFinished|
|target  |string    |库位前站点| √ | |
```json
"a1": {
      "cmd": "StorageFinished",
      "target": "P002"
    }
```
## StorageArrivedDirect指令
- 作用: 直接到单点库位，不需要动态计算位置，直接到目标点，一般用于只有一个容量的库位。
- 发送目标：机器设备。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | StorageArrivedDirect   |
|target  |string    |具体库位编号| √ | |
|params  |string    | | √ | |
|id   |string |具体库位名称| √ |  |
|source_id|string |站前点名称|√ |      |
|operation|string |ForkLoad叉举动作| √ |  |
|start_height  |float |叉举前高度|  √   |      |
|end_height  |float |到目标点叉举的高度|  √   |      |
```json
  "a1": {
      "cmd": "StorageArrivedDirect",
      "target": "P002",
      "params":{
        "id": "LM1",
         "operation": "ForkLoad",
         "start_height": 0.1,
          "end_height": 0.5,
          "operation":"ForkLoad" 
      }
    }
```
 ## StorageFinishedDirect指令
- 作用: 叉举完成退出库位，更新库位，不需要动态计算位置，一般用于只有一个容量的库位。
- 发送目标：机器设备。
- 指令参数具体如下： 

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | StorageFinishedDirect|
|target  |string    |库位前站点| √ | |

```json
"a1": {
      "cmd": "StorageFinishedDirect",
      "target": "P002"
    }
```
## Sound指令
- 作用: 让机器人播放音乐。
- 发送目标：AGV本体
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | Sound|
|name  |string    |需要播放的音频文件名(不含文件扩展名)| √ | |
|loop|boolean|是否循环播放(true = 循环, false = 不循环,如果缺省则默认不循环)| | 缺省值 false|
```json
 "a1": {
      "cmd": "Sound",
      "name": "shehuizhuyihao",
       "loop": "true"
    }
```
## StopAudio指令
- 作用: 让机器人播放音乐。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | StopAudio|
```json
"a1":
 {
  "cmd": "StopAudio"
  }
```
## SetDo指令
- 作用: 设置机器人输出IO。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | SetDo   |
|params  |string    | 指令参数| √ | |
|id   |int |IO序号| √ |  |
|status  |boolean    |设置的值| √ | true/false|
```json
"a1": {
    "cmd": "SetDo",
    "params":[
  {"id":0,"status":true},
  {"id":1,"status":true},
  {"id":2,"status":false},
  {"id":3,"status":false}]
}
```
## CheckIO指令
- 作用: 检查机器人IO是否正确。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | CheckIO   |
|params  |string    | 指令参数| √ | |
|id   |int |IO序号| √ |  |
|status  |boolean    |设置的值| √ | true/false|
```json
"a1": {
    "cmd": "CheckIO",
    "params":[
  {"id":0,"status":true},
  {"id":1,"status":true},
  {"id":2,"status":false},
  {"id":3,"status":false}]
}
```
## SetHeight指令
- 作用: 设置叉车高度。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | SetHeight   |
|height  |string    | 指令参数| √ | |
```json
"a1": 
{
  "cmd": "SetHeight",
  "height":0.5
  }
``` 
## CheckHeight指令
- 作用:检查叉车高度， 小于(<) 大于(>)  大于等于(>=)   小于等于(<=)   不等于(!=)。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | CheckHeight   |
|expression  |string    | 表达式| √ | |
注意：
- 由于高度是浮点数目，但是计算机上即使两个一模一样的浮点数目，也不能相等，例如都是变量a=0.01 变量 b =0.01，但是a==b 是false，所以叉车的实际高度是0.75 表达是x==0.75永远都是false，所以高度校验最好不要用==，也不能是<=0.75,可以但是<=0.751是成立的，具体参考计算机浮点数。
- 同理大于>=也是一样的，最后给叉车显示的实际高度后面多一个1，例如0.75就是写0.751，如果是大于某个高度，例如大于0.5，叉车实际高度是0.5，那么表达应该是>0.4999这样，给出一个0.001的误差，千分之一的误差值。
- 如果需要等于的话，可以这么写 给一个范围值例如要让高度在等于0.05 那么 可以写 "expression":"x<0.051&& x >0.04999" 这样来做等于的判断。
```json
"a1": 
{
"cmd": "CheckHeight",
"expression":"x<0.5"
  }
``` 
## ChangeMap指令
- 作用: 切换地图。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | ChangeMap   |
|mapName  |string    | 地图名称| √ | |
```json
 "a1":{
     "cmd":"ChangeMap",
      "mapName":"middle"
}
```
## Waiting指令
- 作用: 让机器人等待，等待某个点的任务到达什么状态，或者等待多长时间。
- 发送目标：AGV本体。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|cmd     |string    | 指令名称 | √        | Waiting   |
|type|int| 指令参数| √ | 等待时间 单位ms 0 表示等多长时间 ，1，表示 等待任务|
```json
//等待任务类型
"a1":{
     "cmd":"Waiting",
      "type":1 ,
       "params":{
        "taskType":1, //1接料 2 送料，
        "target":"料口或者库位编号",
        "Status":"任务状态",// 0未分配 10 已经分配，30 已经执行 60对接中 70 正在传送 80 已经完成
       }
}
```
```json
//等待多长时间
"a1":{
     "cmd":"Waiting",
      "type":0 ,
       "params":{
        "time":100,
       }
}
```
## Check
- 作用: 检查某个寄存器的值是否正确。
- 发送目标：设备地址。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|GroupName     |string    | 设备组id 或者料口id | √  |    |
|VariableName  |string    | 变量名称| √ | 多个变量用逗号隔开|
|Values  |string    | 要对比的数值| √ |对应的值和变量一样，用逗号隔开 |
```json
"a2": {
  "cmd": "Check",
  "request": {
    "GroupName": "T001",
    "VariableName": "V1,V3",
    "Values": "1,2"
  }
}
```
### 玖物非叉车机器人用法 
玖物的（非叉车）用法  $ Check|groupName/PortId|变量名|值。
```json
//例如小车可以发送
"$Check|T001|V1,V3|1,2"
```
## SingleWrite
- 作用: 给设备单个寄存器写值。
- 发送目标：设备地址。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|GroupName     |string    | 设备组名称或者料口id | √  |    |
|VariableName  |string    | 变量名称| √ | |
|Values  |string    | 要写入的值| √ ||
```json
"a2":{
  "cmd": "SingleWrite",
  "request": {
    "GroupName": "T001",
    "VariableName": "V1",
    "Values": "113"
}
```
### 玖物非叉车机器人用法  
玖物的（非叉车）用法  $ SingleWrite|groupName/PortId|变量名|值
```json
//例如小车可以发送
"$SingleWrite|T001|V1|113"
```
## MultiWrite
- 作用: 给多个寄存器写值。
- 发送目标：设备地址。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|GroupName     |string    | 变量组名称或者料口id | √  |    |
|VariableName  |string    | 变量名称| √ | 多个变量名用逗号隔开|
|Values  |string    | 要写入的值| √ |多个值用变量隔开|

```json
"a3": {
  "cmd": "MultiWrite",
  "request": {
    "GroupName": "T001",
    "VariableId": "V1,V3",
    "Values": "1,2"
  }
}
```
### 玖物非叉车机器人用法  
玖物的（非叉车）用法  $ MultiWrite|groupName/PortId|变量名|值
```json
//例如小车可以发送
"$MultiWrite|T001|V1,V2|1,2"
```
## WriteCheck
- 作用: 给多个寄存器写值。
- 发送目标：设备地址。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|GroupName     |string    | 变量组名称或者料口id | √  |    |
|VariableName  |string    | 变量名称| √ | 多个变量名用逗号隔开|
|Values  |string    | 要写入的值| √ |多个值用变量隔开|
```json
"a3": {
  "cmd": "WriteCheck",
  "request": {
    "GroupName": "T001",
    "VariableName": "V1,V3", //注意先是写的地址，然后是读的地址
    "Values": "1,2"   //先是写的值，然后读检测是否等于的值
  }
}
```
### 玖物非叉车机器人用法  
玖物的（非叉车）用法  $ WriteCheck|groupName/PortId|变量名|值
```json
//例如小车可以发送
"$WriteCheck|T001|V1,V2|1,2"
```
## KeepRead
- 作用: 读取设备当前值保存到机器人中，用于给设备传递信息。
- 发送目标：设备地址。
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|GroupName     |string    | 变量组名称或者料口id | √  |    |
|VariableName  |string    | 变量名称| √ | 多个变量名用逗号隔开|
|Values  |string    | 特征名称| √ |例如从A寄存器读的值保存到机器人包号名称是 叫Material里的里这个最好唯一|
|ExtraInfo     |string    | 表示读取的长度 |   |    |
```json
"a4": {
  "cmd": "KeepRead",
  "request": {
    "GroupName": "T001",
    "VariableName": "V1,V3",
    "Values": "info",
    "ExtraInfo": "2"
  }
}
```
### 玖物非叉车机器人用法  
玖物的（非叉车）用法  $ KeepRead|groupName/PortId|变量名|值|额外信息
```json
//例如小车可以发送
"$KeepRead|T001|V1,V2|info|2"
```
## KeepWrite
- 作用: 将保存在机器人包号里的信息写到设备中
- 发送目标：设备地址
- 指令参数具体如下：

| **字段**| **类型** | **说明** | **必须** |**说明** |
| -------|--------- | --------| ---------|--------|
|GroupName     |string    | 变量组名称或者料口id | √  |    |
|VariableName  |string    | 变量名称| √ | 多个变量名用逗号隔开|
|Values  |string    | 特征名称| √ |例如从A寄存器读的值保存到机器人包号名称是 叫Material里的里这个最好唯一|
```json
"a4": {
  "cmd": "KeepWrite",
  "request": {
    "GroupName": "T001",
    "VariableName": "V1",
    "Values": "info"
  }
}
```
### 玖物非叉车机器人用法  
玖物的（非叉车）用法  $ KeepWrite|groupName/PortId|变量名|值|额外信息
```json
//例如小车可以发送
"$KeepWrite|T001|V1,V2|info"
```
注意事项：
- 1.凡是 xxxArrived的属于自定义指令，自定义指令的目标点一般都是 target。
- 2.每个现场根据需要不同，可能有不同的自定义指令，所以不同的现场，有特殊指令时候，开发人员需要跟售后人员讲清楚。





