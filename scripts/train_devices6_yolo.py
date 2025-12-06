import os
import shutil
import subprocess
from pathlib import Path
from ultralytics import YOLO

def main():
    yaml_path = os.environ.get("DEVICES6_YAML", "data/devices6.yaml")
    out_dir = Path(os.environ.get("OUTPUT_DIR", "runs/devices6"))
    out_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO("yolov8n.pt")
    model.train(data=yaml_path, epochs=30, imgsz=320, batch=16, project=str(out_dir), name="train")
    best = out_dir / "train" / "weights" / "best.pt"
    if not best.exists():
        raise RuntimeError("best.pt not found")
    final = out_dir / "devices6_yolov8n.pt"
    shutil.copyfile(best, final)
    bucket = os.environ.get("MODEL_BUCKET", "").replace("gs://", "").strip()
    if bucket:
        subprocess.run(["gsutil", "cp", str(final), f"gs://{bucket}/devices6_yolov8n.pt"], check=True)
    print(f"Saved: {final}")

if __name__ == "__main__":
    main()