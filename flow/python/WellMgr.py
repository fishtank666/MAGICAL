##
# @file WellMgr.py
# @author Keren Zhu
# @date 03/14/2021
# @brief Well generation manager
#

import magicalFlow
from device_generation.basic import basic as basic
import numpy as np
from PIL import Image
from models.WellGAN import torch_p2p
import cv2


# 0: horizontal; 1: vertical
def classify_edge(p1, p2):
    delta_x = abs(p1[0] - p2[0])
    delta_y = abs(p1[1] - p2[1])
    return delta_x < delta_y

def classify_edges(polygon):
    num_points = polygon.shape[0]

    edges = []
    edges_class = []
    for i in range(num_points-1):
        p1 = polygon[i][0]
        p2 = polygon[i+1][0]
        edges.append([p1, p2])
        edges_class.append( classify_edge(p1, p2) )
    edges.append([polygon[-1][0], polygon[0][0]])
    edges_class.append( classify_edge(polygon[-1][0], polygon[0][0]) )
    return edges, edges_class


def merge_edges(edges, edges_class):
    merged_edges = []
    merged_edges_class = []
    p1 = edges[0][0]
    p2 = edges[0][1]
    d = edges_class[0]
    if (p1 == p2).all(): # same point error
        return merged_edges, merged_edges_class
    for i in range(1, len(edges) + 1):
        if i < len(edges_class) and edges_class[i] == d:
            # calculate area
            p2 = edges[i][1]
        else:
            # print "here1 p1: ", p1, ", p2: ", p2
            actual_d = classify_edge(p1, p2)
            merged_edges.append(i-1) # only append the index, the second point of this index is p2
            # merged_edges_class.append(d)
            merged_edges_class.append(actual_d)
            if i < len(edges_class):
                p1 = edges[i][0]
                p2 = edges[i][1]
                d = edges_class[i]
    
    # return merged_edges, merged_edges_class, merged_edges_value
    return merged_edges, merged_edges_class 


# merge the edges that have the same direction
def merge_edges_direction(edges, merged_edges, merged_edges_class):
    ret_edges = []
    ret_edges_class = []
    i = 0
    while i < len(merged_edges):
        d = merged_edges_class[i] 
        j = i # i is first index, j is second index
        while (j < len(merged_edges)-1 and merged_edges_class[j+1] == d): 
            j += 1
        p1 = edges[merged_edges[i-1]][1]
        p2 = edges[merged_edges[j]][1]
        actual_d = classify_edge(p1, p2)
        ret_edges.append(merged_edges[j])
        ret_edges_class.append(actual_d)
        i = j+1
    # merge the first and the last edges if necessary
    if len(ret_edges_class) > 1 and ret_edges_class[0] == ret_edges_class[-1]:
        p1 = edges[ret_edges[-2]][1]
        p2 = edges[ret_edges[0]][1]
        actual_d = classify_edge(p1, p2)
        ret_edges_class[0] = actual_d
        ret_edges.pop()
        ret_edges_class.pop()
        
    return ret_edges, ret_edges_class

def rectilinear_transform(edges, edges_class, edges_value):
    # find intersection points
    num = len(edges_class)
    points = np.zeros((num+1, 1, 2), np.int32)
    if num == 0:
        return points
    # first point
    if edges_class[0]:
        points[0][0][0] = edges_value[0]        # x 
        points[0][0][1] = edges_value[num-1]    # y
    else:
        points[0][0][0] = edges_value[num-1] 
        points[0][0][1] = edges_value[0]
    for i in range(1, num):
        if edges_class[i]:
            points[i][0][0] = edges_value[i]
            points[i][0][1] = edges_value[i-1]
        else:
            points[i][0][0] = edges_value[i-1]
            points[i][0][1] = edges_value[i]
    # last point
    points[num][0] = points[0][0]
    return points

def calculate_edges_value(edges, i1, i2, d):
    tot_area = 0
    p1 = edges[i1][1]
    p2 = edges[i2][1]
    if i1 > i2:
        for i in range(i1+1, len(edges)):
            pointa = edges[i][0]
            pointb = edges[i][1]
            if d == 0:
                a = pointa[1] - p1[1]
                b = pointb[1] - p1[1]
                c = pointb[0] - pointa[0]
            else:
                a = pointa[0] - p1[0]
                b = pointb[0] - p1[0]
                c = pointb[1] - pointa[1]
            tot_area += (a + b) * c / 2.0        
        for i in range(0, i2+1):
            pointa = edges[i][0]
            pointb = edges[i][1]
            if d == 0:
                a = pointa[1] - p1[1]
                b = pointb[1] - p1[1]
                c = pointb[0] - pointa[0]
            else:
                a = pointa[0] - p1[0]
                b = pointb[0] - p1[0]
                c = pointb[1] - pointa[1]
            tot_area += (a + b) * c / 2.0        
    else:
        for i in range(i1+1, i2+1):
            pointa = edges[i][0]
            pointb = edges[i][1]
            if d == 0:
                a = pointa[1] - p1[1]
                b = pointb[1] - p1[1]
                c = pointb[0] - pointa[0]
            else:
                a = pointa[0] - p1[0]
                b = pointb[0] - p1[0]
                c = pointb[1] - pointa[1]
            tot_area += (a + b) * c / 2.0
    if d == 0:
        dist = p2[0] - p1[0]
        return p1[1] + int(tot_area / dist)
    else:
        dist = p2[1] - p1[1]
        return p1[0] + int(tot_area / dist)


