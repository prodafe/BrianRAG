---
title: 双舵轮-CheckPose参数说明
description: 
published: true
date: 2025-09-25T07:07:37.920Z
tags: 
editor: markdown
dateCreated: 2025-09-24T03:27:45.730Z
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
|camName_check |String |"cam0" |停车检测的相机 |
|bundleName_check |String |"bundle4" |停车检测的二维码名字 |

|offset_x |double |0 |小码校验时，机器人中心在小码中的前后偏移 |
|offset_y |double |0 |小码校验时，机器人中心在小码中的左右偏移 |
|offset_t |double |0 |小码校验时，机器人中心在小码中的角度偏移 |

|offset_addx |double |0 |据多车一致性设置偏移量x |
|offset_addy |double |0 |据多车一致性设置偏移量y |
|offset_addt |double |0 |据多车一致性设置偏移量t |

|max_error_x |double |3 |最终到点精度要求 |
|max_error_y |double |3 |最终到点精度要求 |
|max_error_t |double |1 |最终到点精度要求 |

|time |double |100 |超时的限定时间 |

|find_step |double |10 |找二维码的步长 |

|min_speed |double |5 |最小速度 |
|min_angle_speed |double |1 |最小角速度 |

|find_code_type |String |"cross" |"left_right", "front_back", "cross"备选项，代表找二维码的方式，即左右、前后、前后左右十字三种类型 |

|has_check_result_dis |double |20 |获取数据后且行走超过此距离就判定找到二维码 |

|calibration |bool |false |调整完成后，是否发送消息给服务器 |
|ip |String |" " |若calibration为true，发送的服务器ip |
|port |int |12345 |若calibration为true，发送的服务器port |

|is_check_pose |bool |true |需不需要做最后调整，一般为true |
|is_check_id |bool |true |需不需要根据二维码校验id |

|id_from_rms |bool |false |是否从rms获得ID与readID |
|ID |String |"" |若id_from_rms为false，从routes获得的ID |
|readID |bool |false |若id_from_rms为false，从routes获得的readID，是否需要校验结果与获得的ID一致 |

|check_robot_init_pose |bool |false |初始化时是否检查起始误差阈值 |
|permit_errorx |double |1000 |初始化x方向误差阈值要求 |
|permit_errory |double |300 |初始化y方向误差阈值要求 |
|permit_errort |double |10 |初始化角度误差阈值要求 |