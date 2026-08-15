"""Precise PE import scanner: which DLLs does the llama-cpp CUDA build need,
and which are missing from the system? This tells us the EXACT blocker
before we install anything (per diagnosis discipline)."""
import os, re, glob, sys

LIB = r"C:/Users/WwW/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/llama_cpp/lib"
dlls = glob.glob(os.path.join(LIB, "*.dll"))
print("=== DLLs present in llama_cpp/lib ===")
for d in dlls:
    print(" ", os.path.basename(d))

# crude PE import-name extractor: find ASCII runs ending in ".dll" / ".DLL"
IMPORT_RE = re.compile(rb'[ -~]{2,}\.(dll|DLL)')

def imports_of(path):
    data = open(path, "rb").read()
    names = set()
    for m in IMPORT_RE.finditer(data):
        try:
            s = m.group(0).decode("ascii").strip()
        except Exception:
            continue
        # filter noise: real DLL names are short, no spaces, contain letters
        if " " in s or len(s) > 30 or len(s) < 6:
            continue
        names.add(s.lower())
    return names

# search dirs for existence
SEARCH_DIRS = [
    r"C:/Windows/System32",
    r"C:/Windows/SysWOW64",
    LIB,
    r"C:/Users/WwW/AppData/Local/hermes/hermes-agent/venv/Scripts",
    r"C:/Users/WwW/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/llama_cpp",
]
def find_dll(name):
    for d in SEARCH_DIRS:
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    # also check PATH
    return None

print("\n=== Import requirements per DLL ===")
for d in sorted(dlls):
    imps = imports_of(d)
    if imps:
        print(f"\n{os.path.basename(d)}:")
        for n in sorted(imps):
            loc = find_dll(n)
            flag = "OK" if loc else "*** MISSING ***"
            print(f"   {n:28s} {flag}")

# system-wide search for any cudart / cublas / nvrtc to be sure
print("\n=== system-wide CUDA runtime search ===")
import subprocess
for pat in ["cudart64*.dll", "cublas64*.dll", "nvrtc64*.dll", "nvrtc-builtins64*.dll", "nvcuda.dll", "cufft64*.dll", "curand64*.dll"]:
    r = subprocess.run(["cmd", "/c", "dir", "/s", "/b", r"C:\\"+pat],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip().lower().endswith(".dll")]
    print(f"{pat}: {len(lines)} found -> {lines[:5]}")
