#!/bin/bash
cam_name="cam1"
bundle_name="bundle10"
echo "data: 'start@$cam_name@$bundle_name'"
rostopic pub -1 /opts std_msgs/String "data: 'start@$cam_name@$bundle_name'" ;
python q2e.py 
sleep(2)
rostopic pub /opts std_msgs/String "data: 'stop@$cam_name@$bundle_name'"
