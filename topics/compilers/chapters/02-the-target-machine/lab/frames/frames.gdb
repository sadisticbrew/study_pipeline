set pagination off
set confirm off
set disable-randomization off
set $first = 0
break fact
commands
  silent
  if $first == 0
    set $first = (long)&n
  end
  printf "n=%ld  &n - &n_first = %ld bytes\n", n, (long)&n - $first
  continue
end
run
