import cv2
import pyautogui
import numpy as np

from PIL import Image
import win32gui
from os import path

import socket
import pickle
import struct
import threading


class StreamingServer:
   
    def __init__(self, host, port, slots=8, quit_key='q'):#complete
       
        self.__host = host
        self.__port = port
        self.__slots = slots
        self.__used_slots = 0
        self.__running = False
        self.__quit_key = quit_key
        self.__block = threading.Lock()
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__init_socket()

    def __init_socket(self):#complete(host)
        
        self.__server_socket.bind((self.__host, self.__port))

    def start_server(self):#complete(host)
        
        if self.__running:
            print("Server is already running")
        else:
            self.__running = True
            server_thread = threading.Thread(target=self.__server_listening)
            server_thread.start()

    def __server_listening(self):#complete(host) (connection management)
        
        self.__server_socket.listen()
        while self.__running:
            self.__block.acquire()
            connection, address = self.__server_socket.accept()
            if self.__used_slots >= self.__slots:
                print("Connection refused! No free slots!")
                connection.close()
                self.__block.release()
                continue
            else:
                self.__used_slots += 1
            self.__block.release()
            thread = threading.Thread(target=self.__client_connection, args=(connection, address,))
            thread.start()

    def stop_server(self):#complete (host)
        
        if self.__running:
            self.__running = False
            closing_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            closing_connection.connect((self.__host, self.__port))
            closing_connection.close()
            self.__block.acquire()
            self.__server_socket.close()
            self.__block.release()
        else:
            print("Server not running!")

    def __client_connection(self, connection, address):#completed in client
        
        payload_size = struct.calcsize('>L')
        data = b""

        while self.__running:

            break_loop = False

            while len(data) < payload_size:
                received = connection.recv(4096)
                if received == b'':
                    connection.close()
                    self.__used_slots -= 1
                    break_loop = True
                    break
                data += received

            if break_loop:
                break

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]

            msg_size = struct.unpack(">L", packed_msg_size)[0]

            while len(data) < msg_size:
                data += connection.recv(4096)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            frame = pickle.loads(frame_data, fix_imports=True, encoding="bytes")
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            cv2.imshow('Host Computer', frame)
            if cv2.waitKey(1) == ord(self.__quit_key):
                connection.close()
                self.__used_slots -= 1
                break


class StreamingClient:
    

    def __init__(self, host, port):#completed (client)
       
        self.__host = host
        self.__port = port
        self._configure()#part of the host class
        self.__running = False
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _configure(self):#complete (host)
        
        self.__encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def _get_frame(self):#completed in host
        
        return None

    def _cleanup(self):#completed in host
        
        cv2.destroyAllWindows()

    def __client_streaming(self):#completed as host
        
        self.__client_socket.connect((self.__host, self.__port))
        while self.__running:
            frame = self._get_frame()
            result, frame = cv2.imencode('.jpg', frame, self.__encoding_parameters)
            data = pickle.dumps(frame, 0)
            size = len(data)

            try:
                self.__client_socket.sendall(struct.pack('>L', size) + data)
            except ConnectionResetError:
                self.__running = False
            except ConnectionAbortedError:
                self.__running = False
            except BrokenPipeError:
                self.__running = False

        self._cleanup()

    def start_stream(self):
        

        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            client_thread = threading.Thread(target=self.__client_streaming)
            client_thread.start()

    def stop_stream(self):
        
        if self.__running:
            self.__running = False
        else:
            print("Client not streaming!")


class CameraClient(StreamingClient):
    

    def __init__(self, host, port, x_res=1024, y_res=576):
        
        self.__x_res = x_res
        self.__y_res = y_res
        self.__camera = cv2.VideoCapture(0)
        super(CameraClient, self).__init__(host, port)

    def _configure(self):
        
        self.__camera.set(3, self.__x_res)
        self.__camera.set(4, self.__y_res)
        super(CameraClient, self)._configure()

    def _get_frame(self):
        
        ret, frame = self.__camera.read()
        return frame

    def _cleanup(self):
        
        self.__camera.release()
        cv2.destroyAllWindows()


