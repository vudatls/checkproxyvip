import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from proxy_checker import ProxyChecker
from sys import stdout
from colorama import Fore, Style
import argparse

lock = threading.Lock()

# Lock to control concurrent access to stdout
def write(arg):
    lock.acquire()
    stdout.flush()
    print(arg)
    lock.release()

class ProxyCheck:
    def __init__(self):
        print('Loading..')
        self.checker = ProxyChecker()
        self.checked_proxies = set()  # Set để lưu các proxy đã kiểm tra

    def check(self, proxy, port):
        # Gắn port vào proxy nếu proxy không có port
        if ':' not in proxy:
            proxy = f"{proxy}:{port}"

        retries = 3
        for attempt in range(retries):
            try:
                # Kiểm tra proxy qua proxy_checker
                c = self.checker.check_proxy(proxy)

                # Nếu proxy sống, kiểm tra và lưu vào file
                if c:
                    write(Fore.GREEN + f'[ALIVE] {proxy} | {c["anonymity"]} | Timeout: {str(c["timeout"])} {c["country_code"]}' + Style.RESET_ALL + ' ' + c['protocols'][0])
                    # Lưu proxy vào file nếu chưa được lưu
                    self.save_to_file(proxy)
                    return
                else:
                    write(Fore.RED + f'[DEAD] {proxy}' + Style.RESET_ALL)
                    return  # Không lưu proxy chết vào tệp

            except Exception as e:
                write(Fore.YELLOW + f'[ERROR] {proxy} - Attempt {attempt+1}/{retries}: {e}' + Style.RESET_ALL)
                if attempt < retries - 1:
                    time.sleep(2)  # Wait before retrying
                else:
                    write(Fore.RED + f'[DEAD] {proxy} - Max retries reached' + Style.RESET_ALL)
                    return  # Không lưu proxy chết vào tệp

    def save_to_file(self, proxy):
        """Save only live proxies to the file (without API details)"""
        # Kiểm tra xem proxy đã được lưu chưa, nếu chưa thì mới lưu
        if proxy not in self.checked_proxies:
            self.checked_proxies.add(proxy)  # Thêm proxy vào set để tránh lưu trùng
            file_name = 'alive_proxies.txt'  # Tất cả proxy sống sẽ được lưu vào tệp này
            with open(file_name, 'a', encoding='UTF-8') as f:
                f.write(proxy + '\n')

# Main function for executing the proxy check
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Proxy Check Tool")
    parser.add_argument('thread_count', type=int, help="Number of threads to use")
    parser.add_argument('proxy_file', type=str, help="Path to the proxy list file")
    parser.add_argument('output_file', type=str, help="Path to save the output")
    parser.add_argument('port', type=int, help="Port to append if not present in proxy")

    args = parser.parse_args()

    # Get arguments from the command line
    thread_count = args.thread_count
    proxy_file = args.proxy_file
    output_file = args.output_file
    port = args.port

    # Ensure that the proxy file exists
    if not os.path.isfile(proxy_file):
        print(f"File '{proxy_file}' not found. Please check the file path and try again.")
        return

    try:
        with open(proxy_file, 'r', encoding='UTF-8') as file:
            proxy_list = [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print('Loading proxies...')
    
    pc = ProxyCheck()

    # Using ThreadPoolExecutor for better thread management
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(pc.check, proxy, port) for proxy in proxy_list]

        for future in as_completed(futures):
            future.result()  # To capture exceptions raised in the threads

    print(f"Results saved to {output_file}")
    print('Finished.')

if __name__ == '__main__':
    main()

