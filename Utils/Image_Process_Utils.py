from PIL import Image, ImageChops
import cv2
import os
import numpy as np
import re
import math
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'/Users/youssef/Application/Homebrew/Cellar/tesseract/4.1.1/bin/tesseract'

def trim(im):
    bbox = get_box(im)
    if bbox:
        return im.crop(bbox)
    return im

def read_and_trim(input_file):
	img = Image.open(input_file)
	img = trim(img)
	img = np.asarray(img)
	return img

# Rescale the image, if needed.
def rescaling(image, imagename, output):
    img_pil = Image.fromarray(image)
    imagepaths=imagename.split("/")
    imagenames=imagepaths[len(imagepaths)-1].split(".")
    imagename=output+"/"+imagenames[len(imagenames)-2]+"600dpi."+imagenames[len(imagenames)-1]
    print(imagename)
    img_pil = img_pil.save(imagename, dpi=(600, 600))
    image = cv2.imread(imagename)
    print(image.shape)
    d=(1024,768)
    if image.shape[0] > image.shape[1]:
        image=deskew(image)
    if image.shape[0] == image.shape[1]:
        scale_percent = int(900 * 100 /image.shape[0]) # percent of original size
        width = int(image.shape[1] * scale_percent / 100)
        height = int(image.shape[0] * scale_percent / 100)
        d = (width, height)
    img = cv2.resize(image, d, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    print(img.shape)
    os.remove(imagename)
    return img

# get grayscale image
def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# noise removal
def remove_noise(image):
    # Apply dilation and erosion to remove some noise
    kernel = np.ones((1, 1), np.uint8)
    img = cv2.dilate(image, kernel, iterations=1)
    img = cv2.erode(img, kernel, iterations=1)
    # Apply blur to smooth out the edges
    img = cv2.GaussianBlur(img, (5, 5), 0)
    return img

#thresholding with different filters
def apply_threshold(img,gray, argument):
    kernel = np.ones((1,1), np.uint8)
    switcher = {
        1: gray,
        2: cv2.erode(cv2.threshold(cv2.GaussianBlur(gray, (3, 3), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],kernel,iterations=1),
        3: cv2.erode(cv2.threshold(cv2.GaussianBlur(gray, (1, 1), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],kernel,iterations=1),
        4: cv2.threshold(cv2.GaussianBlur(gray, (3, 3), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        5: cv2.threshold(cv2.GaussianBlur(gray, (1, 1), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        6: cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        7: cv2.threshold(cv2.medianBlur(gray, 5), 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        8: cv2.threshold(cv2.medianBlur(gray, 3), 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        9: cv2.threshold(cv2.medianBlur(gray, 1), 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        10: cv2.adaptiveThreshold(cv2.bilateralFilter(img,9,40,100), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, 2),
        11: cv2.threshold(cv2.bilateralFilter(img,3,75,75),127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        12: img,
        13: gray,
        14: cv2.adaptiveThreshold(cv2.bilateralFilter(gray,7,75,75), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 5, 2),
        15: cv2.adaptiveThreshold(cv2.bilateralFilter(gray,8,75,75), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 5, 2),
        16: cv2.adaptiveThreshold(cv2.bilateralFilter(gray,7,75,75), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 9, 2),
        17: cv2.adaptiveThreshold(cv2.bilateralFilter(img,9,150,150), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 9, 2),
        18: cv2.adaptiveThreshold(cv2.bilateralFilter(img,8,75,75), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, 2),
        19: cv2.adaptiveThreshold(cv2.GaussianBlur(img, (5, 5), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
        20: cv2.adaptiveThreshold(cv2.medianBlur(img, 3), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),


    }
    return switcher.get(argument, "Invalid method")

#deskew
def deskew(image):
    # convert the image to grayscale and flip the foreground
    # and background to ensure foreground is now "white" and
    # the background is "black"
    #This second bit detect smaller inclination angle and correct it
    # convert the image to grayscale and flip the foreground
    # and background to ensure foreground is now "white" and
    # the background is "black"
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    # threshold the image, setting all foreground pixels to
    # 255 and all background pixels to 0
    thresh = cv2.threshold(gray, 0, 255,
       cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    # grab the (x, y) coordinates of all pixel values that
    # are greater than zero, then use these coordinates to
    # compute a rotated bounding box that contains all
    # coordinates
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    # the `cv2.minAreaRect` function returns values in the
    # range [-90, 0); as the rectangle rotates clockwise the
    # returned angle trends to 0 -- in this special case we
    # need to add 90 degrees to the angle
    if angle < -45:
        angle = -(90 + angle)
    # otherwise, just take the inverse of the angle to make
    # it positive
    else:
        angle = -angle
    # rotate the image to deskew it
    print("[ANGLE] "+str(angle))
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    image = cv2.warpAffine(image, M, (w, h),
       flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    try:
        img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        img_edges = cv2.Canny(img_gray, 100, 100, apertureSize=3)
        lines = cv2.HoughLinesP(img_edges, 1, math.pi / 180.0, 100, minLineLength=100, maxLineGap=5)
        angles = []

        for x1, y1, x2, y2 in lines[0]:
            cv2.line(image, (x1, y1), (x2, y2), (255, 0, 0), 3)
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            angles.append(angle)

            median_angle = np.median(angles)
            print("[ANGLE 2] "+str(median_angle))
            img_pil = Image.fromarray(image)
            img_pil = img_pil.rotate(median_angle, expand=True)
        #convert the pil image to cv2 image
        image = np.asarray(img_pil)
    except TypeError:
        print("image too small to deskew")
    #this bit detect if the image is upside down or at 90 or 270 degree
    #then rotate it
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        #use tesseract image_to_osd method to detect angles of rotation
        rot_data = pytesseract.image_to_osd(image, lang='fra')
    except pytesseract.pytesseract.TesseractError:
        print("Too few characters/resolution in image to osd")
    else:
        print("[OSD] "+rot_data)
        rot = re.search('(?<=Rotate: )\d+', rot_data).group(0)
        conf = re.search('(?<=Orientation confidence: )\d+', rot_data).group(0)
        #calculation of the correction angle
        if float(conf) > 0.7:
            angle = float(rot)
        else:
            angle = 0

        if angle > 0:
            angle = 360 - angle

        print("[ANGLE 3] "+str(angle))
        # rotate the image to deskew it
        img_pil = Image.fromarray(image)
        img_pil = img_pil.rotate(angle, expand=True)
        #convert the pil image to cv2 image
        image = np.asarray(img_pil)
    return image

def get_box(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    return bbox

def pre_process(image, input_file):
    img = rescaling(image,input_file,"./")
    img = deskew(img)
    gray = get_grayscale(img)
    img = remove_noise(gray)
    img_thresh = apply_threshold(img,gray,19)
    img_thresh = Image.fromarray(img_thresh)
    box = get_box(img_thresh)
    img_p = Image.fromarray(img)
    img_p = img_p.crop(box)#2
    img = np.asarray(img_p)
    img = rescaling(img,input_file,"./")
    img = get_grayscale(img)
    img = remove_noise(img)
    return  (img, gray)