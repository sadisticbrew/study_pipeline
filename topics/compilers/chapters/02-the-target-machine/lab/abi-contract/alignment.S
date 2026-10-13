.text
.globl sum3
.type sum3, @function
sum3:
#ifndef MISALIGNED
    subq $8, %rsp              # Entry rsp is 8 modulo 16; call rsp must be 0.
#endif
    call vector_local
#ifndef MISALIGNED
    addq $8, %rsp
#endif
    ret
.size sum3, .-sum3
.section .note.GNU-stack,"",@progbits
