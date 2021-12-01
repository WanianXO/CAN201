import json
import time
from socket import *
from os.path import *
import os
import struct
import hashlib

#The main function of client, used for connect and send the file to receiver. The basic step of this function are:
#1. Create the socket and send a connection request to server, if cannot connect, then try to connect again.
#2. Scan all the file under the 'share' folder. And send this file list to receiver.
#3. Receive the step index from receiver, according to the step index to do different things.
#4. Step index 1: send the file
#   Step index 2: send the file
#   Step index 3: Send the file modify time and file md5 value to receiver
#   Step index 4: Send the new file to receciver
#   Step index 5: Break the loop and scan the file again, which means go back to the step 2.
def send_file(receiver_ip, receiver_port):
    while True:
        while True:
            try:
                sender_socket = socket(AF_INET, SOCK_STREAM)
                sender_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sender_socket.connect((receiver_ip, receiver_port))
                break
            except Exception as e:
                time.sleep(0.5)

        while True:
            try:
                total_file_list = scan_file('share')
                file_list_str = json.dumps(total_file_list)
                sender_socket.send(file_list_str.encode())
                while True:
                    recv_step_index_b = sender_socket.recv(4)
                    recv_step_index = struct.unpack('!I', recv_step_index_b)[0]
                    if recv_step_index == 1: #send the file
                        file_name = get_name(sender_socket)
                        send(sender_socket, file_name)
                    elif recv_step_index == 2: #send the file
                        file_name = get_name(sender_socket)
                        send(sender_socket, file_name)
                    elif recv_step_index == 3: #send file modify time and file md5 value to receiver
                        file_name_b = sender_socket.recv(1500)
                        file_name = file_name_b.decode()
                        file_md5 = create_file_md5(file_name)
                        file_mtime = os.path.getmtime(file_name)
                        file_dict = {'fmtime': file_mtime, 'fmd5': file_md5}
                        file_dict_str = json.dumps(file_dict)
                        file_dict_b = file_dict_str.encode()
                        sender_socket.send(file_dict_b)
                        recv_step_index_b = sender_socket.recv(4)
                        recv_step_index = struct.unpack('!I', recv_step_index_b)[0]
                        if recv_step_index == 0: #Do nothing
                            pass
                        elif recv_step_index == 4: #Send the file
                            file_size = os.path.getsize(file_name)
                            file_size_b = struct.pack('!Q', file_size)
                            sender_socket.send(file_size_b)
                            send(sender_socket, file_name)
                    elif recv_step_index == 5: # Break the loop and scan the file list again
                        break
            except:
                break

def get_name(sender_socket):
    file_name_b = sender_socket.recv(1500)
    file_name = file_name_b.decode()
    file_size = os.path.getsize(file_name)
    file_size_b = struct.pack('!Q', file_size)
    sender_socket.send(file_size_b)
    return file_name

def send(sender_socket, file_name):
    while True:
        recv_step_index_b = sender_socket.recv(4)
        recv_step_index = struct.unpack('!I', recv_step_index_b)[0]
        if recv_step_index == 0:
            break
        else:
            block_dict_b = sender_socket.recv(1500)
            block_dict_str = block_dict_b.decode()
            block_dict = json.loads(block_dict_str)
            block_index = block_dict['block_index']
            block_size = block_dict['block_size']
            send_content = create_send_content(file_name, block_size, block_index)
            sender_socket.send(send_content)

#Scan the whole file under the folder 'share'.
def scan_file(file_dir):
    is_exists_path = os.path.exists(file_dir)
    if not is_exists_path:
        os.mkdir(file_dir)  #If the 'share' folder doesn't exisit, then create it.
    file_list = []
    file_folder_list = os.listdir(file_dir)  #Obtain the file name and folder under the 'share' folder
    for file_folder_name in file_folder_list:
        suffixName = file_folder_name[-8:] #Check whether the file has suffix '.lefting'
        if suffixName != '.lefting':
            if isfile(join(file_dir, file_folder_name)):
                file_list.append(join(file_dir, file_folder_name))
            else:
                file_list.extend(scan_file(join(file_dir, file_folder_name)))
    return file_list

#Create the md5 value of the file
def create_file_md5(file_name):
    file = open(file = file_name, mode= 'rb')
    file.seek(0)
    content = file.read(1024*1024*4)
    content_md5 = hashlib.md5(content).hexdigest()
    file.close()
    return content_md5

#Read the file at the corresponding position, the size of each block is equal to the block size.
def create_send_content(each_file, block_size, block_index):
    file = open(file = each_file, mode = 'rb')
    file.seek(block_size*block_index) #To seek the right block and read it
    content = file.read(block_size)
    file.close()
    content_length = len(content) #use content length to avoid the error at the end of file. The length of last block won't be equal to the block size.
    content_length_b = struct.pack('!Q', content_length)
    return content_length_b + content