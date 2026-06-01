; Two .text + two .data sections plus a stack. `.org` introduces an
; explicit gap before the second .text section, and two trailing
; instructions in `write_out` are deliberately unreachable so the
; second text section has partial coverage.

    .text
_start:
    ; Load input pointer from data section 1, then read the input.
    lui      t0, %hi(input_ptr)
    addi     t0, t0, %lo(input_ptr)
    lw       t0, 0(t0)
    lw       a0, 0(t0)

    ; Set up the stack at 0x200 and push the input there.
    lui      sp, %hi(0x200)
    addi     sp, sp, %lo(0x200)
    addi     sp, sp, -4
    sw       a0, 0(sp)

    jal      ra, write_out
    halt

    .data
input_ptr:       .word  0x80              ; -> data section 1

    ; Force a gap before the second .text section so the layout has
    ; addresses that belong to no declared region.
    .text
    .org     64
write_out:
    lw       a0, 0(sp)
    addi     sp, sp, 4

    lui      t1, %hi(output_ptr)
    addi     t1, t1, %lo(output_ptr)
    lw       t1, 0(t1)
    sw       a0, 0(t1)
    jr       ra

unreachable:                              ; dead code — never fetched
    addi     zero, zero, 0
    halt

    .data
output_ptr:      .word  0x84              ; -> data section 2
