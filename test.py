import subprocess
d = subprocess.run([f"dir"], shell=True, capture_output=True, text=True)

print(d)