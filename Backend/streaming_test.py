import cv2

url = "rtsp://100.97.83.56:8554/stream"
#url = "rtsp://10.105.142.73:8554/stream"
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    cv2.imshow("iPhone Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
