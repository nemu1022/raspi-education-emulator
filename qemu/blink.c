#include "const.h"

static void delay(volatile unsigned int count) {
    while (count--) ;
}

int main(void) {
    *GPFSEL1 = GPFSEL_VEC1;      // GPIO10を出力に設定

    while (1) {
        *GPSET0 = 1 << LED_PORT;  // 点灯
        delay(345000);
        *GPCLR0 = 1 << LED_PORT;  // 消灯
        delay(345000);
    }
    return 0;
}