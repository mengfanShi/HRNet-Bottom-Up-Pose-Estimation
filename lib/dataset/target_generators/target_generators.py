# ------------------------------------------------------------------------------
# Copyright (c) Microsoft
# Licensed under the MIT License.
# Written by Ke Sun (sunk@mail.ustc.edu.cn).
# ------------------------------------------------------------------------------

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np


class HeatmapGenerator():
    def __init__(self, output_res, num_joints, use_jnt=False):
        self.output_res = output_res
        self.num_joints = num_joints

    def get_heat_val(self, sigma, x, y, x0, y0):

        g = np.exp(- ((x - x0) ** 2 + (y - y0) ** 2) / (2 * sigma ** 2))

        return g

    def __call__(self, joints, sgm, ct_sgm, bg_weight=1.0):
        '''
        sgm为关节点的标准差；ct_sgm为人体中心点的标准差
        bg_weight为背景元素所占的权重
        TODO 可考虑将尺度因素引入到标准差计算中,参考之前设定的公式
        '''
        assert self.num_joints == joints.shape[1], \
            'the number of joints should be %d' % self.num_joints

        hms = np.zeros((self.num_joints, self.output_res, self.output_res),
                       dtype=np.float32)
        ignored_hms = 2*np.ones((1, self.output_res, self.output_res),
                                dtype=np.float32)

        hms_list = [hms, ignored_hms]

        for p in joints:
            for idx, pt in enumerate(p):
                if idx < 17:
                    sigma = sgm
                else:
                    sigma = ct_sgm
                if pt[2] > 0:           # 值为0时表明图中关节点不可见
                    x, y = pt[0], pt[1]
                    if x < 0 or y < 0 or \
                            x >= self.output_res or y >= self.output_res:
                        continue
                    # 对坐标位置进行一个筛选

                    # 通过sigma计算一个辐射边界，边界内才有值，边界外认为没有影响
                    ul = int(np.floor(x - 3 * sigma - 1)
                             ), int(np.floor(y - 3 * sigma - 1))
                    br = int(np.ceil(x + 3 * sigma + 2)
                             ), int(np.ceil(y + 3 * sigma + 2))

                    cc, dd = max(0, ul[0]), min(br[0], self.output_res)
                    aa, bb = max(0, ul[1]), min(br[1], self.output_res)

                    joint_rg = np.zeros((bb-aa, dd-cc))
                    for sy in range(aa, bb):
                        for sx in range(cc, dd):
                            joint_rg[sy-aa, sx -
                                     cc] = self.get_heat_val(sigma, sx, sy, x, y)

                    # 关节热图的边界框内的值不能会负数, 且重叠位置使用最大值
                    hms_list[0][idx, aa:bb, cc:dd] = np.maximum(
                        hms_list[0][idx, aa:bb, cc:dd], joint_rg)
                    hms_list[1][0, aa:bb, cc:dd] = 1.

        # 通过值的差别来得到没有关节影响辐射区域的位置
        hms_list[1][hms_list[1] == 2] = bg_weight

        return hms_list


