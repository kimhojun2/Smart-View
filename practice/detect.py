import cv2
import jetson_inference
import jetson_utils



def tags(name):
    # Hardcoded image file path
    image_file = './images/inp.jpg'

    # Hardcoded network
    network = 'ssd-mobilenet-v2'

    # Hardcoded overlay
    overlay = 'box,labels,conf'

    # Hardcoded detection threshold
    threshold = 0.5

    # Hardcoded labels file path
    labels_file = 'labels.txt'

    # Load the object detection network
    net = jetson_inference.detectNet(network, threshold)

    # Load class labels
    class_labels = []
    with open(labels_file, 'r') as f:
        class_labels = [line.strip() for line in f.readlines()]

    # Load the image
    img = cv2.imread(image_file)

    if img is not None:
        # Convert the image to RGBA (required for jetson-inference)
        img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

        # Allocate CUDA memory for the image
        cuda_img = jetson_utils.cudaFromNumpy(img_rgba)

        # Detect objects in the image (with overlay)
        detections = net.Detect(cuda_img, img.shape[1], img.shape[0], overlay=overlay)

        # Print the detections
        print("Detected objects in {}:".format(image_file))
        for detection in detections:
            class_label = class_labels[detection.ClassID]
            print("Class:", class_label)

    else:
        print("Failed to load the image from the specified path.")
