import asyncio
import json
import subprocess
import socket
import time

from websockets.server import serve


# ============================================
# グローバル
# ============================================

QEMU_DIR = "/workspaces/raspi_education_emulator/qemu"

qemu_process = None
gdb_process = None
gdb_monitor_task = None


# ============================================
# watch.gdb 自動生成
# ============================================

def generate_gdb_script(main_code: str):

    lines = main_code.splitlines()

    script_lines = ["target remote localhost:1234"]

    gpset_patterns = ["GPSET0", "0x3f20001c", "0x3F20001C"]
    gpclr_patterns = ["GPCLR0", "0x3f200028", "0x3F200028"]

    for i, line in enumerate(lines, start=1):

        if any(p in line for p in gpset_patterns):
            script_lines += [
                f"break blink.c:{i}",
                "commands",
                "silent",
                'printf "LED_ON\\n"',
                "continue",
                "end"
            ]

        if any(p in line for p in gpclr_patterns):
            script_lines += [
                f"break blink.c:{i}",
                "commands",
                "silent",
                'printf "LED_OFF\\n"',
                "continue",
                "end"
            ]

    script_lines.append("continue")
    script_lines.append("quit")   # ← GDBが終了時にプロセスに居座らないよう明示的に終了させる

    with open(f"{QEMU_DIR}/watch.gdb", "w") as f:
        f.write("\n".join(script_lines) + "\n")


# ============================================
# ソース生成
# ============================================

def build_sources(main_code: str, const_code: str):

    with open(f"{QEMU_DIR}/const.h", "w") as f:
        f.write(const_code)

    with open(f"{QEMU_DIR}/blink.c", "w") as f:
        f.write(main_code)

    generate_gdb_script(main_code)


# ============================================
# GDBポート待機
# ============================================

async def wait_for_gdbstub(host="127.0.0.1", port=1234, timeout=10):

    for _ in range(timeout * 10):

        try:
            sock = socket.create_connection((host, port), timeout=0.1)
            sock.close()
            return True
        except OSError:
            await asyncio.sleep(0.1)

    return False


# ============================================
# 古いプロセスを確実に片付ける
# ============================================

async def cleanup_old_processes():

    global qemu_process, gdb_process, gdb_monitor_task

    # ① 先に実プロセスを強制終了する(パイプを閉じさせる)
    subprocess.run(["pkill", "-9", "-f", "qemu-system-arm"])
    subprocess.run(["pkill", "-9", "-f", "gdb-multiarch"])

    qemu_process = None
    gdb_process = None

    # ② プロセスが死ぬとパイプがEOFになり、
    #    readline()がブロックから解放されるので、
    #    ここでタスクの終了を安全に待てる
    if gdb_monitor_task is not None:
        try:
            await asyncio.wait_for(gdb_monitor_task, timeout=3)
        except asyncio.TimeoutError:
            print("WARNING: gdb_monitor_task did not finish in time")
        except Exception:
            pass
        gdb_monitor_task = None

    # OSがポートを解放するまで少し待つ
    await asyncio.sleep(0.5)


# ============================================
# GDB監視
# ============================================

async def monitor_gdb(websocket):

    global gdb_process

    ready = await wait_for_gdbstub()

    if not ready:
        print("GDB TIMEOUT: QEMU stub not ready")
        try:
            await websocket.send("QEMU_ERROR")
        except Exception:
            pass
        return

    print("GDB START")

    gdb_process = subprocess.Popen(
        ["stdbuf", "-oL", "gdb-multiarch", "-q", "-x", "watch.gdb", "blink.elf"],
        cwd=QEMU_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    last_time = None

    while True:

        line = await asyncio.to_thread(gdb_process.stdout.readline)

        if not line:
            break

        line = line.strip()
        print("GDB:", line)

        if "[Inferior 1" in line:
            print("GDB END")
            try:
                gdb_process.kill()
            except Exception:
                pass
            gdb_process = None
            break

        now = time.time()

        if "LED_ON" in line:
            print(f"LED_ON {now:.3f}")
            last_time = now
            try:
                await websocket.send("LED_ON")
            except Exception:
                break

        if "LED_OFF" in line:
            if last_time is not None:
                print(f"LED_OFF {now:.3f} ({now - last_time:.3f}s)")
            try:
                await websocket.send("LED_OFF")
            except Exception:
                break


# ============================================
# WebSocket処理
# ============================================

async def handler(websocket):

    global qemu_process, gdb_monitor_task

    async for message in websocket:

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            continue

        if data.get("type") != "BUILD":
            continue

        print("BUILD REQUEST")

        # 古いプロセスを確実に終了させ、ポート解放を待つ
        await cleanup_old_processes()

        build_sources(data.get("main", ""), data.get("consts", ""))

        result = subprocess.run(
            ["make"],
            cwd=QEMU_DIR,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(result.stderr)
            await websocket.send("BUILD_ERROR")
            continue

        await websocket.send("BUILD_OK")

        # QEMU起動
        qemu_process = subprocess.Popen(
            ["qemu-system-arm", "-M", "raspi2b", "-kernel", "blink.elf",
             "-nographic", "-s", "-S"],
            cwd=QEMU_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        print("QEMU PID:", qemu_process.pid)

        # 本当に起動してポートが開いたか確認する
        ready = await wait_for_gdbstub()

        if not ready:
            # 失敗時はQEMU自体の出力を読んで原因をログに出す
            try:
                qemu_process.kill()
            except Exception:
                pass

            out, _ = qemu_process.communicate(timeout=2) if qemu_process.stdout else ("", "")
            print("QEMU FAILED TO START. Output:")
            print(out)

            await websocket.send("QEMU_ERROR")
            continue

        await websocket.send(f"QEMU_PID:{qemu_process.pid}")
        await websocket.send("QEMU_STARTED")

        gdb_monitor_task = asyncio.create_task(monitor_gdb(websocket))


# ============================================
# メイン
# ============================================

async def main():

    try:
        async with serve(handler, "0.0.0.0", 8765):
            print("WebSocket Server Started")
            await asyncio.Future()

    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    finally:
        print("Shutting down: killing child processes...")
        subprocess.run(["pkill", "-9", "-f", "qemu-system-arm"])
        subprocess.run(["pkill", "-9", "-f", "gdb-multiarch"])


asyncio.run(main())