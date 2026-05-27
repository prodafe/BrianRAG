---
title: tagzodom部署
description: 
published: true
date: 2026-02-24T06:54:59.805Z
tags: tag, 公开
editor: markdown
dateCreated: 2025-06-24T06:57:08.679Z
---

# tagzodom部署
  
| 文件名称 | tagzodom部署         |
| -------- | -------------------- |
| 部门     | 软件算法部           |
| 版本     | 1.0                  |
| 密级     | 公开 |


## 修改记录

| 版本号 | 修改日期   | 修改人   | 概述         | 详细说明 |
| ------ | ---------- | -------- | ------------ | -------- |
| 1.0    | 2025-06-18 | aldnoeas | tagzodom部署 | 简单介绍了tagzodom部署流程和相关模板     |

## 一、概述
该文件描述了tagzodom功能的部署流程和基础模板。tagzodom通常用于到点或对接反光板后，通过二维码进行位置微调并校验。与checkpose的差别是tagzodom是在大码对接时就进行二维码对接，能够一定程度上调整横向误差。

## 二、基本流程
1. 将[docking_cam.sh](/规控/file/docking_cam.sh)和[q2e.py](/规控/file/q2e.py)传入机器人，且这两个文件需要在同一目录下
2. 使用命令赋予两个脚本权限：
```sudo chmod +x docking_cam.sh q2e.py```
3. 修改docking_cam.sh中的相机名和bundle名，cam_name和相机朝向基本遵循以下规则：cam0 向前，cam1 向上，cam2 向左，cam3 向右，cam4 向后，cam5 向下。bundle_name是二维码名，在/usr/local/urobot/jarvis/share/bot600/param/visual_docking/tags.yaml文件中配置
1. 前往文件所在目录，执行脚本：./docking_cam.sh
2. 将所得数据分别填入routes中的distance,offset,angleRobotdiff

## 三、基础模板
**注意**：一个routes的参数可以写在task.json中，也可以写在routes中。当一个参数是不同机台或料架就不一样的情况下，需要写在routes.json中。如果所有机台和料架都是一样的值，那么就可以写在task.json中。当两个文件都有这个参数的时候，以routes.json为准。
```
task.json:{
    "tagzodom":{
        "distance" : 5,             //二维码相对于车的前后偏移，通常由脚本直接读出
        "offset" : 0.0,             //二维码相对于车的左右偏移，通常由脚本直接读出
        "angleRobotdiff" : 0.180,   //二维码相对于车的角度偏移，通常由脚本直接读出
        "speed" : 50,               //对接速度
        "max_angle": 5,             //机器人对接转动的最大角度
        "max_length": 300,          //机器人对接对接运行的最长距离
        "running_direction": "back",//车辆y调整时的方向 ，可选front 、back、front+back
        "camName": "cam3",          //校验时所用的传感器名称，通常为相机cam
        "bundleName": "bundle0",    //检验时所用的bundle名
        "max_err": 160,             //第一次对接后允许的y方向上误差，可以设置得大一些
        "max_err_check": 5,         //判定对接成功的y方向误差，根据实际误差要求来
        "max_secs" : 100,           //最长对接时间
        "is_check": true,           //是否使用二维码校验位置，默认为false
        "is_check_ID":false,        //是否校验二维码id
        "ID_from_rms":true,         //id信息是否来之rms系统，当true时，忽略本地写的ID和resdID参数，而是用调度系统发来的信息
        "ID":"1",                   //二维码id,默认为空
        "readID":false              //是否读id，为true时，不再根据本地信息校验ID，而是读取ID后并上报Rms
        "note" : 1                  //当note为-1时，任务不可被rms取消
    }
    
}
routes.json:{
    a:{
        "cmd" : "tagzodom",
        "distance" : 5,             //需要根据脚本读出的参数修改
        "offset" : 0.0,             //需要根据脚本读出的参数修改
        "angleRobotdiff" : 0.180,   //需要根据脚本读出的参数修改
        "note" : 1,         
        "speed" : 50,
        "max_angle": 5,
        "max_length": 300,
        "running_direction": "back",
        "camName": "cam3",          //需要根据实际情况修改参数
        "bundleName": "bundle0",    //需要根据实际情况修改参数
        "max_err": 160,
        "max_err_check": 5,
        "max_secs" : 100,  
        "is_check": true,       
        "is_check_ID":false,        //需要根据实际情况修改参数
        "ID_from_rms":true,         //需要根据实际情况修改参数
        "ID":"1",                   //需要根据实际情况修改参数
        "readID":false              //需要根据实际情况修改参数
    }
}

```


## 四、返回值
0：zodom后误差过大，或者到最后未获得相机数据，可能是里程计误差过大，相机识别误差，参数不合适，打滑等导致，可再次zodom或者检查其他参数时候正确
1：正常
2：二维码id错误
3：一开始就未获得定位结果，一般出现在开不到标志物的情况