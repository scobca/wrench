; Exercises a layout with two .text and two .data sections plus a stack.
; The stats report should capture all four section clusters in mem:data /
; mem:instr ranges, the IO accesses in mem:io, and the stack pushes/pops
; sitting outside any declared section.

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

    .text
write_out:
    ; Pop the saved input from the stack.
    lw       a0, 0(sp)
    addi     sp, sp, 4

    ; Load output pointer from data section 2, then write.
    lui      t1, %hi(output_ptr)
    addi     t1, t1, %lo(output_ptr)
    lw       t1, 0(t1)
    sw       a0, 0(t1)
    jr       ra

    .data
output_ptr:      .word  0x84              ; -> data section 2
