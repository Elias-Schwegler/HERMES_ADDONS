#!/usr/bin/env python3
# Coder-loop benchmark: drive Studio's agentic coder (Ornith + enable_tools) on 10
# problems. For each, the model must write a function file + self-test + loop until
# correct. We then INDEPENDENTLY verify by running our OWN asserts against the file.
import json, subprocess, time, os, urllib.request

SKEY = os.environ.get("STUDIO_API_KEY", "sk-unsloth-REPLACE_ME")  # never hardcode — export STUDIO_API_KEY
URL  = "http://127.0.0.1:8888/v1/chat/completions"
SBX  = "/home/elias/studio_sandbox/_default"
LOG  = "/tmp/coder_benchmark/progress.log"
os.makedirs("/tmp/coder_benchmark", exist_ok=True)

PROBLEMS = [
 ("solution1.py","is_prime(n)","returns True if n is a prime number, else False",
  "import solution1 as s\nassert s.is_prime(2) and s.is_prime(13) and s.is_prime(97)\nassert not s.is_prime(1) and not s.is_prime(15) and not s.is_prime(4)"),
 ("solution2.py","merge_intervals(intervals)","takes a list of [start,end] integer intervals and merges all overlapping ones, returning a new sorted list of [start,end]",
  "import solution2 as s\nassert s.merge_intervals([[1,3],[2,6],[8,10],[15,18]])==[[1,6],[8,10],[15,18]]\nassert s.merge_intervals([[1,4],[4,5]])==[[1,5]]"),
 ("solution3.py","two_sum(nums, target)","returns a list of two distinct indices [i,j] such that nums[i]+nums[j]==target",
  "import solution3 as s\nr=s.two_sum([2,7,11,15],9); assert sorted(r)==[0,1]\nr=s.two_sum([3,2,4],6); assert sorted(r)==[1,2]"),
 ("solution4.py","valid_parentheses(string)","returns True if the brackets (), [], {} in the string are correctly balanced and nested, else False",
  "import solution4 as s\nassert s.valid_parentheses('()[]{}')\nassert s.valid_parentheses('')\nassert not s.valid_parentheses('(]')\nassert not s.valid_parentheses('([)]')"),
 ("solution5.py","fibonacci(n)","returns the n-th Fibonacci number, 0-indexed where fibonacci(0)==0 and fibonacci(1)==1",
  "import solution5 as s\nassert s.fibonacci(0)==0 and s.fibonacci(1)==1\nassert s.fibonacci(10)==55 and s.fibonacci(20)==6765"),
 ("solution6.py","binary_search(arr, target)","performs binary search on a sorted ascending list arr and returns the index of target, or -1 if not present",
  "import solution6 as s\nassert s.binary_search([1,3,5,7,9,11],7)==3\nassert s.binary_search([1,3,5,7,9,11],4)==-1\nassert s.binary_search([],5)==-1"),
 ("solution7.py","word_count(text)","returns a dict mapping each whitespace-separated word to the number of times it appears in text",
  "import solution7 as s\nassert s.word_count('the cat the dog the')=={'the':3,'cat':1,'dog':1}"),
 ("solution8.py","reverse_words(text)","returns a string with the order of whitespace-separated words reversed",
  "import solution8 as s\nassert s.reverse_words('hello world foo')=='foo world hello'\nassert s.reverse_words('a')=='a'"),
 ("solution9.py","gcd(a, b)","returns the greatest common divisor of two positive integers a and b",
  "import solution9 as s\nassert s.gcd(48,18)==6 and s.gcd(7,13)==1 and s.gcd(100,10)==10"),
 ("solution10.py","flatten(nested)","takes a list that may contain nested lists of arbitrary depth and returns a single flat list of all elements, in order",
  "import solution10 as s\nassert s.flatten([1,[2,[3,4],5],[6]])==[1,2,3,4,5,6]\nassert s.flatten([])==[]\nassert s.flatten([[[[7]]]])==[7]"),
]

def log(m):
    print(m, flush=True)
    with open(LOG, "a") as f: f.write(m + "\n")

def ask(prompt):
    body = json.dumps({"model":"deepreinforce-ai/Ornith-1.0-35B-GGUF","enable_tools":True,
                       "messages":[{"role":"user","content":prompt}],"max_tokens":3500,"stream":True}).encode()
    req = urllib.request.Request(URL, data=body,
            headers={"Authorization":f"Bearer {SKEY}","Content-Type":"application/json"})
    text = ""
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            for raw in r:
                line = raw.decode("utf-8","ignore").strip()
                if not line.startswith("data:"): continue
                d = line[5:].strip()
                if d == "[DONE]": break
                try:
                    j = json.loads(d)
                    delta = j.get("choices",[{}])[0].get("delta",{}).get("content")
                    if delta: text += delta
                except Exception: pass
    except Exception as e:
        text += f"\n[REQUEST ERROR: {e}]"
    return text

def verify(fname, vpy):
    path = os.path.join(SBX, fname)
    if not os.path.exists(path): return "FAIL(no-file)"
    try:
        p = subprocess.run(["python3","-c",vpy], cwd=SBX, capture_output=True, timeout=40)
        return "PASS" if p.returncode == 0 else "FAIL(assert)"
    except Exception:
        return "FAIL(timeout)"

log(f"[{time.strftime('%H:%M:%S')}] === CODER BENCHMARK START — 10 problems, agentic loop (Studio+Ornith, studio_sandbox) ===")
npass = 0
for i,(fname,sig,spec,vpy) in enumerate(PROBLEMS, 1):
    try: os.remove(os.path.join(SBX, fname))
    except Exception: pass
    t0 = time.time()
    prompt = (f"Use your sandbox tools (write files, run python3). Create a file named {fname} that defines a "
              f"Python function {sig} which {spec}. Put any test/demo code under an "
              f"`if __name__ == '__main__':` block so the file imports cleanly. Then test it by running "
              f"python3 {fname} in the sandbox; if it is wrong, fix the file and rerun until correct. "
              f"When the function is correct, reply with exactly: RESULT=PASS")
    out = ask(prompt)
    said = "YES" if "RESULT=PASS" in out else "no"
    v = verify(fname, vpy)
    dt = int(time.time() - t0)
    if v == "PASS": npass += 1
    log(f"[{time.strftime('%H:%M:%S')}] P{i:<2d} {fname:<14s} model_said_pass={said:<3s} independent={v:<13s} {dt:>3d}s   [tally {npass}/{i}]")
log(f"[{time.strftime('%H:%M:%S')}] === BENCHMARK DONE: {npass}/10 independently verified PASS ===")