class VideoClient(StreamingClient):
    

    def __init__(self, host, port, video, loop=True):
        
        self.__video = cv2.VideoCapture(video)
        self.__loop = loop
        super(VideoClient, self).__init__(host, port)

    def _configure(self):
        
        self.__video.set(3, 1024)
        self.__video.set(4, 576)
        super(VideoClient, self)._configure()

    def _get_frame(self):
        
        ret, frame = self.__video.read()
        return frame

    def _cleanup(self):
        
        self.__video.release()
        cv2.destroyAllWindows()


class ScreenShareClient(StreamingClient):
    

    def __init__(self, host, port, x_res=1024, y_res=576):
        
        self.__x_res = x_res
        self.__y_res = y_res
        super(ScreenShareClient, self).__init__(host, port)

    def _get_frame(self):
        
        screen = pyautogui.screenshot()
        frame = np.array(screen)
    
        x,y = pyautogui.position()

        cursor = [
            [#regular
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,2,2,2,1,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,2,2,2,2,1,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,2,2,2,2,2,1,0,0,0,0,0,0,0],
                [1,2,2,2,2,2,2,1,1,1,1,1,0,0,0,0,0,0,0],
                [1,2,2,2,1,2,2,1,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,1,0,1,2,2,1,0,0,0,0,0,0,0,0,0,0],
                [1,2,1,0,0,1,2,2,1,0,0,0,0,0,0,0,0,0,0],
                [1,1,0,0,0,0,1,2,2,1,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,1,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0]
            ],[#inverted
                [2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,2,0,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,1,2,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0],
                [2,1,1,1,1,1,1,2,2,2,2,2,0,0,0,0,0,0,0],
                [2,1,1,1,2,1,1,2,0,0,0,0,0,0,0,0,0,0,0],
                [2,1,1,2,0,2,1,1,2,0,0,0,0,0,0,0,0,0,0],
                [2,1,2,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0,0],
                [2,2,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,2,1,1,2,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,2,2,0,0,0,0,0,0,0,0,0,0]
            ],[#finger
                [0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,0,0,1,1,1,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,0,0,1,0,0,1,1,1,0,0,0,0,0,0],
                [1,1,1,0,1,0,0,1,0,0,1,0,0,1,1,0,0,0,0],
                [1,0,0,1,1,0,0,1,0,0,1,0,0,1,0,1,0,0,0],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0],
                [0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
                [0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
                [0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
                [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0],
                [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
                [0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
                [0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
                [0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0,0],
                [0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0,0],
                [0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0]
            ],[#bar
                [0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0],
                [0,0,0,0,2,2,2,2,2,1,2,2,2,2,2,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,1,1,1,1,1,2,1,1,1,1,0,0,0,0],
                [0,0,0,0,2,2,2,2,2,2,2,2,2,2,2,0,0,0,0]
            ],[#up/down arrow
                [0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,2,2,0,1,0,0,0,0,0,0],
                [0,0,0,0,0,1,1,1,1,2,1,1,1,1,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,1,1,1,1,2,1,1,1,1,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,2,2,2,1,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0]
            ],[#topleft/bottomright arrow
                [1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,1,0,1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0],
                [1,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,1],
                [0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,1,0,1,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,1,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1]
            ],[#left/right arrow
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
                [0,0,0,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0],
                [0,0,1,2,1,0,0,0,0,0,0,0,0,0,1,2,1,0,0],
                [0,1,2,2,1,1,1,1,1,1,1,1,1,1,1,2,2,1,0],
                [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
                [0,1,2,2,1,1,1,1,1,1,1,1,1,1,1,2,2,1,0],
                [0,0,1,2,1,0,0,0,0,0,0,0,0,0,1,2,1,0,0],
                [0,0,0,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0],
                [0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
            ],[#bottomleft/topright arrow
                [0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,1,2,1],
                [0,0,0,0,0,0,0,0,0,0,0,1,2,2,2,1,0,1,1],
                [0,0,0,0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,1],
                [0,0,0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0,0,0],
                [1,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0,0,0,0],
                [1,1,0,1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,2,2,2,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0]
            ],[#circle w arrows
                [0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0],
                [0,0,0,0,1,1,2,2,2,2,2,2,2,1,1,0,0,0,0],
                [0,0,0,1,2,2,2,2,2,1,2,2,2,2,2,1,0,0,0],
                [0,0,1,2,2,2,2,2,1,1,1,2,2,2,2,2,1,0,0],
                [0,1,2,2,2,2,2,1,1,1,1,1,2,2,2,2,2,1,0],
                [0,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,0],
                [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
                [1,2,2,2,1,2,2,2,2,2,2,2,2,2,1,2,2,2,1],
                [1,2,2,1,1,2,2,2,2,1,2,2,2,2,1,1,2,2,1],
                [1,2,2,2,2,2,2,2,1,1,1,2,2,2,1,1,1,2,1],
                [1,2,2,1,1,2,2,2,2,1,2,2,2,2,1,1,2,2,1],
                [1,2,2,2,1,2,2,2,2,2,2,2,2,2,1,2,2,2,1],
                [1,2,2,2,2,2,2,2,2,2,2,2,2,2,1,2,2,2,1],
                [0,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1,0],
                [0,1,2,2,2,2,2,1,1,1,1,1,2,2,2,2,2,1,0],
                [0,0,1,2,2,2,2,2,1,1,1,2,2,2,2,2,1,0,0],
                [0,0,0,1,2,2,2,2,2,1,2,2,2,2,2,1,0,0,0],
                [0,0,0,0,1,1,2,2,2,2,2,2,2,1,1,0,0,0,0],
                [0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0]
            ],[#no circle all arrows
                [0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,2,2,0,1,0,0,0,0,0,0],
                [0,0,0,0,0,1,1,1,1,2,1,1,1,1,0,0,0,0,0],
                [0,0,0,0,1,0,0,0,1,2,1,0,0,0,1,0,0,0,0],
                [0,0,0,1,1,0,0,0,1,2,1,0,0,0,1,1,0,0,0],
                [0,0,1,2,1,0,0,0,1,2,1,0,0,0,1,2,1,0,0],
                [0,1,2,2,1,1,1,1,1,2,1,1,1,1,1,2,2,1,0],
                [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,1],
                [0,1,2,2,1,1,1,1,1,2,1,1,1,1,1,2,2,1,0],
                [0,0,1,2,1,0,0,0,1,2,1,0,0,0,1,2,1,0,0],
                [0,0,0,1,1,0,0,0,1,2,1,0,0,0,1,1,0,0,0],
                [0,0,0,0,1,0,0,0,1,2,1,0,0,0,1,0,0,0,0],
                [0,0,0,0,0,1,1,1,1,2,1,1,1,1,0,0,0,0,0],
                [0,0,0,0,0,0,1,2,2,2,2,2,1,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,1,2,2,2,1,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0]
            ]
        ]
        i,t,p = win32gui.GetCursorInfo()
        # print(t)
        verticalOffset = 0
        horizontalOffset = 0
        ct = 0
        if t == 31918455:#inverted
            ct = 1
        elif t == 65569:#finger
            ct = 2
        elif t == 65543:#bar
            ct = 3
            verticalOffset = -9
        elif t == 65557:#up/down arrow
            ct = 4
            verticalOffset = -9
        elif t == 65551:#topleft/bottomright arrow
            ct = 5
            verticalOffset = -9
            horizontalOffset = -9
        elif t == 65555:#left/right arrow
            ct = 6
            horizontalOffset = -9
        elif t == 65553:#bottomleft/topright arrow
            ct = 7
            verticalOffset = -9
            horizontalOffset = -9
        elif t == 17697265 or t == 259656119:#circle w arrow
            ct = 8
        elif t == 1902623:#no circle all arrows
            ct = 9
        else:#regular
            ct = 0
        
        s=19
       
        for r in range(s):
            for c in range(s):
                try:
                    if x >= 0 and y >= 0:
                        if cursor[ct][r][c] == 1:
                            frame[y+r+verticalOffset][x+c+horizontalOffset] = (0,0,0)
                        elif cursor[ct][r][c] == 2:
                            frame[y+r+verticalOffset][x+c+horizontalOffset] = (255,255,255)
                except Exception:
                    pass
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.__x_res, self.__y_res), interpolation=cv2.INTER_AREA)
        return frame
