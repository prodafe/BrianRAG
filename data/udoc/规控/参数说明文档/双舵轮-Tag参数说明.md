---
title: 双舵轮-Tag参数说明
description: 
published: true
date: 2025-12-17T11:34:51.746Z
tags: tagomni, 双舵轮, 参数说明
editor: markdown
dateCreated: 2025-09-16T08:53:07.422Z
---

# 双舵轮-Tag参数说明
  
| 文件名称 | 双舵轮-Tag参数说明  |
| ---- | ---------- |
| 部门   | 软件算法部      |
| 版本   | 1.0        |
| 密级   | 保密（部门内部公开） |


## 修改记录

| 版本号 | 修改日期       | 修改人      | 概述        | 详细说明        |
| --- | ---------- | -------- | --------- | ----------- |
| 1.0 | 2025-09-24 | Fan Xie  | 双舵轮-Tag | 双舵轮-Tag中使用的参数的含义 |

## 一、概述
简单解释双舵轮-Tag中会用到的参数的含义。第一阶段为移动到目标位置，第二阶段为微调，但是由于现场原因一般不使用第二阶段，而是采用另外一个check pose的mode作为routes的补充来使用。



## 二、参数
| 参数 | 数据类型 | 默认值 | 概述 | 
| :---: | :----------: | :--------: | --------- | 
|record_bag |bool |false |是否打开对接录包功能，推荐开启 |

|use_robot_center |bool |false |是否使用机器人中心作为参数配置的参考点，值为true则由offset_x,offset_y,offset_t确定目标位置，否则使用distance,offset,angle_robot_diff确定，建议使用第一种 |

|distance |double |700 |停车点在标志物中心的前后偏移 |
|offset |double |0 |停车点在标志物中心的左右偏移，左负右正 |
|angle_robot_diff |double |与offset_t一致 |机器人对接方向,正对接0度，倒对接180 |

|offset_x |double |0 |靠识别标志物移动停在标志物坐标系下的x方向的坐标，二维码粘贴时，一般将x轴指向机台 |
|offset_y |double |0 |靠识别标志物移动停在标志物坐标系下的y方向的坐标,左正右负 |
|offset_t |double |0 |靠识别标志物移动停在标志物坐标系下的t方向的坐标，逆时针为正，顺时针为负 |

|offset_addx |double |0 |据多车一致性设置偏移量x |
|offset_addy |double |0 |据多车一致性设置偏移量y |
|offset_addt |double |0 |据多车一致性设置偏移量t |

|odom_dis |double |0 |使用里程计运行的距离 |

|speed |double |100 |运行速度 |
|angle_speed |double |20 |旋转速度 |
|min_speed |double |5 |最小速度 |
|min_angle_speed |double |1 |最小角速度 |

|sensor_name |String |"cam0" |对接第一阶段对接依赖的传感器名称，如激光（话题名称，如前激光为/front/scan），相机（如cam1）等 |
|bundle_name |String |"bundle0" |对接第一阶段对接标志物的名称，料腿（料车名称，shelf-JH-side），二维码（如bundle0）等 |

|anglePathdiff |double |0 |道路的方向，90度的时候为侧对接等,用于绘制路径 |
|max_errx |double |10 |最终到点精度要求 |
|max_erry |double |10 |最终到点精度要求 |
|max_errt |double |1 |最终到点精度要求 |

|online_dis |double |30 |起点需要横移上线阈值 |
|online_angle |double |5 |起点需要原地旋转的阈值 |
|check_angle |bool |true |检验舵轮转到位后再移动 |
|steer_type |String |"two_helm" |舵轮类型为双舵轮还是四舵轮 |
|direction |String |"" |"left", "L", "right", "R", "front", "F", "back", "B"备选项，代表机器人对接方向和停车角度，如果配置了，会覆盖前面的offset_t和angle_robot_diff，否则按照offset_t和angle_robot_diff配置运行|
|max_secs |double |100 |最长对接时间 |
|odom_dis1 |double |100 |没有定位结果时，使用纯里程计运行的最大距离，超过此距离后会对接失败 |
|no_loc_secs |double |2 |如果超过该时间没有定位结果，认为定位失败 |
|update_laser_resolution |bool |false |如果需要更新激光频率，设置为true |
|need_check_init |bool |false |初始化时是否检查误差阈值 |
|permit_errorx |double |1000 |初始化x方向误差阈值要求 |
|permit_errory |double |300 |初始化y方向误差阈值要求 |
|permit_errort |double |10 |初始化角度误差阈值要求 |

|start_check_cam |bool |false |一般不使用此功能，是否检查第二阶段数据，如果true，则获取到第二阶段数据且走过距离超过has_check_result_dis就直接认为对接成功 |
|has_check_result_dis |double |20 |获取到第二阶段数据后且行走超过此距离就直接认为对接成功 |
|sensor_name_check |String |与sensor_name一致 |第二阶段传感器名称，如激光，相机等，命名规则同与sensor_name一致 |
|bundle_name_check |String |与bundle_name一致 |第二阶段停车检测依赖的标志物名称，料腿，二维码等，命名规则同bundle_name |