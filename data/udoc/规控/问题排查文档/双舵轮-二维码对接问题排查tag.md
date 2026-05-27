---
title: 二维码对接问题排查
description: 
published: true
date: 2025-12-17T11:06:46.555Z
tags: tagomni
editor: markdown
dateCreated: 2025-06-11T08:56:04.808Z
---

# 二维码对接部署流程
  
| 文件名称 | 二维码对接问题排查  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 保密（部门内部公开） |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2025-06-10 | caopan  | tag omni | 问题排查流程 |

## 1.机器人在起点附近没有移动，直接任务失败
第一步 如果是调度任务，结合任务号搜索到对应的对接任务，如果是手动执行，则直接看最后一个手动任务即可

第二步 在日志中搜索 deactivate ModeTag,找到mode切换的日志，查看二维码对接mode退出前返回值是多少

第三步 如果返回值是2，<span style="color:rgb(66, 66, 66);">表示刚开始对接就拿不到结果，需要检查routes当中用到的相机名称和二维码名称是否正确</span>

<span style="color:rgb(66, 66, 66);">第四步 利用</span><span style="color:#DF2A3F;">二维码对接部署流程</span><span style="color:rgb(66, 66, 66);">中的 第4部分 手动检查是否能输出结果</span>

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749627985986-7741eb16-b7d9-40ec-b29a-8aa63c76fcfa.png)

第五步 如果手动执行也没有结果，检查相机绑定，以及二维码配置

第六步 如果手动执行，有定位结果，大概率是增加了防止识别错机台的检测，可以在日志中搜索如下内容

"init pose ，error"，如果有对应内容，表示参数导致识别出的结果不满足需求，参数含义见<span style="color:#DF2A3F;">二维码对接参数说明中防错参数</span>

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749630841592-f823df5b-f7f3-4627-98ed-cf754532af63.png)

## 2.机器人对接到一半，开始后退
第一步 查找log日志，是否有 <span style="color:#DF2A3F;">"超过固定周期未拿到定位数据"</span> 的打印，如果有说明移动过程中看不到二维码了

## 3.对接到目标点，任务不结束，后退回起点或者直接报失败
检查机器人失败后退前的状态，在日志中搜索 "<span style="color:#DF2A3F;">JActTagOmni: state change</span>" ,可以得到机器人切换到后退前最后的状态，如

"JActTagOmni: state change: APPROACHING -> MOVE_BACK."

表示机器人是从前进状态切换到后退的。下面针对不同的切换流程排查问题

+ 如果日志中有 "<span style="color:#DF2A3F;">JActTagOmni: state change: APPROACHING -> MOVE_BACK</span>." 大概率是机器人最后误差大于配置文件中的设定值。在状态切换附近找到 "go arrive goal mMaxErr = 0.01",表示允许误差为0.01米。找到 "go arrive goal err_x=(%f) err_y=(%f) err_t=(%f)"，里面的 err_y为机器人最终的横向误差