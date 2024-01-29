from vidstream import ScreenShareClient
import threading

sender = ScreenShareClient('10.0.0.191',1234)

t = threading.Thread(target=sender.start_stream)
t.start()

while input("") != 'exit':
    continue

sender.stop_stream()