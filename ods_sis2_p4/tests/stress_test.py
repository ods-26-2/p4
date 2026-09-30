import time
import os
import psutil
import threading
import queue
import cv2

frame_queue = queue.Queue(maxsize=1)
process_ref = psutil.Process(os.getpid())

def frame_producer(cap):
    while cap.is_opened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_queue.full():
            try:
                frame_queue.get_nowait() # Tratamento de Frame Drop (Descarte FIFO)
            except queue.Empty:
                pass
        frame_queue.put(frame)

def run_test():
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    producer_thread = threading.Thread(target=frame_producer, args=(cap,), daemon=True)
    producer_thread.start()
    
    initial_memory = process_ref.memory_info().rss / (1024 * 1024)
    print(f"Memória Inicial (RSS): {initial_memory:.2f} MB")
    
    frame_count = 0
    while frame_count < 2000:
        if not frame_queue.empty():
            frame = frame_queue.get()
            _ = cv2.GaussianBlur(frame, (5, 5), 0)
            frame_count += 1
            if frame_count % 500 == 0:
                curr_mem = process_ref.memory_info().rss / (1024 * 1024)
                print(f"Frame: {frame_count} | Memória: {curr_mem:.2f} MB")
                
    cap.release()
    final_memory = process_ref.memory_info().rss / (1024 * 1024)
    print(f"Memória Final: {final_memory:.2f} MB | Delta: {final_memory - initial_memory:+.2f} MB")

if __name__ == "__main__":
    run_test()