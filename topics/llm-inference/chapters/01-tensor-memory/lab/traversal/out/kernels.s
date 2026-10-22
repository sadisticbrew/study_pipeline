	.file	"kernels.c"
	.text
	.p2align 4
	.globl	columns_inner
	.type	columns_inner, @function
columns_inner:
.LFB0:
	.cfi_startproc
	movq	%rsi, %r10
	xorl	%r8d, %r8d
	testq	%rsi, %rsi
	je	.L3
	testq	%rdx, %rdx
	jne	.L15
.L13:
	addq	$1, %r8
	cmpq	%r8, %r10
	jne	.L13
.L3:
	xorl	%edx, %edx
	movq	%rdx, %rax
	ret
	.p2align 4,,10
	.p2align 3
.L15:
	leaq	0(,%rdx,4), %r9
	xorl	%edx, %edx
	leaq	(%rdi,%r9), %rsi
	.p2align 4
	.p2align 3
.L5:
	movq	%rsi, %rax
	subq	%r9, %rax
	.p2align 4
	.p2align 4
	.p2align 3
.L4:
	movslq	(%rax), %rcx
	addq	$4, %rax
	addq	%rcx, %rdx
	cmpq	%rax, %rsi
	jne	.L4
	addq	$1, %r8
	addq	%r9, %rsi
	cmpq	%r8, %r10
	jne	.L5
	movq	%rdx, %rax
	ret
	.cfi_endproc
.LFE0:
	.size	columns_inner, .-columns_inner
	.p2align 4
	.globl	rows_inner
	.type	rows_inner, @function
rows_inner:
.LFB1:
	.cfi_startproc
	movq	%rsi, %r8
	movq	%rdx, %r11
	testq	%rdx, %rdx
	je	.L19
	testq	%rsi, %rsi
	je	.L19
	leaq	0(,%rdx,4), %r9
	xorl	%r10d, %r10d
	xorl	%ecx, %ecx
	.p2align 4
	.p2align 3
.L21:
	movq	%rdi, %rdx
	xorl	%eax, %eax
	.p2align 5
	.p2align 4
	.p2align 3
.L20:
	movslq	(%rdx), %rsi
	addq	$1, %rax
	addq	%r9, %rdx
	addq	%rsi, %rcx
	cmpq	%rax, %r8
	jne	.L20
	addq	$1, %r10
	addq	$4, %rdi
	cmpq	%r10, %r11
	jne	.L21
	movq	%rcx, %rax
	ret
.L19:
	xorl	%ecx, %ecx
	movq	%rcx, %rax
	ret
	.cfi_endproc
.LFE1:
	.size	rows_inner, .-rows_inner
	.ident	"GCC: (GNU) 16.2.1 20260810"
	.section	.note.GNU-stack,"",@progbits