def get_merged_edges_value(edges, merged_edges, merged_edges_class):
    ret_edges = []
    ret_value = []
    if len(merged_edges) == 1:
        ret_edges.append( edges[merged_edges[0]] )
        ret_value.append( calculate_edges_value(edges, merged_edges[0]-1, merged_edges[0], merged_edges_class[0]) )
        return ret_edges, ret_value
    for i in range(len(merged_edges)):
        i1 = merged_edges[i-1]
        i2 = merged_edges[i]
        p1 = edges[i1][1]
        p2 = edges[i2][1]
        ret_edges.append([p1, p2])
        ret_value.append( calculate_edges_value(edges, i1, i2, merged_edges_class[i]) )

    return ret_edges, ret_value

def check_alternate_direction(edges_class):
    for i in range(len(edges_class)):
        if edges_class[i-1] == edges_class[i]:
            return False
    return True

def orthogonalize(polygon):
    """
    Orthogonalize a polygon. 
    """
    
    # classify edge to the two orthogonal direction
    edges, edges_class = classify_edges(polygon)
    # merge adjacent edges that share the same class
    merged_edges, merged_edges_class = merge_edges(edges, edges_class)
    while (len(merged_edges_class) > 1 and check_alternate_direction(merged_edges_class) == False):
        merged_edges, merged_edges_class = merge_edges_direction(edges, merged_edges, merged_edges_class)
    
    if len(merged_edges) <= 1:
        return np.zeros((0, 1, 2), np.int32)

    merged_edges, merged_edges_value = get_merged_edges_value(edges, merged_edges, merged_edges_class)
    
    # rectilinear transformation: 
    points = rectilinear_transform(merged_edges, merged_edges_class, merged_edges_value)

    return points

