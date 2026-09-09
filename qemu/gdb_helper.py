import gdb
import json


def inject_switches(var_name, ports, state_path):

    try:
        with open(state_path) as f:
            states = json.load(f)
    except Exception as e:
        print(f"[inject_switches] failed: {e}")
        states = {}

    value = 0

    for name, port in ports.items():
        if states.get(name):
            value |= (1 << port)

    gdb.execute(f"set variable {var_name} = {value}")

    print(f"SWITCH_INJECTED={value} states={states}")

def check_led_write(kind, line, gpfsel_addr, bit_offset):

    try:
        inferior = gdb.selected_inferior()
        mem = inferior.read_memory(gpfsel_addr, 4)
        value = int.from_bytes(mem, byteorder="little")
    except Exception as e:
        print(f"[check_led_write] failed to read GPFSEL: {e}")
        value = 0

    # 該当ポートの3ビットを取り出す (000=入力, 001=出力)
    field = (value >> bit_offset) & 0b111
    is_output = (field == 0b001)

    if is_output:
        # 出力設定されている場合のみ、実際にLEDへ反映する
        print(f"LED_{kind}:{line}")
    else:
        # 入力のままなら、書き込み自体はログに残すが無視する
        print(f"LED_IGNORED:{line} (field={field:03b}, not output)")