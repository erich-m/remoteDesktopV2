from vidstream import StreamingServer
import threading

reciever  = StreamingServer('10.0.0.191',1234)

t = threading.Thread(target=reciever.start_server)
t.start()

while input("") != 'exit':
    continue

reciever.stop_server()