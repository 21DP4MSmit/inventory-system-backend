import cv2
import numpy as np
import os

import cv2
import numpy as np
import os


class ObjectDetector:
    def __init__(
        self,
        weights_path="ai/models/yolov4.weights",
        config_path="ai/models/yolov4.cfg",
        classes_path="ai/models/coco.names",
    ):
        if not all(
            os.path.exists(path) for path in [weights_path, config_path, classes_path]
        ):
            missing_files = [
                path
                for path in [weights_path, config_path, classes_path]
                if not os.path.exists(path)
            ]
            raise FileNotFoundError(
                f"YOLO model files not found. Please check paths. Missing: {missing_files}"
            )

        print(f"Loading YOLOv4 model from: {weights_path} and {config_path}")

        try:
            self.net = cv2.dnn.readNet(weights_path, config_path)
        except cv2.error as e:
            raise RuntimeError(
                f"Failed to load YOLO model from {weights_path} and {config_path}. OpenCV Error: {e}"
            )

        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(
            cv2.dnn.DNN_TARGET_CPU
        )  # Change to DNN_TARGET_CUDA if you have NVIDIA GPU

        print(f"Loading class names from: {classes_path}")
        try:
            with open(classes_path, "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
        except Exception as e:
            raise RuntimeError(
                f"Failed to read class names from {classes_path}. Error: {e}"
            )

        self.layer_names = self.net.getLayerNames()
        try:
            unconnected_out_layers_indices = self.net.getUnconnectedOutLayers()

            if (
                isinstance(unconnected_out_layers_indices, np.ndarray)
                and unconnected_out_layers_indices.ndim >= 1
            ):
                unconnected_out_layers_indices = (
                    unconnected_out_layers_indices.flatten()
                )
            elif isinstance(unconnected_out_layers_indices, int):
                unconnected_out_layers_indices = [unconnected_out_layers_indices]

            self.output_layers = [
                self.layer_names[i - 1] for i in unconnected_out_layers_indices
            ]

        except Exception as e:
            raise RuntimeError(
                f"Failed to get output layer names from the model. Error: {e}"
            )

        print(
            f"Model loaded successfully with {len(self.classes)} classes. Output layers: {self.output_layers}"
        )

    def detect(self, image_path, confidence_threshold=0.5, nms_threshold=0.4):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")

        height, width, channels = image.shape

        blob = cv2.dnn.blobFromImage(
            image, 1 / 255.0, (416, 416), swapRB=True, crop=False
        )

        self.net.setInput(blob)
        try:
            outputs = self.net.forward(self.output_layers)
        except cv2.error as e:
            raise RuntimeError(f"Error during model forward pass: {e}")

        class_ids = []
        confidences = []
        boxes = []

        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                if confidence > confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, confidence_threshold, nms_threshold
        )

        results = []
        if len(indices) > 0:
            if isinstance(indices, np.ndarray) and indices.ndim > 1:
                indices = indices.flatten()
            indices = [int(i) for i in indices]

            for i in indices:
                box = boxes[i]
                x, y, w, h = box
                x = max(0, x)
                y = max(0, y)
                w = max(1, w)
                h = max(1, h)

                results.append(
                    {
                        "class": self.classes[class_ids[i]],
                        "confidence": confidences[i],
                        "box": [x, y, w, h],
                    }
                )

        return results

    def annotate_image(self, image_path, output_path, detections):
        image = cv2.imread(image_path)
        if image is None:
            print(f"Warning: Could not read image {image_path} for annotation.")
            return None

        for detection in detections:
            x, y, w, h = detection["box"]
            label = f"{detection['class']} {detection['confidence']:.2f}"

            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(image.shape[1] - 1, x + w), min(image.shape[0] - 1, y + h)

            confidence = detection["confidence"]
            if confidence > 0.8:
                color = (0, 255, 0)
            elif confidence > 0.6:
                color = (0, 255, 255)
            else:
                color = (0, 165, 255)

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

            text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            text_w, text_h = text_size

            rect_y1 = y1 - text_h - 10
            if rect_y1 < 0:
                rect_y1 = y1 + 10

            rect_y2 = rect_y1 + text_h + 10

            cv2.rectangle(image, (x1, rect_y1), (x1 + text_w + 5, rect_y2), color, -1)

            text_y = rect_y1 + text_h + 5
            cv2.putText(
                image,
                label,
                (x1 + 3, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            success = cv2.imwrite(output_path, image)
            if not success:
                print(f"Warning: Failed to write annotated image to {output_path}")
                return None
        except Exception as e:
            print(f"Error writing annotated image to {output_path}: {e}")
            return None

        return output_path
