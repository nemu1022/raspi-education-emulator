#define GPIO_BASE       (volatile int *)0x3f200000
#define GPFSEL1         (GPIO_BASE + 1)
#define GPSET0          (GPIO_BASE + 7)
#define GPCLR0          (GPIO_BASE + 10)

#define GPFSEL_VEC1     1
#define LED_PORT        10