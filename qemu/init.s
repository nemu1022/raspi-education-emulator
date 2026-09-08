@ 最小限のスタートアップルーチン
.section .init
.global _start
_start:
    @ 自分のCPU番号を調べる (MPIDRレジスタの下位2bit)
    mrc     p15, 0, r0, c0, c0, 5   @ MPIDR読み出し
    and     r0, r0, #3              @ 下位2bit = CPU番号 (0〜3)
    cmp     r0, #0
    bne     halt_loop               @ CPU0以外はここで停止

    @ ここから先はCPU0だけが実行する
    ldr     sp, =0x8000             @ スタックポインタ初期化
    bl      main                    @ main関数呼び出し
    b       .                       @ その場で無限ループ (停止)

halt_loop:
    wfe                             @ 割り込み待ちで待機（低消費電力）
    b       halt_loop               @ 起こされても即座に寝直す