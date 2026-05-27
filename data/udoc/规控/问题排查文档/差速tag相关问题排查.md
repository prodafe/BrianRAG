---
title: tag问题排查
description: tag问题排查
published: true
date: 2026-02-24T06:52:28.508Z
tags: 公开, 差速
editor: markdown
dateCreated: 2025-06-23T08:19:09.173Z
---

# tag问题排查
  
| 文件名称 | tag问题排查          |
| -------- | -------------------- |
| 部门     | 软件算法部           |
| 版本     | 1.0                  |
| 密级     | 公开 |


## 修改记录

| 版本号 | 修改日期   | 修改人   | 概述        | 详细说明 |
| ------ | ---------- | -------- | ----------- | -------- |
| 1.0    | 2025-06-24 | aldnoeas | tag问题排查 | 介绍了使用tag时遇到问题该如何定位问题 |

## 一、概述
该文件描述了机器人在tag时可能遇到的各种问题以及排查方法。

## 二、基本
二维码对接分为两个阶段，大码对接和小码校验。大码是指前一阶段的标识物，而不是指二维码，例如腿对接中的料腿，直线对接中的直线。小码通常是指二维码。
如果下面排查参考未能解决问题，寻找开发人员请下载logs/bz_robot.log,log/log-xxxx.log,log/error/ref_bag中对应任务的bag包以及对应对接方式的日志文件。

## 三、日志文件
下发日志多数为没有数字为最新日志，然后0-10，数字越大，时间越远。下载日志需要根据对应时间下载对应日志。
|日志名|路径|作用|
| - | - | - | - |
|log-xxxx.log|/usr/local/urobot/log|jarvis-g的日志，用于查看任务报错情况和对接中的误差情况|
|bz_robot.log|/usr/local/urobot/logs|bz的日志，用于查看机器人在对接过程中的控制问题，通常不需要|
|xxx-xxx.bag|/usr/local/urobot/log/error/ref_bag|对接过程中的数据包，命名格式为ref/tag-任务号.bag。基本都需要，出问题需要第一时间下载数据包，不然会被覆盖。|
|leg_loc.log|/usr/local/urobot/logs|腿对接日志|
|tag.log|/usr/local/urobot/logs|相机对接二维码日志|
|line.log|/usr/local/urobot/logs|正向直线对接日志|
|side.log|/usr/local/urobot/logs|侧向直线对接日志|

## 四、参数检查
遇到任何问题，优先排查routes和task.json中的参数是否存在异常（参数名是否正确，数据类型和参数是否对应），常用参数如下：
| 参数               | 数据类型 | 默认值    | 说明                                                                          |
| ------------------ | -------- | --------- | ----------------------------------------------------------------------------- |
| "camName"          | string   | "cam0"    | 大码对接使用传感器，一般是/front/scan                                         |
| "camName_check"    | string   | "cam0"    | 小码对接使用传感器，一般是对应方向相机                                        |
| "bundleName"       | string   | "bundle0" | 大码对接使用的配置参数，根据实际配置文件来，如果是侧向对接就是"left"和"right" |
| "bundleName_check" | string   | "bundle4" | 小码对接使用的配置参数，通常根据tags.yaml配置                                 |
| "distance"         | double   | 700       | 大码坐标系下的停车位置，具体参考部署文档，**参数无引号**                      |
| "offset"           | double   | 0         | 大码坐标系下的左右偏移，具体参考部署文档，**参数无引号**                      |
| "distance_check"   | double   | 700       | 小码坐标系下的停车位置，具体参考部署文档，**参数无引号**                      |
| "offset_check"     | double   | 0         | 小码坐标系下的左右偏移，具体参考部署文档，**参数无引号**                      |

