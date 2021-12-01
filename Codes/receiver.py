import struct
from socket import *
import os
import math
from sender import create_file_md5
import json

#It's the main function of server, it is responsible for receive the file from the client
#The basic run step is:
#1. Create the server socket and accept the connection from client.
#2. Receive the file list from sender.
#3. For each file, receiver create the step index to for the different situation of this file.
#4. Step index 0: The file is same with the sender's file.
#   Step index 1: This file doesn't exist in receiver.
#   Step index 2: This file has not compeletly received.
#   Step index 3: Needs more file info such as modify time and md5 value to judge the next step index.
#   Step index 4: Sender's file has updated.
#   Step index 5: All the file in this list has been checked. Receiver needs to receive a new file list. Go back to the step2.
def receive_file():
    global step_index
    receiver_socket = socket(AF_INET, SOCK_STREAM)
    receiver_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    receiver_socket.bind(('', 21000))
    receiver_socket.listen(128)
    while True:
        connection_socket, sender_addr = receiver_socket.accept()
        while True:
            try:
                file_list_b = connection_socket.recv(2000)
                file_list_str = file_list_b.decode()
                file_list = json.loads(file_list_str)
                for each_file in file_list:
                    if not os.path.exists(each_file):
                        if not os.path.exists(each_file + '.lefting'):
                            step_index = 1 #This file doesn't exist in receiver.
                            pre_for_recv(step_index, connection_socket, each_file)
                        else:
                            step_index = 2 #This file has not compeletly received.
                            pre_for_recv(step_index, connection_socket, each_file)
                    else:
                        step_index = 3 #Needs more file info such as modify time and md5 value
                        file_mtime,file_md5,recv_mtime,recv_md5 = request_more_info(step_index, connection_socket, each_file)
                        if file_md5 == recv_md5:
                            step_index = 0 #This file is same with the sender's file.
                            step_index_b = struct.pack('!I', step_index)
                            connection_socket.send(step_index_b)
                        else:
                            if recv_mtime > file_mtime:
                                step_index = 0 #This file is same with the sender's file.
                                step_index_b = struct.pack('!I', step_index)
                                connection_socket.send(step_index_b)
                            else:
                                step_index = 4 #Sender's file has updated.
                                step_index_b = struct.pack('!I', step_index)
                                connection_socket.send(step_index_b)
                                file_size_b = connection_socket.recv(8)
                                file_size = struct.unpack('!Q', file_size_b)[0]
                                receive(each_file, file_size, step_index, connection_socket)
                step_index = 5 #All the file in this list has been checked, it needs to receive a new file list.
                step_index_b = struct.pack('!I', step_index)
                connection_socket.send(step_index_b)
            except Exception as e:
                print(str(e))
                break


#Send the step indx to sender and get the file size from sender
def pre_for_recv(step_index, connection_socket, each_file):
    step_index_b = struct.pack('!I', step_index)
    connection_socket.send(step_index_b)
    connection_socket.send(each_file.encode())
    file_size_b = connection_socket.recv(8)
    file_size = struct.unpack('!Q', file_size_b)[0]
    receive(each_file, file_size, step_index, connection_socket)

#Ask for the file modify time and md5 value from sender.
def request_more_info(step_index, connection_socket, each_file):
    step_index_b = struct.pack('!I', step_index)
    connection_socket.send(step_index_b)
    connection_socket.send(each_file.encode())
    file_dict_b = connection_socket.recv(1500)
    file_dict = json.loads(file_dict_b)
    file_mtime = file_dict['fmtime']
    file_md5 = file_dict['fmd5']
    recv_mtime = os.path.getmtime(each_file)
    recv_md5 = create_file_md5(each_file)
    return file_mtime,file_md5,recv_mtime,recv_md5


# Receive the whole file from sender. If the step index is 2, then delete the unfinished file. If the step index is 4, deldete the old file.
def receive(file_name, file_size, step_index, connection_socket):
    if step_index == 2:
        os.remove(file_name + '.lefting')
    if step_index == 4:
        os.remove(file_name)
    path, rest_file_name = os.path.split(file_name)
    if not path == '':#If the folder doesn't exist, then create the folder.
        is_exist_path = os.path.exists(path)
        if not is_exist_path:
            os.makedirs(path)
    file = open(file = file_name + '.lefting',mode = 'wb') #Before the receiver receive the whole file, the file name will have '.lefting' as suffix
    block_size = 1024*1024*3
    total_index = math.ceil(file_size/ block_size)
    for block_index in range(total_index):
        print('Receive process:', block_index, '/', total_index)
        step_index_b = struct.pack('!I', step_index)
        connection_socket.send(step_index_b)
        block_dict = {'block_index': block_index, 'block_size': block_size}#The block info for sender so that the sender will send the correct block to receiver
        block_dict_str = json.dumps(block_dict)
        connection_socket.send(block_dict_str.encode())
        content_length_b = connection_socket.recv(8)
        content_length = struct.unpack('!Q', content_length_b)[0]
        content_b = b''
        while len(content_b) < content_length:
            content_b += connection_socket.recv(content_length)
        file.write(content_b)

    step_index = 0
    step_index_b = struct.pack('!I', step_index)
    connection_socket.send(step_index_b)
    file.close()
    os.rename(file_name + '.lefting', file_name) #Delete the suffix '.lefting', which means the file has alreay received.