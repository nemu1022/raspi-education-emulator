target remote localhost:1234
break blink.c:10
commands
silent
printf "LED_ON\n"
continue
end
break blink.c:18
commands
silent
printf "LED_OFF\n"
continue
end
continue
quit
