-- The harness binds each of 1, 0, NULL to both parameters.
SELECT :a AND :b AS a_and_b, :a OR :b AS a_or_b, NOT :a AS not_a;