###########################################################################################
class ScaleAwareHeatmapGenerator():
    def __init__(self, output_res, num_joints, use_jnt=True):
        self.output_res = output_res
        self.num_joints = num_joints
        self.use_jnt = use_jnt
        self.jnt_thr = 0.01
        self.use_int = True

    def get_heat_val(self, sigma, x, y, x0, y0):

        g = np.exp(- ((x - x0) ** 2 + (y - y0) ** 2) / (2 * sigma ** 2))

        return g

    def __call__(self, joints, sgm, ct_sgm, bg_weight=1.0):
        '''
        sgm为关节点的标准差；ct_sgm为人体中心点的标准差
        bg_weight为背景元素所占的权重
        TODO 可考虑将尺度因素引入到标准差计算中,参考之前设定的公式
        '''
        assert self.num_joints == joints.shape[1], \
            'the number of joints should be %d' % self.num_joints

        hms = np.zeros((self.num_joints, self.output_res, self.output_res),
                       dtype=np.float32)
        ignored_hms = 2*np.ones((1, self.output_res, self.output_res),
                                dtype=np.float32)

        hms_list = [hms, ignored_hms]

        for p in joints:
            for idx, pt in enumerate(p):
                if idx < 17:
                    #####################################################
                    sigma = pt[3]
                    #####################################################
                else:
                    sigma = ct_sgm
                if pt[2] > 0:           # 值为0时表明图中关节点不可见
                    x, y = pt[0], pt[1]
                    if x < 0 or y < 0 or \
                            x >= self.output_res or y >= self.output_res:
                        continue
                    # 对坐标位置进行一个筛选
                    if self.use_jnt:
                        ################### JNT ######################
                        radius = np.sqrt(np.log(1 / self.jnt_thr) * 2 * sigma ** 2)
                        if self.use_int:
                            radius = int(np.round(radius))  # 取整
                        
                        ul = int(np.round(x - radius - 1)), int(np.round(y - radius - 1))
                        br = int(np.round(x + radius + 2)), int(np.round(y + radius + 2))
                        ################### JNT ######################
                    else:
                        ################### 3sigma ######################
                        ul = int(np.floor(x - 3 * sigma - 1)), int(np.floor(y - 3 * sigma - 1))
                        br = int(np.ceil(x + 3 * sigma + 2)), int(np.ceil(y + 3 * sigma + 2))
                        ################### 3sigma ######################

                    cc, dd = max(0, ul[0]), min(br[0], self.output_res)
                    aa, bb = max(0, ul[1]), min(br[1], self.output_res)

                    joint_rg = np.zeros((bb-aa, dd-cc))
                    for sy in range(aa, bb):
                        for sx in range(cc, dd):
                            joint_rg[sy-aa, sx -
                                     cc] = self.get_heat_val(sigma, sx, sy, x, y)

                    # 关节热图的边界框内的值不能会负数, 且重叠位置使用最大值
                    hms_list[0][idx, aa:bb, cc:dd] = np.maximum(
                        hms_list[0][idx, aa:bb, cc:dd], joint_rg)
                    hms_list[1][0, aa:bb, cc:dd] = 1.

        # 通过值的差别来得到没有关节影响辐射区域的位置
        hms_list[1][hms_list[1] == 2] = bg_weight

        return hms_list
##########################################################################################


class OffsetGenerator():
    def __init__(self, output_h, output_w, num_joints, radius):
        self.num_joints_without_center = num_joints - 1
        self.output_w = output_w
        self.output_h = output_h
        self.num_joints = num_joints
        self.radius = radius

    def __call__(self, joints, area):
        assert joints.shape[1] == self.num_joints, \
            'the number of joints should be 18, 17 keypoints + 1 center joint.'

        offset_map = np.zeros((self.num_joints_without_center*2, self.output_h, self.output_w),
                              dtype=np.float32)
        weight_map = np.zeros((self.num_joints_without_center*2, self.output_h, self.output_w),
                              dtype=np.float32)
        area_map = np.zeros((self.output_h, self.output_w),
                            dtype=np.float32)

        for person_id, p in enumerate(joints):
            # p[-1, 0]为人体中心点
            ct_x = int(p[-1, 0])
            ct_y = int(p[-1, 1])
            ct_v = int(p[-1, 2])
            if ct_v < 1 or ct_x < 0 or ct_y < 0 \
                    or ct_x >= self.output_w or ct_y >= self.output_h:
                continue

            for idx, pt in enumerate(p[:-1]):
                if pt[2] > 0:
                    x, y = pt[0], pt[1]
                    if x < 0 or y < 0 or \
                            x >= self.output_w or y >= self.output_h:
                        continue
                    
                    # 计算影响区域，用矩阵框来代替圆形区域
                    start_x = max(int(ct_x - self.radius), 0)
                    start_y = max(int(ct_y - self.radius), 0)
                    end_x = min(int(ct_x + self.radius), self.output_w)
                    end_y = min(int(ct_y + self.radius), self.output_h)

                    for pos_x in range(start_x, end_x):
                        for pos_y in range(start_y, end_y):
                            offset_x = pos_x - x
                            offset_y = pos_y - y

                            # 这里规划offset_map重合后只保留尺度更小的人
                            # 考虑如此可能是由于尺度小的人范围应该小一点精确一点
                            # TODO 不应单从尺度问题上考虑，也需要考虑到距离的因素
                            # 若距离中心点小于某个阈值，则不论尺度大小应该保留该人体的offset_map
                            if offset_map[idx*2, pos_y, pos_x] != 0 \
                                    or offset_map[idx*2+1, pos_y, pos_x] != 0:
                                if area_map[pos_y, pos_x] < area[person_id]:
                                    continue
                            offset_map[idx*2, pos_y, pos_x] = offset_x
                            offset_map[idx*2+1, pos_y, pos_x] = offset_y
                            
                            # weight_map是权值热图，依据尺度大小来进行赋值
                            weight_map[idx*2, pos_y, pos_x] = 1. / np.sqrt(area[person_id])
                            weight_map[idx*2+1, pos_y, pos_x] = 1. / np.sqrt(area[person_id])
                            area_map[pos_y, pos_x] = area[person_id]

        return offset_map, weight_map