## 五、任务开始后车不走
### 通用检查
配置文件基础位置为/usr/local/urobot/jarvis/share/项目名
| 对接方法     | launch/bringup.launch对应参数   | 配置文件位置                 | 详细配置文档地址                                                                                          | 
| ------------ | ------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------- |
| 腿对接       | jarvis_leg_loc_enable           | param/leg_localization.yaml  | [料腿对接文档](https://p10j68f02n.feishu.cn/docx/VwNwde131ocWGtx6RDwcf6gYndu?from=from_copylink)          |
| 直线正向对接 | jarvis_line_localization_enable | param/line_localization.yaml | [直线正向对接部署配置 ](https://p10j68f02n.feishu.cn/docx/YyI7dP5l0oHkL4xxrzCcABdun9e?from=from_copylink) |
| 直线侧向对接 | jarvis_side_localization_enable | param/side_localization.yaml | [直线侧向对接部署配置](https://p10j68f02n.feishu.cn/docx/Q2t0dMstLogBKGxuwkqcLRT9n8d?from=from_copylink)  |


```kroki
mermaid

graph TD
  A[开始任务] -->|客户端输入 rostopic echo /pose_in_tag| B{查看 /pose_in_tag 有无数据}
  B -->|有数据| C[客户端输入 rostopic echo /jvel]
  B -->|没数据| D[客户端输入 pgrep  locali -l]
  C -->|有速度| E[客户端输入 rostopic echo /jodom，观察有无速度并联系下位机排查]
  C -->|没速度| F[检查机器人是否避障，是否下使能。如果正常则下载logs/bz_robot.log和log/log-xxxx.log给上位机开发排查]
  D -->|有进程| G[没有找到标志物，请根据下面内容排查]
  D -->|没进程| H[检查对应配置文件格式是否正确]
  E --> I[都不行，下载日志文件，bringup.launch和配置文件给开发排查]
  F --> I
  G --> I
  H --> I
```

### 腿对接检查
1. 检查当前运行的routes里面，bundle_name配置的名字是否对应的是此料车，同时货架腿的信息已经正常配置到了leg_localization.yaml文件中
2. jarvis_leg_loc.launch中配置的是否使用反光板的参数是否和实际一致？如果是采用反光板辅助对接，确认反光板粘贴是否正常，
3. 重新测量腿的宽度和长度，腿之间的宽度，长度等信息，尤其是确认腿之间的宽度配置是否正常，注意此次的距离均为腿中心距，也可以使用左腿左侧到右腿左侧的距离，前腿前侧到后腿前侧的距离
4. 确定机器人激光处于料车前0.6—1m的距离，不要太远也不要太近
5. 反光板辅助的情况下确认反光板阈值配置是否正确

#### 激光数据检查
可以通过rviz命令查看对接过程中的匹配激光点，料车定位中心等信息，是非常好用的问题处理工具，需要大家灵活运用，运行以下命令：
```roscd leg_localization/rviz/```
进入腿对接的配置文件夹内，然后运行：
```rviz -d leg_loc.rviz```
会看到一个rviz的界面，这时候再运行对接的routes，就可以看到腿对接的过程和匹配的激光点，腿模板，定位坐标系，用于定位激光数据，用于检查是否腿尺寸是否和激光匹配，排查腿参数模板错误或者激光测距错误。
通过这个方式检查激光数据是由存在异常。  

### 正向直线检查
1. 配置信息是否正确，/launch/jarvis_line_localization.launch 中 config_path 是否配置为对应的配置文件
2. 激光强度阈值intensity_threshold 是否正确配置。
3. 查看日志/usr/local/urobot/logs/line.log 如果出现 shape length is wrong, cannot use0.478 ,可尝试修改对应配置文件中docker_length 的值，使它接近日志中的数值。注意修改完需重新启动服务。
### 侧向直线检查
1. 配置信息是否正确，/launch/jarvis_side_localization.launch 中 config_path 是否配置为对应的配置文件
2. 可能是边界距离配置不对，尝试修改1.2.2中的left_bound 和 right_bound。 修改后重启服务
## 六、对接过程中出错
### 腿对接
1. 进入料车时，走到一半停下，然后等待一段时间（约5s）后退出，报错为“运行过程中丢失定位结果，对接失败”
	1. 如果有反光板辅助定位，请确认后腿上按照要求正确粘贴了反光板，且激光看到反光板是正常的。
	2. 同时增加tag配置参数中distance和odom_dis的大小，增量相同，但是也不宜过大，odom_dis正常要小于（机器人前方长度+料车长度的一半）
	3. 重新测量腿的宽度长度，腿之间的宽度，长度等信息，尤其是确认腿之间的长度配置是否正常，注意此次的距离均为腿中心距，也可以使用左腿左侧到右腿左侧的距离，前腿前侧到后腿前侧的距离
	4. 查看日志，如果为========= POINTING====== 结束，========= APPROACHING====== 刚开始便出现ros::Time::now().toSec()相关打印，首先查看上线转正之后的激光数据是否正常，如果正常，则需要查看机器人旋转过程中的激光数据是否正常。
	5. 走到料车前不进入就后退，通常为后腿识别有问题
2. 同类型料车，个别车辆可以进入，个别车辆无法进入
	1. 同类型料车，进入部分料车正常，进入另一部分料车时，在门口不动
		1. 查看日确定任务失败的返回值是否为3，如果是3，确认料车是否需要反光板辅助对接，若是，请确认不可进入的料车是否有反光板，反光板粘贴位置是否正常，激光高度是否能看到反光板，也可重新粘贴并上下补充后再试
		2. 确定机器人激光处于料车前0.6—1m的距离，不要太远也不要太近。
3. 同类型料车，进入部分料车正常，进入另一部分料车时，走到一半停下，然后等待一段时间（约10s）后退出，按照第一点的方式处理

### 直线对接
直线对接，无论正向还是侧向，如果出现问题，先检查激光在对接过程中看到的反光板数据是否正常，看到的直线是否弯曲，如果出现明显异常数据，请找激光人员排查。
## 七、二维码阶段出错
1. 查看日志，找到对接过程中，由========= FINAL_ROTATE====== 切换到========= FINAL_MOVE_BACK======= 的地方，中间会写明失败原因，
2. 如“JActTag don't get cam pose for 2s,failed”代表长时间未得到相机数据，请检查二维码及相机状态; 
3. 如显示“id check  failed.check ID is :”X” ,but response is: “Y”，”则表示二维码id错误，请检查包号及识别结果是否准确；可修改id后继续或者直接将ID_from_rms为false，"readID"暂时设置成true进行测试，实车跑时，要将ID_from_rms设置为true，听从调度指令
4. 如显示“final rotate 到位失败，横向误差（）太大”，表示误差过大，重试即可，如多次重试均失败，请清理反光板及二维码，或者调整二维码位置，或者调整相机外参。