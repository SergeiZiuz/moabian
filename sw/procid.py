import sys, os, signal, time, errno
import logging as log

def kill_doppelganger(pid_path='/tmp/menu.pid'):
    our_pid=os.getpid()

    if os.path.isfile(pid_path):
        with open(pid_path, 'r') as f:
            twin_pid = int(f.read())
            try:
                print(f'Sending SIGINT to {twin_pid}...', end='')
                os.kill(twin_pid, signal.SIGINT)
                print(f'sent.')
            except OSError as err:
                if err.errno == errno.ESRCH:
                    print(f'no such process.')
                else:
                    print(f'oserror {err}')
            except Exception as e:
                print(f'Unexpected exception {e} which is ok')

    with open(pid_path, 'w') as f:
        f.write(str(our_pid))
    return our_pid

if __name__ == "__main__":
    try:
        pid = kill_doppelganger()
        input(f'This pid={pid}. Press any key to quit...')
    except KeyboardInterrupt:
        print(f'\nCaught SIGINT...exiting in ', end='', flush=True)
        for s in range(3,0,-1):
            print(s, end='.', flush=True)
            time.sleep(1)
        sys.exit()