class WellMgr(object):
    def __init__(self, ddb, tdb):
        """
        @param ddb: a magicalFlow.DesignDB object
        """
        self._ddb = ddb
        self._tdb = tdb
        self._util = magicalFlow.DataWellGAN(ddb, tdb.pdkLayerToDb(basic.layer['OD']))
        self.imageSize = 256 # 256 * 256
        self.cropMargin = 5
        self.cropSize = self.imageSize - 2 * self.cropMargin
        self._scale = self._tdb.units().dbu * 0.06 # pixel = 1um / 0.06. Ask WellGAN for this number
        self.legalPaddingOffset = 10
        self.legalAreaThresh = 20 
    def clear(self):
        self._util.clear()
    def constructCkt(self, cktIdx):
        # Extract well shapes from layouts
        self._util.construct(cktIdx)
        # Scale and convert them in images
        # WellGAN's initial implementation first convert layout into 512*256*3,
        # where the left part is including NW and right part is not include.
        # The left part is basically golden.
        # In GAN model, the data are actually processed as 256 * 256 * 6,
        # where the first three channels are "input" and the last three are "output"
        # There needs some normalization too.
        # In this implementation, we just do everything together
        #
        # We need to crop the whole layouts into smaller clips
        # Each clip is 256 / scale * 256 / scale in db unit (so it's actually technology dependent)
        bbox = self._util.bbox()
        self._xLo = bbox.xLo
        self._yLo = bbox.yLo
        width = self.pixelX(bbox.xHi)
        height = self.pixelY(bbox.yHi)
        self.numRow = int(height / self.cropSize)  + 1 
        self.numCol = int(width / self.cropSize) + 1
        self.imgs = np.zeros(( self.numRow * self.numCol, self.imageSize, self.imageSize, 6), dtype=np.float32)
        def fillRect(rect, channels):
            colBegin, colBeginOffset = self.imgX(rect.xLo - self.cropMargin)
            colEnd, colEndOffset = self.imgX(rect.xHi + self.cropMargin)
            rowBegin, rowBeginOffset = self.imgY(rect.yLo - self.cropMargin)
            rowEnd, rowEndOffset = self.imgY(rect.yHi + self.cropMargin)
            for row in range(rowBegin, rowEnd + 1):
                rStartIdx = 0
                rEndIdx = self.imageSize - 1
                if row == rowBegin:
                    rStartIdx = rowBeginOffset
                if row == rowEnd:
                    rEndIdx = rowEndOffset
                for col in range(colBegin, colEnd + 1):
                    cStartIdx = 0
                    cEndIdx = self.imageSize - 1
                    if col == colBegin:
                        cStartIdx = colBeginOffset
                    if col == colEnd:
                        cEndIdx = colEndOffset
                    for r in range(rStartIdx, rEndIdx + 1):
                        for c in range(cStartIdx, cEndIdx + 1):
                            for ch in channels:
                                self.imgs[self.imgIdx(row, col)][r][c][ch] = 1.0 

        for odIdx in range(self._util.numPchOdRects()):
            rect = self._util.odPchRect(odIdx)
            fillRect(rect, [2, 5]) #R
        for odIdx  in range(self._util.numOtherOdRects()):
            rect = self._util.odOtherRect(odIdx)
            fillRect(rect, [1, 4]) #G
        self.imgs = self.imgs * 2.0 - 1
    def infer(self):
        model = torch_p2p()
        model.load_model()
        infer = model.sample(self.imgs) 
        self.inferred=infer[:,:,:,0]
    def merge(self):
        self.mergeInferred = np.zeros( (self.numRow * self.cropSize, self.numCol * self.cropSize), dtype = np.float32)
        self.mergeInput = np.zeros( (self.numRow * self.cropSize, self.numCol * self.cropSize, 2), dtype = np.float32)
        for imI in range(self.numRow * self.numCol):
            row, col = self.imgIdxToRC(imI)
            self.mergeInferred[row* self.cropSize: (row+1) * self.cropSize, col* self.cropSize: (col+1) * self.cropSize] = self.inferred[imI,self.cropMargin:self.imageSize - self.cropMargin,self.cropMargin:self.imageSize - self.cropMargin]
            self.mergeInput[row* self.cropSize: (row+1) * self.cropSize, col* self.cropSize: (col+1) * self.cropSize, :] = self.imgs[imI,self.cropMargin:self.imageSize - self.cropMargin,self.cropMargin:self.imageSize - self.cropMargin, 1:3]

    def legalize(self):
        im = ((self.mergeInferred / 2.0 + 0.5) * 255).astype(np.uint8)
        height,width = im.shape
        imPad = np.zeros( (height + self.legalPaddingOffset *2, width + self.legalPaddingOffset *2), np.uint8)
        imPad[self.legalPaddingOffset:self.legalPaddingOffset+height, self.legalPaddingOffset:self.legalPaddingOffset+width] = im
        im = imPad
        
        # Find the contours
        _, thresh = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Prune the contours and orthogonalize the contours
        approxContours = []
        for contour in contours:
            if contour.shape[0] > 1 and cv2.contourArea(contour) > self.legalAreaThresh:
                approx = orthogonalize(contour)
                if approx.shape[0] <= 2:
                    continue
                epsilon = 3
                approx = cv2.approxPolyDP(approx, epsilon, True)
                approx = orthogonalize(approx)
                if approx.shape[0] > 2:
                    approx = approx - self.legalPaddingOffset # Offet back the padding
                    approxContours.append(approx)


    def imgIdxToRC(self, idx):
        return idx % self.numRow, int(idx / self.numRow)
    def imgIdx(self, row, col):
        return row + col * self.numRow
    def pixelX(self, x):
        return int( ( x - self._xLo) / self._scale)
    def pixelY(self, y):
        return int( ( y - self._yLo) / self._scale)
    def imgX(self, x):
        """
        return col, offset
        """
        rx = self.pixelX(x)
        return int(rx / self.cropSize), rx % self.cropSize
    def imgY(self, y):
        """
        return row, offset
        """
        ry = self.pixelY(y)
        return int(ry / self.cropSize), ry % self.cropSize
    def drawInputImage(self):
        """
        Draw self.img, for debugging purpose
        """
        img = self.imgs[7]
        img = img /2.0 + 0.5
        img = (img[:,:, :3] * 255).astype(np.uint8)
        b,g,r = img[:,:,0], img[:,:,1], img[:,:,2]
        img = np.concatenate((r[:,:,np.newaxis],g[:,:, np.newaxis],b[:,:, np.newaxis]), axis=-1)
        img_s = Image.fromarray(img, 'RGB') # fromarray only works with uint8
        img_s.show()
    def drawInferredImage(self):
        """
        Draw self.img, for debugging purpose
        """
        input_img = self.imgs[7]
        input_img = input_img / 2.0 + 0.5
        r,g = input_img[:,:,2], input_img[:,:,1]
        b = self.inferred[7]  / 2.0 + 0.5
        r = (r * 255).astype(np.uint8)
        g = (g * 255).astype(np.uint8)
        b = (b * 255).astype(np.uint8)
        img = np.concatenate((r[:,:,np.newaxis],g[:,:, np.newaxis],b[:,:, np.newaxis]), axis=-1)

        img_s = Image.fromarray(img, 'RGB') # fromarray only works with uint8
        img_s.show()
    def drawMergedInferredImage(self):
        input_img = self.mergeInput / 2.0 +0.5
        r,g = input_img[:,:,1], input_img[:,:,0]
        b = self.mergeInferred 
        b = b/2.0 + 0.5
        r = (r * 255).astype(np.uint8)
        g = (g * 255).astype(np.uint8)
        b = (b * 255).astype(np.uint8)
        img = np.concatenate((r[:,:,np.newaxis],g[:,:, np.newaxis],b[:,:, np.newaxis]), axis=-1)

        img_s = Image.fromarray(img, 'RGB') # fromarray only works with uint8
        img_s.show()
