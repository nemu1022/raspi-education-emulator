import asyncio
import json
import os
import re
import socket
import subprocess

from websockets.server import serve


# ============================================
# 設定
# ============================================

# QEMU関連ファイルを配置するディレクトリ
QEMU_DIR = "/workspaces/raspi_education_emulator/qemu"

# スイッチ状態を保存するJSONファイル
SWITCH_STATE_PATH = f"{QEMU_DIR}/switch_state.json"

# 教材上では345000回の空ループを約0.5秒として扱う
DELAY_RATIO = 0.5 / 345000


# ============================================
# 実行中プロセス・状態
# ============================================

qemu_process = None
gdb_process = None
gdb_monitor_task = None

# 現在実行しているmain.c
# 待ち時間の解析に使用する
current_main_code = ""


# ============================================
# const.h解析
# ============================================

def parse_switch_ports(const_code: str) -> dict:

    ports = {}

    pattern = r"#define\s+SW(\d+)_PORT\s+(\d+)"

    for number, port in re.findall(pattern, const_code):
        ports[f"sw{number}"] = int(port)

    return ports

def parse_led_port(const_code: str) -> int:
    m = re.search(r"#define\s+LED_PORT\s+(\d+)", const_code)
    return int(m.group(1)) if m else 10   # 見つからなければデフォルト10

def gpfsel_address_and_bit(port: int):
    GPIO_BASE = 0x3f200000
    reg_index = port // 10        # GPFSEL0/1/2のどれか
    bit_offset = (port % 10) * 3  # レジスタ内のビット位置
    address = GPIO_BASE + reg_index * 4
    return address, bit_offset

# ============================================
# watch.gdb 自動生成
# ============================================

def generate_gdb_script(
    main_code: str,
    switch_ports: dict,
    led_port: int          # ← 追加
):

    lines = main_code.splitlines()

    script_lines = ["target remote localhost:1234"]

    gpset_patterns = ["GPSET0", "0x3f20001c", "0x3F20001C"]
    gpclr_patterns = ["GPCLR0", "0x3f200028", "0x3F200028"]

    gplev_pattern = re.compile(
        r"(\w+)\s*=\s*\*(GPLEV0|\(int\s*\*\)\s*0x3[fF]200034)"
    )

    ports_repr = repr(switch_ports)

    # LED_PORTに対応するGPFSELアドレス・ビット位置を計算
    gpfsel_addr, bit_offset = gpfsel_address_and_bit(led_port)

    # gdb_helper.pyの読み込みは1回だけで良いので、スクリプト先頭に置く
    script_lines.append(
        f'python exec(open("{QEMU_DIR}/gdb_helper.py").read())'
    )

    for i, line in enumerate(lines, start=1):

        if any(p in line for p in gpset_patterns):
            script_lines += [
                f"break blink.c:{i}",
                "commands",
                "silent",
                f'python check_led_write("ON", {i}, {gpfsel_addr}, {bit_offset})',
                "continue",
                "end"
            ]

        if any(p in line for p in gpclr_patterns):
            script_lines += [
                f"break blink.c:{i}",
                "commands",
                "silent",
                f'python check_led_write("OFF", {i}, {gpfsel_addr}, {bit_offset})',
                "continue",
                "end"
            ]

        match = gplev_pattern.search(line)

        if not match:
            continue

        var_name = match.group(1)

        usage_pattern = re.compile(r"\b" + re.escape(var_name) + r"\b")
        target_line = None

        for j in range(i, len(lines)):
            if usage_pattern.search(lines[j]):
                target_line = j + 1
                break

        if target_line is None:
            target_line = i

        script_lines += [
            f"break blink.c:{target_line}",
            "commands",
            "silent",
            f'python inject_switches("{var_name}", {ports_repr}, "{SWITCH_STATE_PATH}")',
            "continue",
            "end"
        ]

    script_lines.append("continue")
    script_lines.append("quit")

    with open(f"{QEMU_DIR}/watch.gdb", "w") as file:
        file.write("\n".join(script_lines) + "\n")


# ============================================
# 空ループによる待ち時間推定
# ============================================

def estimate_delay(
    main_code: str,
    start_line: int,
    end_line: int
) -> float:
    """
    GPIO操作間に存在するforループの回数から、
    教材上の待ち時間を推定する。

    345000回 ≒ 0.5秒として扱う。
    """

    lines = main_code.splitlines()

    for_pattern = re.compile(
        r"for\s*\("
        r"[^;]*;"
        r"\s*\w+\s*<\s*(\d+)\s*;"
    )

    total_count = 0

    for line in lines[max(start_line, 0):end_line]:

        match = for_pattern.search(line)

        if match:
            total_count += int(match.group(1))

    return total_count * DELAY_RATIO


