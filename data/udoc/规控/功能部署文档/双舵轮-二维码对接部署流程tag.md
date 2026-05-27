---
title: 二维码对接部署流程
description: 
published: true
date: 2025-12-17T11:38:26.406Z
tags: tagomni, 部署说明, 对接, 二维码
editor: markdown
dateCreated: 2025-06-11T07:24:46.104Z
---

# 二维码对接部署流程
  
| 文件名称 | 二维码对接部署流程  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 保密（部门内部公开） |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2025-06-10 | caopan  | tag omni | 部署流程说明 |
二维码对接功能部署流程大体如下

![画板](https://cdn.nlark.com/yuque/0/2025/jpeg/57535152/1749606678422-c3ca6d0f-bb68-4401-afcc-951423564c03.jpeg)

# 1.二维码粘贴
尽量保证二维码位于相机中心，二维码位于相机视野边缘容易出现畸变，影响识别结果。

# 2.修改相机参数
这里列一些简单步骤，详细参数说明见相机相关说明文档。

配置相机参数，包括相机外参，内参。

相机外参位于/usr/local/urobot/jarvis/share/omni_bot/param/visual_docking文件夹下的<span style="background-color:#FCE75A;">settings.yaml</span>中，这部分一般不会修改，如果有需求，可以联系研发

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749607689165-4dcac259-aae1-473f-aec1-987f31599c8a.png)

相机内参在更换相机时需要修改，首先找到位于/usr/local/urobot/jarvis/share/omni_bot/param/visual_docking文件夹下的camera.yaml中，里面会定义不同相机的端口等参数

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749607783418-cfc393f9-9b22-495f-8682-56d148b96376.png)

通过上述文件的camera_info可以找到具体对应的内参，如下图

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749607842852-5a0e6343-3ab3-4023-a59f-e05179d88ed6.png)

# 3.二维码参数
二维码参数在/usr/local/urobot/jarvis/share/omni_bot/param/visual_docking文件夹下的tags.yaml中,一般也不需要修改，只需要在对接失败时检查有没有配置对应的名字，没有的话找研发确认

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749607915952-52f397d2-38e4-4793-8d29-25f9edcf76f2.png)

# 4.测试是否部署生效
可以通过手动执行命令行，测试相机是否能识别二维码，具体步骤如下

+ 手动将机器人推到二维码带上，大致保证对应相机可以看到码带。
+ 在终端输入如下指令rostopic pub -r 1 /opts std_msgs/String "data: '"cam0@bundle0"'"。其中的cam0和bundle0是对应的相机名称和二维码带的名称
+ 等待几秒钟后，执行ctrl-c
+ 执行rostopic echo /pose_in_tag 看有没有输出结果

# 5.部署routes
具体的routes参数含义见二维码对接参数说明文档，这里只是进行举例，不做详细参数解释

如下图机器人向前行走，一般二维码带都是起点为坐标（0，0）点，前进方向为x轴，向左为y轴

![](https://cdn.nlark.com/yuque/0/2025/png/57535152/1749608595250-dda1a2ee-63a7-4ca4-a1f6-79ed89b4f374.png)

```json
"a1": 
{
"cmd": "tag_omni",//对接用到的指令
"use_robot_center": true,
"odom_dis": 0,//当全程都能看到二维码，则该值为0
"offset_x": 500, //最终停车的x位置           
"offset_y": 0,//最终停车的y位置
"offset_t": 0, //最终停车的角度，前对接是0度左右           
"sensor_name": "cam0",//识别二维码的相机的编号
"bundle_name": "bundle0",//二维码编号，一般出厂前配好，有问题可以咨询研发
"sensor_name_check": "cam0",//默认和sensor_name相同
"bundle_name_check": "bundle0"//默认和bundle_name相同
},	
```