CC      = arm-none-eabi-gcc
AS      = arm-none-eabi-as
LD      = arm-none-eabi-ld
OBJCOPY = arm-none-eabi-objcopy

all: blink.img

init.o: init.s
	$(AS) init.s -o init.o

blink.o: blink.c const.h
	$(CC) -c blink.c -o blink.o -O0

blink.elf: init.o blink.o
	$(LD) -m armelf init.o blink.o -o blink.elf

blink.img: blink.elf
	$(OBJCOPY) blink.elf -O binary blink.img

clean:
	rm -f *.o *.elf *.img