# ============================================
# Cソース・状態ファイル生成
# ============================================

def build_sources(main_code: str, const_code: str):

    global current_main_code
    current_main_code = main_code

    with open(f"{QEMU_DIR}/const.h", "w") as file:
        file.write(const_code)

    with open(f"{QEMU_DIR}/blink.c", "w") as file:
        file.write(main_code)

    switch_ports = parse_switch_ports(const_code)

    initial_switch_states = {name: False for name in switch_ports}

    with open(SWITCH_STATE_PATH, "w") as file:
        json.dump(initial_switch_states, file)

    led_port = parse_led_port(const_code)   # ← 追加

    generate_gdb_script(main_code, switch_ports, led_port)   # ← led_portを渡す


# ============================================
# QEMU GDBスタブ起動待ち
# ============================================

async def wait_for_gdbstub(
    host="127.0.0.1",
    port=1234,
    timeout=10
):

    for _ in range(timeout * 10):

        try:

            sock = socket.create_connection(
                (host, port),
                timeout=0.1
            )

            sock.close()

            return True

        except OSError:

            await asyncio.sleep(0.1)

    return False


# ============================================
# 古いQEMU / GDBを終了
# ============================================

async def cleanup_old_processes():

    global qemu_process
    global gdb_process
    global gdb_monitor_task

    # 古いプロセスを終了
    subprocess.run(
        ["pkill", "-9", "-f", "qemu-system-arm"]
    )

    subprocess.run(
        ["pkill", "-9", "-f", "gdb-multiarch"]
    )

    qemu_process = None
    gdb_process = None

    # GDB監視タスクの終了を待つ
    if gdb_monitor_task is not None:

        try:

            await asyncio.wait_for(
                gdb_monitor_task,
                timeout=3
            )

        except asyncio.TimeoutError:

            print(
                "WARNING: "
                "gdb_monitor_task did not finish in time"
            )

        except Exception:
            pass

        gdb_monitor_task = None

    # ポート1234の解放を少し待つ
    await asyncio.sleep(0.5)


# ============================================
# GDB出力監視
# ============================================

