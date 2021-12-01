from sender import *
from receiver import *
import argparse
from threading import Thread
import time

#To create the argument of this program
def _argparse():
    parser = argparse.ArgumentParser(description="This is description!")
    parser.add_argument('--ip', action='store', required=True, dest='ip', help='ip')
    return parser.parse_args()

#Create two threads and run them
def main():
    peer_ip = _argparse()
    print('python3 main.py --ip ' + peer_ip.ip)

    #Create two thread on both host, one is working as client, and the other is working as server.
    #So that this host is not only a client, but also a server.
    receiver = Thread(target=receive_file, args=())
    sender = Thread(target=send_file, args=(peer_ip.ip, 21000))

    while True:
        try:
            receiver.start()
            sender.start()
        except:
            pass
        time.sleep(0.3)


if __name__ == '__main__':
    main()
