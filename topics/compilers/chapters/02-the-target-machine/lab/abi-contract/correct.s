.text
.globl sum3
.type sum3, @function
sum3:
    pushq %rbx                 # Save the caller's value; align rsp before call.
    movq %rdi, %rbx
    addq %rsi, %rbx
    addq %rdx, %rbx
    movq %rbx, %rdi
    call echo
    popq %rbx
    ret
.size sum3, .-sum3
.section .note.GNU-stack,"",@progbits