async def monitor_gdb(websocket):

    global gdb_process

    # QEMUのGDBスタブ起動を待つ
    ready = await wait_for_gdbstub()

    if not ready:

        print(
            "GDB TIMEOUT: QEMU stub not ready"
        )

        try:
            await websocket.send("QEMU_ERROR")
        except Exception:
            pass

        return

    print("GDB START")

    # GDB起動
    gdb_process = subprocess.Popen(
        [
            "stdbuf",
            "-oL",
            "gdb-multiarch",
            "-q",
            "-x",
            "watch.gdb",
            "blink.elf"
        ],
        cwd=QEMU_DIR,

        # 実ターミナルをGDBへ渡さない
        stdin=subprocess.DEVNULL,

        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    previous_line = 0

    while True:

        # GDB出力を非同期で1行読み込む
        line = await asyncio.to_thread(
            gdb_process.stdout.readline
        )

        if not line:
            break

        line = line.strip()

        print(
            "GDB:",
            line
        )

        # --------------------------------------------
        # GDB対象プログラム終了
        # --------------------------------------------

        if "[Inferior 1" in line:

            print("GDB END")

            try:
                gdb_process.kill()
                gdb_process.wait(timeout=3)

            except Exception:
                pass

            gdb_process = None

            break

        # --------------------------------------------
        # LED_ON / LED_OFF
        # --------------------------------------------

        if (
            line.startswith("LED_ON:")
            or line.startswith("LED_OFF:")
        ):

            label, line_number_text = line.split(":")

            line_number = int(
                line_number_text
            )

            # 前回のGPIO操作との間に存在する空ループから
            # 教材上の待ち時間を計算
            delay = estimate_delay(
                current_main_code,
                previous_line,
                line_number
            )

            if delay > 0:

                print(
                    f"WAIT {delay:.3f}s "
                    f"(line {previous_line} "
                    f"-> {line_number})"
                )

                await asyncio.sleep(delay)

            # LED_ON / LED_OFFをブラウザへ送信
            try:

                await websocket.send(
                    label
                )

            except Exception:
                break

            previous_line = line_number


# ============================================
# WebSocketクライアント処理
# ============================================

async def handler(websocket):

    global qemu_process
    global gdb_process
    global gdb_monitor_task

    async for message in websocket:

        # JSONデコード
        try:

            data = json.loads(
                message
            )

        except json.JSONDecodeError:

            continue

        message_type = data.get(
            "type"
        )

        # ========================================
        # STOP
        # ========================================

        if message_type == "STOP":

            print(
                "STOP REQUEST"
            )

            # GDB終了
            if gdb_process is not None:

                try:
                    gdb_process.kill()
                    gdb_process.wait(timeout=3)

                except Exception:
                    pass

                gdb_process = None

            # QEMU終了
            if qemu_process is not None:

                try:
                    qemu_process.kill()
                    qemu_process.wait(timeout=3)

                except Exception:
                    pass

                qemu_process = None

            await websocket.send(
                "STOPPED"
            )

            continue

        # ========================================
        # SWITCH
        # ========================================

        if message_type == "SWITCH":

            switch_name = data.get(
                "switch"
            )

            pressed = (
                data.get("value") == 1
            )

            # 現在のスイッチ状態を読み込む
            try:

                with open(
                    SWITCH_STATE_PATH,
                    "r"
                ) as file:

                    states = json.load(
                        file
                    )

            except Exception:

                states = {}

            # 対象スイッチの状態を更新
            states[switch_name] = pressed

            # 更新した状態を書き出す
            with open(
                SWITCH_STATE_PATH,
                "w"
            ) as file:

                json.dump(
                    states,
                    file
                )

            print(
                switch_name,
                pressed
            )

            continue

        # ========================================
        # BUILD
        # ========================================

        if message_type != "BUILD":
            continue

        # 前回のQEMU / GDBを終了
        await cleanup_old_processes()

        # blink.c / const.h / watch.gdb生成
        build_sources(
            data.get("main", ""),
            data.get("consts", "")
        )

        # ----------------------------------------
        # ARMプログラムをビルド
        # ----------------------------------------

        result = subprocess.run(
            ["make"],
            cwd=QEMU_DIR,
            capture_output=True,
            text=True
        )

        # ビルド失敗
        if result.returncode != 0:

            print(
                result.stderr
            )

            await websocket.send(
                "BUILD_ERROR"
            )

            continue

        # ビルド成功
        await websocket.send(
            "BUILD_OK"
        )

        # ----------------------------------------
        # QEMU起動
        # ----------------------------------------

        qemu_process = subprocess.Popen(
            [
                "qemu-system-arm",
                "-M",
                "raspi2b",
                "-kernel",
                "blink.elf",
                "-nographic",
                "-s",
                "-S"
            ],
            cwd=QEMU_DIR,

            # QEMUへ実ターミナルを渡さない
            # Ctrl+Cが効かなくなる問題を防止
            stdin=subprocess.DEVNULL,

            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        print(
            "QEMU PID:",
            qemu_process.pid
        )

        # ----------------------------------------
        # GDBスタブ起動確認
        # ----------------------------------------

        ready = await wait_for_gdbstub()

        if not ready:

            try:
                qemu_process.kill()
            except Exception:
                pass

            # QEMUが出したエラーを取得
            if qemu_process.stdout:

                output, _ = qemu_process.communicate(
                    timeout=2
                )

            else:

                output = ""

            print(
                "QEMU FAILED TO START. Output:"
            )

            print(
                output
            )

            await websocket.send(
                "QEMU_ERROR"
            )

            continue

        # QEMU起動完了をブラウザへ通知
        await websocket.send(
            f"QEMU_PID:{qemu_process.pid}"
        )

        await websocket.send(
            "QEMU_STARTED"
        )

        # GDB出力監視開始
        gdb_monitor_task = asyncio.create_task(
            monitor_gdb(
                websocket
            )
        )


# ============================================
# WebSocketサーバー
# ============================================

async def main():
    """
    8765番ポートでWebSocketサーバーを起動する。
    """

    async with serve(
        handler,
        "0.0.0.0",
        8765
    ):

        print(
            "WebSocket Server Started"
        )

        # サーバーを継続動作させる
        await asyncio.Future()


# ============================================
# エントリーポイント
# ============================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nCtrl+C received. Shutting down..."
        )

    finally:

        # QEMU / GDBを確実に終了
        subprocess.run(
            ["pkill", "-9", "-f", "qemu-system-arm"]
        )

        subprocess.run(
            ["pkill", "-9", "-f", "gdb-multiarch"]
        )

        # asyncio.to_thread()のスレッド待ちをせず終了する
        os._exit(0)