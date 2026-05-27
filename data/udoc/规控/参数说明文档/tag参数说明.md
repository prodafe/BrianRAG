---
title: tag参数说明
description: 
published: true
date: 2026-02-24T06:56:32.050Z
tags: tag, 公开, 差速, 参数说明, 对接
editor: markdown
dateCreated: 2025-07-07T03:30:21.281Z
---

# tag参数说明

| 文件名称 | tag参数说明 |
| -------- | -------------- |
| 部门     | 软件算法部     |
| 版本     | 1.0            |
| 密级     | 公开           |

## 修改记录

| 版本号 | 修改日期   | 修改人        | 概述                               | 详细说明                                 |
| ------ | ---------- | ------------- | ---------------------------------- | ---------------------------------------- |
| 1.0    | 2025-07-08 | 陆志辉        | tag参数说明                     | 详细说明tag全部参数                           |

---

## 一、概述
该文档列举并说明了tag中所有相关参数并解释参数作用（安全相关参数不在其中）。

## 二、 基本对接参数
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
| online_distance_to_stop |  double  |   2000    |最短对接长度，机器人需要在该范围内才能够对接      |
|       online_dis        |  double  |    20     |起步先横移向中心线的阈值，如果小车对接要进入窄通道，就需要把值设置的很小，比如10mm，一般情况可以适度放大，以便减少对接动作      |
|        odom_dis         |  double  |     0     |使用里程计额外走的距离，通常用于靠近目标后激光精度不够的情况      |

### 第一步对接参数
**找腿，找直线阶段**
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|        distance         |  double  |    700    |第一步停车点，第一阶段机器人停下时在标志物坐标系下的x坐标，根据实际情况修改      |
|         offset          |  double  |     0     |实际第一步停车点的左右偏移      |
|     angleRobotdiff      |  double  |     0     |实际第一步停车点的角度偏移      |
|         camName         |  string  |  "cam0"   |第一步对接使用的传感器，通常为前激光话题/front_scan_filtered      |
|       bundleName        |  string  | "bundle0" |第一步对接使用的配置参数，根据具体情况配置      |

### 第二步对接参数
**二维码阶段**
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|     distance_check      |  double  |    700    |机器人在二维码坐标系下的停车前后位置      |
|      offset_check       |  double  |     0     |机器人在二维码坐标系下的停车左右位置      |
|  angleRobotdiff_check   |  double  |     0     |实际第二步停车点的角度偏移      |
|      camName_check      |  string  |  "cam0"   |第二步校验使用的传感器，通常为对应方向的相机      |
|    bundleName_check     |  string  | "bundle4" |第二步校验阶段使用的参数，通常为二维码的名称      |

## 三、 二维码id参数
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|           ID            |  string  |    ""     |二维码id      |
|         readID          |   bool   |   false   |设置为true后，不会校验二维码id，只会读取并上报     |
|       is_check_ID       |   bool   |   false   |是否校验二维码id      |
|       is_RMS_back       |   bool   |   false   |任务失败后退是否需要申请rms节点      |
|        is_check         |   bool   |   false   |是否使用二维码校验位置，设置false就不会在最后进行微调      |
|       ID_from_rms       |   bool   |   false   |是否从rms获取二维码id进行id校验      |

## 四、 对接配置参数
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|          speed          |  double  |    100    |对接速度      |
|       angle_speed       |  double  |    20     |对接角速度      |
|      anglePathdiff      |  double  |     0     |道路的方向，90度的时候为侧对接等,用于绘制路径      |
|   ignore_qr_direction   |   bool   |   false   |是否忽略二维码校验角度，当二维码贴反或者车尾对接时，设置为true，程序会自动进行角度变换      |
|     stuck_stop_dis      |  double  |    -1     |	用于小车在对接最后非常靠近目标点，又安全了，而且避障参数不方便改动的情况下，设置在该距离下卡住一段时间就会转跳下一步骤。-1说明不启用，最大为100      |
|      ref_max_secs       |  double  |    100    |最长对接时间      |

## 五、 对接误差参数和失败处理
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|   robot_front_to_leg    |  double  |   1000    |第一步阶段，机器人起步位置距离目标位置的估计值，用于防止起步识别料腿或直线错误      |
|   front_permit_error    |  double  |   3000    |机器人起步实际位置与估计值差值的可接受范围，大致公式是机器人前边缘距离目标点位置-robot_front_to_leg的值要小于front_permit_error      |
|    side_permit_error    |  double  |   3000    |机器人起步实际位置到目标点中心的左右偏移的误差允许值      |
|      max_move_dis       |  double  |   3000    |approaching的移动阈值，防止第一步对接阶段出现异常导致机器人走出太远的距离      |
|  max_angle_err_failed   |  double  |    181    |二维码校验开始时最大能接受的角度误差，大于该值会认为第一步对接失败      |
|         max_err         |  double  |    10     |允许的最大左右误差      |
|        max_err_x        |  double  |     4     |允许的最大前后误差      |
|       max_err_th        |  double  |    0.5    |允许的最大角度误差      |
|   err_beg_back_times    |   int    |     2     |允许后退重新对接的次数      |
|    failed_odom_back     |   bool   |   true    |任务失败后是否后退到起点位置      |
|      docking_alarm      |   bool   |   false   |对接出错后是否进行语音报警      |
|   stuck_back_mix_dis    |  double  |    -1     |卡住后退最大距离，小于0时不后退      |

## 六、 控制参数
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|    control_intensity    |  string  |  "high"   |控制参数，通常不做改动      |
|        dec_type         |  double  |  "t_dec"  |控制参数，通常不做改动      |
|       controller        |  string  |   "LQR"   |控制参数，使用什么控制器对接，不推荐随意修改      |
|       use_s_plan        |   bool   |   false   |是否使用s型规划，适合对接距离较大的情况，谨慎开启      |
|         angleS          |  double  |     5     |s型规划的开始角度，单位度      |
|         angleC          |  double  |    45     |c型规划的开始角度及s型规划的阶数角度， 单位 度      |
|     reservedLength      |  double  |    700    |预留的直线距离，越长越容易精确,单位mm      |

## 七、 其他debug参数
|          参数           | 数据类型 |  默认值   | 概述 |
| :---------------------: | :------: | :-------: | ---- |
|       record_bag        |   bool   |   false   |是否打开对接录包功能，推荐开启      |
|           log           |   bool   |   false   |是否记录详细日志，设置为true能够在log中打印一些特定日志      |









