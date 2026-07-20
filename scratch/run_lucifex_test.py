import subprocess

try:
    res = subprocess.run(
        [r'C:\Users\gabri\AppData\Local\Programs\Lucifex\Lucifex.exe'],
        capture_output=True,
        text=True,
        timeout=8
    )
    print("RC:", res.returncode)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
except subprocess.TimeoutExpired as e:
    print("TIMEOUT - still running")
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr)
except Exception as e:
    print("Error:", e)
