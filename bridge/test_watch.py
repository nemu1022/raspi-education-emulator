import subprocess

proc = subprocess.Popen(
    [
        "gdb-multiarch",
        "-q",
        "-x",
        "watch.gdb",
        "blink.elf"
    ],
    cwd="/workspaces/raspi_education_emulator/qemu",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

while True:

    line = proc.stdout.readline()

    if not line:
        break

    print(line.strip())