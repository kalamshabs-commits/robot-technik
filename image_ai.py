try:
    from ultralytics import YOLO
except Exception:
    YOLO = None
import os

ID2KEY = {
    0: "multicooker",
    1: "smartphone",
    2: "laptop",
    3: "printer",
    4: "microwave",
    5: "breadmaker"
}

def recognize_objects(image_path, conf=0.25):
    if YOLO:
        try:
            wp = os.environ.get("YOLO_WEIGHTS_PATH", "yolov8n.pt")
            m = YOLO(wp)
            r = m.predict(source=image_path, conf=conf, verbose=False)
            b = r[0].boxes
            cls = b.cls.tolist() if hasattr(b.cls, "tolist") else list(b.cls)
            confs = b.conf.tolist() if hasattr(b.conf, "tolist") else list(b.conf)
            out = []
            for c, s in zip(cls, confs):
                if s >= conf:
                    out.append(ID2KEY.get(int(c)))
            return [x for x in out if x]
        except Exception:
            return []
    return []
