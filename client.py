import os
import socket
import time

sock = None

connected = False
ip = 'localhost'
port = 39990

while True:
    try:
        if not connected:
            sock = socket.socket()         
            sock.connect((ip, port))
            sock.settimeout(120)
            connected = True
            print ('Connected in: ' + time.asctime())        
        if connected:
            sock.send('ping'.encode())
            try:
                data = sock.recv(1024)
            except socket.timeout:
                connected = False
            if data.decode() == 'pong':
                print ('Pong ')
            else:
                sock.close()
                connected = False  
            time.sleep(10)
    except (ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError) as error:
        print ('Server not found ' + time.asctime())
        connected = False
        time.sleep(10)
sock.close()

