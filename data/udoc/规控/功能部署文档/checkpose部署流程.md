---
title: checkpose部署流程
description: 
published: true
date: 2025-12-17T11:27:14.490Z
tags: 公开, 参数说明, checkpose
editor: markdown
dateCreated: 2025-07-03T05:35:15.583Z
---

# checkpose部署流程

| 文件名称 | checkpose部署流程 |
| -------- | -------------- |
| 部门     | 软件算法部     |
| 版本     | 1.0            |
| 密级     | 公开           |

## 修改记录

| 版本号 | 修改日期   | 修改人        | 概述                               | 详细说明                                 |
| ------ | ---------- | ------------- | ---------------------------------- | ---------------------------------------- |
| 1.0    | 2025-07-03 | 陆志辉        | checkpose部署流程                     | 描述checkpose的使用模板和部署流程                           |

---

## 一、概述
该文件描述了机器人使用checkpose常用的模板和部署流程。

## 二、功能介绍
对接标志物的功能，使用时需要配置相机参数，之后便可以正常对接。
通常用于顶起料架后与rms确认料架是否正确。防止现场人员随意更改料车位置导致错料。  
不调整横向误差，只使用标志物调整一下机器人最终的位置及角度，可校验横向偏差和ID。  
**注意**:checkpose通常仅支持x方向和角度的调整，如果需要调整y方向偏移，推荐使用tagzodom

## 三、参数说明
**注意**：一个routes的参数可以写在task.json中，也可以写在routes中。当一个参数是不同机台或料架就不一样的情况下，需要写在routes.json中。如果所有机台和料架都是一样的值，那么就可以写在task.json中。当两个文件都有这个参数的时候，以routes.json为准。
```
task.json:{
    "checkpose":{
        "camName_check":"cam1",         //小码校验时所用的传感器名称，通常为相机cam
        "bundleName_check":"bundle4",   //小码检验时所用的bundle名
        "distance_check":700,;          //小码校验时，二维码相对于车的前后偏移
        "offset_check":-0,              //小码校验时，小码二维码相对于机器人中心的左右偏移，左正右负
        "angleRobotdiff_check": 0,      // 小码校验时，机器人角度在二维码下的角度
        "max_err_check": 10,            //y方向上的最大误差
        "max_err_x": 4,                 //x方向上的最大误差
        "max_err_th": 0.5,              //角度的最大误差
        "is_check_ID": false,           //是否校验二维码id
        "ID_from_rms": false,           //id信息是否来之rms系统，当true时，忽略本地写的ID和resdID参数，而是用调度系统发来的信息
        "ID": "",                       //二维码id,默认为空
        "readID": false,                //是否读id，为true时，不再根据本地信息校验ID，而是读取ID后并上报Rms
        "is_check_pose":true            //是否运行到位时根据位姿调整x和角度
    }
    
}
routes.json:{
    a:{
        "cmd": "checkPose",
        "distance_check": 0,
        "offset_check": 0,
        "angleRobotdiff_check": 90,
        "is_check_pose": true,
        "ID": "22",
        "readID": false,
        "is_check_ID": false
    }
}

```

## 四、返回值
0：看到码但是调整后误差过大，或中途看不到码  
1：正常  
2：二维码id错误  
3：一开始就没有看到标志物  