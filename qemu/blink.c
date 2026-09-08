#include "const.h"      // 定数の定義を読み込む

// 悪い例: LEDを点灯して消灯する（点灯時間短すぎ）
int main()
{
  // GPIOの機能設定
  *GPFSEL1 = GPFSEL_VEC1;  // #10〜#19の設定

  // LED点灯 (LED_PORTの出力を1にする)
  *GPSET0 = 1 << LED_PORT;

  // ** ここに待ち時間が必要 **
  int i;
  // 空ループで時間をつぶす
  for (i = 0; i < 345000; i++) {}
  
  // LED消灯 (LED_PORTの出力を0にする)
  *GPCLR0 = 1 << LED_PORT;

  return 0;  // init.sに戻る
}
