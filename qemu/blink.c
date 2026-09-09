int main()
{
  // GPIOの機能設定 (GPIO #10は出力, それ以外は入力)
  *(int *)0x3f200004 = 0;
  // LED点灯 (GPIO #10の出力を1にする)
  *(int *)0x3f20001c = 1 << 10;

  return 0;  // init.sに戻る
}
