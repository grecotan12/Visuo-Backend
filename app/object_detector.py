from ultralytics import YOLO
import cv2
from collections import defaultdict
import base64
import numpy as np

class ObjectDetector:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")
    
    def encode_image(self, img):
        _, buffer = cv2.imencode(".jpg", img)
        return base64.b64encode(buffer).decode("utf-8")

    def crop_objects(self, contents):
        np_img = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        
        crop_objects = defaultdict(list)
        results = self.model(img, verbose=False)
        r = results[0]

        for i, box in enumerate(r.boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cropped = img[y1:y2, x1:x2]
            
            class_id = int(box.cls[0])
            class_name = self.model.names[class_id]
            confidence = float(box.conf[0])

            crop_objects[class_name].append({
                "confidence": round(confidence, 3),
                "image": self.encode_image(cropped)
            })

            # cv2.imwrite(
            #     f"uploads/crops/{class_name}_{len(crop_objects[class_name])}.jpg",
            #     cropped
            # )
        return {
            "summary": {k: len(v) for k, v in crop_objects.items()},
            "detections": crop_objects
        }
