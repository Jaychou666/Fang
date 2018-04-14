# -*- coding: utf-8-*-
import sys
import subprocess
import random
import time
import threading
import queue
import os

device_sn = "3F1806118CD240ED"
class AsynchronousFileReader(threading.Thread):
    '''
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''

    def __init__(self, fd, queue):
        threading.Thread.__init__(self)
        self._fd = fd
        self._queue = queue


    def run(self):
        '''The body of the tread: read lines and put them on the queue.'''
        for line in iter(self._fd.readline, ''):
            self._queue.put(line)

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive() and self._queue.empty()

def consume(command, fileName):
    '''
    Example of how to consume standard output and standard error of
    a subprocess asynchronously without risk on deadlocking.
    '''

    # Launch the command as subprocess.
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Launch the asynchronous readers of the process' stdout and stderr.
    stdout_queue =queue.Queue()
    stdout_reader = AsynchronousFileReader(process.stdout, stdout_queue)
    stdout_reader.setDaemon(True)
    stdout_reader.start()
    stderr_queue = queue.Queue()
    stderr_reader = AsynchronousFileReader(process.stderr, stderr_queue)
    stderr_reader.setDaemon(True)
    stderr_reader.start()

    wakeup_count = 0
    flag = False
    recog_count = 0
    recog_false_count  = 0
    flag_crash = False
    count = 0

    # Check the queues if we received some output (until there is nothing more to get).
    while not stdout_reader.eof() or not stderr_reader.eof():
        # Show what we received from standard output.
        while not stdout_queue.empty():
            line = stdout_queue.get().decode("utf-8", errors = "ignore")
            #save_memory(device_sn + "_all_log.txt", line.encode("utf-8").encode("gbk").strip())
            #save_memory(device_sn + "_all_log.txt", str(line))
            if line.find("wakeup successfully") != -1:
                wakeup_count = wakeup_count + 1
                flag = True
                print(line + "wakeup success count = " + str(wakeup_count))
                save_memory(device_sn + "_wakeup_result.txt", str(wakeup_count))
            elif line.find("RenderVoiceInputText") != -1 :
                if line.find("callback==>all directives") != -1:
                    text = line[(line.rindex("text") + 7) : (line.rindex("type") -3)]
                    print(text)
                    save_memory(device_sn + "_recognize_result.txt", str(wakeup_count) + ".pcm:" + text.encode("utf-8"))
            elif line.find("AutoTest")!= -1 and line.find("asr.finish") != -1:
                save_memory(device_sn + "_asr_finish_all.txt", line)
                recog_count = recog_count + 1
                print("recog total count:"  + str(recog_count))
                if line.find("Speech Recognize success") == -1:
                    recog_false_count = recog_false_count + 1
                    save_memory(device_sn + "_recognize_false.txt",line)
                    print(line.encode("utf-8"))
                    print("false recog count:" + str(recog_false_count))
                else:
                    print("false recog count:" + str(recog_false_count))
            elif line.find("AutoTest")!= -1 and line.find("asr.partial") != -1:
                #save_memory(device_sn + "_recog_result.txt", line + str("\n"))
                if line.find("final_result") != -1:
                    result = line.split("\"")[-6] + ":" + line.split("\"")[-12]
                    print(result)
                    save_memory(device_sn + "_recog_result.txt", result + str("\n"))
            elif line.find("FATAL") != -1 or line.find("backtrace") != -1:
                save_memory(device_sn + "_crash.txt", line)
                flag_crash = True
                print(line.encode("utf-8"))
            else:
                pass
            if flag_crash:
                save_memory(device_sn + "_crash.txt", line)
                count = count + 1
                if count > 500:
                    count = 0
                    flag_crash = False
                else:
                    print(line)

        # Show what we received from standard error.
        while not stderr_queue.empty():
            line = stderr_queue.get()
            print('Received line on standard error: ' + repr(line))

        # Sleep a bit before asking the readers again.
        time.sleep(.1)

    # Let's be tidy and join the threads we've started.
    stdout_reader.join()
    stderr_reader.join()

    # Close subprocess' file descriptors.
    process.stdout.close()
    process.stderr.close()

def save_memory(filename, content):
    with open(filename, "a+") as f:
        f.write(content)

def getDeviceList():
    device_sn_list = []
    file = os.popen("adb devices")
    for line in file.readlines():
        if line.find("List of devices attached") != -1:
            continue
        else:
            device_sn_list.append(line.split("\t")[0])
            print(line)
    file.close()
    return device_sn_list

if __name__ == '__main__':
    # The main flow:
    # if there is an command line argument 'produce', act as a producer
    # otherwise be a consumer (which launches a producer as subprocess).
#    for device_sn in getDeviceList():
#        print(device_sn)
    while True:
        consume("adb -s {0} logcat -v time ".format(device_sn).split(), time.strftime('%Y%m%d%H%M%S'))
        time.sleep(2)