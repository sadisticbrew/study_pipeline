.text
.globl sum3
.type sum3, @function
sum3:
    subq $8, %rsp              # Align the call, but do not save rbx.
    movq %rdi, %rbx
    addq %rsi, %rbx
    addq %rdx, %rbx
    movq %rbx, %rdi
    call echo
    addq $8, %rsp
    ret
.size sum3, .-sum3
.section .note.GNU-stack,"",@progbits
