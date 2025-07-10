import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort


# Load YOLOv8 model
model = YOLO("yolov8n.pt")  # You can also try yolov8s.pt for better accuracy



# Initialize Deep SORT tracker
# tracker = DeepSort(max_age=30)  # max_age = frames to wait before deleting lost tracks

tracker = DeepSort(
    max_age=60,              # tolerate temporary disappearance
    n_init=3,
    max_cosine_distance=0.4, # tolerate slight ReID differences
    nn_budget=100,
)

# Open webcam
cap = cv2.VideoCapture(0)

tracked_ids_prev = set()

while True:
    ret, frame = cap.read()
    frame = cv2.resize(frame, (640, 480))
    if not ret:
        break

    # YOLO detection
    results = model(frame)[0]
    detections = []

    # Extract person detections
    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        if label == "person":
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            if conf > 0.4 and (x2 - x1) * (y2 - y1) > 500:
                detections.append(([x1, y1, x2 - x1, y2 - y1], conf, 'person'))

    # Update tracker
    tracks = tracker.update_tracks(detections, frame=frame)

    current_ids = set()
    for track in tracks:
        if not track.is_confirmed():
            continue
        track_id = track.track_id
        l, t, w, h = map(int, track.to_ltrb())
        current_ids.add(track_id)

        # Draw bounding box and ID
        cv2.rectangle(frame, (l, t), (l + w, t + h), (0, 255, 0), 2)
        cv2.putText(frame, f"ID: {track_id}", (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Compare ID sets to detect enter/exit
    entered_ids = current_ids - tracked_ids_prev
    exited_ids = tracked_ids_prev - current_ids

    for eid in entered_ids:
        print(f"🔵 Person ID {eid} entered")
    for xid in exited_ids:
        print(f"🔴 Person ID {xid} exited")

    tracked_ids_prev = current_ids.copy()

    # Display frame
    cv2.putText(frame, f"People in frame: {len(current_ids)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.imshow("YOLOv8 + Deep SORT Tracking", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break

cap.release()
cv2.destroyAllWindows()