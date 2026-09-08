@ 最小限のスタートアップルーチン
.section .init
.global _start
_start:
    ldr     sp, =0x8000     @ スタックポインタ初期化
    bl      main            @ main関数呼び出し
    b       .               @ その場で無限ループ (停止)