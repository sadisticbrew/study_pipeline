.text
.globl probe
.type probe, @function
probe:
    pushq %rbx
    pushq %r12
    subq $8, %rsp
    movq %rdi, %r12            # Keep the output pointer across the call.
    movq $1000, %rbx           # A live caller value in a callee-saved register.
    movq $10, %rdi
    movq $20, %rsi
    movq $30, %rdx
    call sum3
    movq %rbx, (%r12)          # Observe the live value after the call.
    addq $8, %rsp
    popq %r12
    popq %rbx
    ret
.size probe, .-probe
.section .note.GNU-stack,"",@progbits
