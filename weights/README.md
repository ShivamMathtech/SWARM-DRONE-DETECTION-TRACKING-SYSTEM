# Model weights

Place your trusted, trained detection checkpoint here as `drone_detector.pt`,
or select another filename under `weights/` in Settings while the stream is stopped.
The code does not silently download models at runtime. No trained drone checkpoint
is included because no dataset or trained weights were supplied.

Demo mode needs no model weights. Generic COCO YOLO weights do not include a drone
class: they will report their actual class names. Train on your annotated drone
dataset and evaluate on held-out flights. PyTorch checkpoints must come from a
trusted source. They are loaded on your local computer.
