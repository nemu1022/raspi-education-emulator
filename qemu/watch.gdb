target remote localhost:1234
python exec(open("/workspaces/raspi_education_emulator/qemu/gdb_helper.py").read())
break blink.c:6
commands
silent
python check_led_write("ON", 6, 1059061764, 0)
continue
end
continue
quit
