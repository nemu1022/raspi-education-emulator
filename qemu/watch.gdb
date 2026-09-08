target remote localhost:1234

break *0x8064
commands
silent
printf "LED_ON\n"
continue
end

break *0x8078
commands
silent
printf "LED_OFF\n"
continue
end

continue