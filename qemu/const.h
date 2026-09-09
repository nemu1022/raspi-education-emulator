// GPIOを操作するための番地
#define GPIO_BASE       (volatile int *)0x3f200000
#define GPFSEL0         (GPIO_BASE + 0)  // GPIO #0〜9の機能選択
#define GPFSEL1         (GPIO_BASE + 1)  // GPIO #10〜19の機能選択
#define GPFSEL2         (GPIO_BASE + 2)  // GPIO #20〜29の機能選択
#define GPSET0          (GPIO_BASE + 7)  // 出力値を1にする
#define GPCLR0          (GPIO_BASE + 10) // 出力値を0にする
#define GPLEV0          (GPIO_BASE + 13) // 入力値を読み出す

// GPFSELxに設定する値
#define GPFSEL_VEC1     1   // GPFSEL1用 (#10のみ出力)

// 各装置が接続されているGPIO番号
#define LED_PORT        10  // LED

#define SW1_PORT        13  // SW1

            