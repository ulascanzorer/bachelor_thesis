import sys
import time
import requests
import os
from typing import Any, Optional

# utility function(s)
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def robust_request(url: str, data: dict[str, Any], post_request: bool, retry_count: int = 5, timeout: int = 30, headers: dict[str, str] = None) -> dict[str, Any]:
    while True:
        if post_request:
            try:
                if headers:
                    response = requests.post(url, json=data, headers=headers, timeout=timeout)
                else:
                    response = requests.post(url, json=data, timeout=timeout)
            except Exception as err:
                eprint(err)
                if retry_count > 0:
                    eprint("Retrying...")
                    retry_count -= 1
                    time.sleep(3)
                    continue
                else:
                    return { "failure": f"Couldn't connect to {url} after {retry_count} times {timeout} seconds" }
        else:
            try:
                if headers:
                    requests.delete(url, json=data, headers=headers, timeout=timeout)
                else:
                    requests.delete(url, json=data, timeout=timeout)
                return {}
            except:
                eprint("Couldn't delete scroll_id")
                if retry_count > 0:
                    eprint("Retrying...")
                    retry_count -= 1
                    time.sleep(3)
                    continue
                else:
                    return { "failure": f"Couldn't connect to {url} after {retry_count} times {timeout} seconds" }

        try:
            response_json = response.json()
        except:
            eprint("Can't convert response into json, writing response to file 'unexpected_response.txt' in current directory")
            with open("unexpected_response.txt", "w") as f:
                f.write(response.text)
            return { "failure": "Couldn't convert response into json, writing response to file 'unexpected_response.txt" }
        
        return response_json

def annoying_notification() -> None:
    duration = 2 # seconds
    freq = 1200  # Hz
    os.system("play -nq -t alsa synth {} sine {}".format(duration, freq))