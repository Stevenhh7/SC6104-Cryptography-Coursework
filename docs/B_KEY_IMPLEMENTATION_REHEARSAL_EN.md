# RSA recovery: speaker sheet

## Main explanation (about 40–50 seconds)

The slide shows two sequential stages: the left function returns an RSA private key; the caller passes that key to the right decryption function. The three arithmetic statements remain highlighted within the full recovery logic. Leave the two dialogs closed during the main explanation.

> The left function rebuilds an RSA private key from the factor found by our detector. The highlighted lines recover q, calculate lambda, and obtain d by modular inversion. Four checks reject invalid inputs and inconsistent results. PyCryptodome constructs the key. The right functions use matching SHA-256, MGF1 and label settings for OAEP decryption. Finally, a separate evaluation compares the recovered plaintext with the expected message.

If asked to explain the arithmetic, point to the example:

> For N equal to seventy-seven, p equal to seven and e equal to seventeen, q is eleven, lambda is thirty, and d is twenty-three. Seventeen times twenty-three modulo thirty equals one.

## Where to point

1. Left: lines 17, 22 and 25 for q, lambda and d.
2. Left: summarize the four checks in one sentence; line 26 constructs the key and line 29 returns it.
3. Right: lines 34–35 set the OAEP parameters; line 53 decrypts using the recovered key.
4. The example buttons highlight the matching arithmetic line. Use them for a question about the inverse, not as a second full demo.

## What the three lines mean

| Statement | Meaning | Example |
|---|---|---|
| `q = n // p` | Obtain the other factor by exact integer division. The complete function first checks that p is a proper divisor. | `77 // 7 = 11` |
| `lambda_n = lcm(p - 1, q - 1)` | Calculate the Carmichael value for a product of two distinct primes. | `lcm(6, 10) = 30` |
| `d = pow(e, -1, lambda_n)` | Calculate the modular inverse of the public exponent. | `pow(17, -1, 30) = 23` |

The inverse check is `17 * 23 = 391 = 13 * 30 + 1`. Thus `17 * 23 mod 30 = 1`.

The main slide includes the complete recovery logic, followed by OAEP configuration and decryption. Blank lines and comments are omitted, and error messages are concise. The supplementary buttons show different parts of the same workflow, rather than repeating these functions.

## Supplementary buttons (for questions)

**Recovery pipeline** shows `recover_messages()` in `rsa_lab/crypto.py`, lines 83–96. This caller passes detected factors to `recover_private_key()`, reuses a cached key for the same `(N, e)`, and passes the recovered private key to `decrypt_message()`. Errors remain explicit as `invalid_factor` or `invalid_ciphertext` before processing continues. The excerpt connects the two stages shown on the main slide.

> These calls connect key recovery to message decryption. We cache the recovered key by N and e, so duplicate public-key records can reuse the same key while retaining separate ciphertexts. Reconstruction and decryption failures are recorded separately.

**Verification evidence** shows the plaintext comparison in the separate `evaluate()` function, followed by three selectable archived results: verified recovery, wrong OAEP label and corrupted ciphertext. The recorded recovery verified six messages across five distinct moduli. Both negative controls produced `invalid_ciphertext`, as expected.

> Decryption is followed by an independent comparison with the expected message bytes. The recorded experiment verified six messages from five distinct keys. The wrong-label and corrupted-ciphertext controls were both rejected. These buttons show saved evidence; the live Python replay is on slide six.

Use one supplementary view when a question calls for it. Keep both closed during the main explanation. The independent evaluator receives the expected messages after the recovery process; the attack functions do not receive them.

## Short answers to likely questions

**Where does p come from?**

The shared-factor detector calculates it from related public moduli. The recovery function receives N, e and that detected factor. It receives no original private key.

**Why use `//` rather than `/`?**

RSA needs exact integer arithmetic. The earlier check confirms that p divides N. `//` returns an integer; `/` would use floating-point division for these integer inputs.

**Why use lambda rather than phi?**

For two distinct primes, lambda is `lcm(p - 1, q - 1)` and phi is `(p - 1) * (q - 1)`. Lambda gives a sufficient modulus for the RSA exponent relation. An inverse modulo phi can also produce a valid private exponent. This implementation uses lambda consistently.

**What does the negative one in `pow` mean?**

With the third argument supplied, `pow(e, -1, lambda_n)` computes the modular inverse. It does not calculate a floating-point reciprocal. The result satisfies `(e * d) % lambda_n == 1`.

**When does that inverse exist?**

Only when `gcd(e, lambda_n) == 1`. For this example, e = 17 works. If e = 3, `gcd(3, 30) = 3`, so the function rejects the input before calculating d.

**What do the four recovery checks reject?**

The left function checks that the factor is a nontrivial integer divisor, that p and q are distinct primes, that e has a modular inverse, and that the reconstructed key satisfies the factor-product and inverse relations. `RSA.construct(..., consistency_check=True)` also performs library consistency checks. The main slide shows all four checks.

**Which operations does the project delegate to libraries?**

Python provides `gcd`, `lcm` and modular inversion through `pow`. PyCryptodome provides primality checking, RSA key construction and OAEP encryption/decryption. The recovery function combines these operations with input validation.

**Does successful key construction prove that the plaintext is correct?**

No. The recovered key must first decrypt the OAEP ciphertext. A separate evaluation then compares the recovered bytes with the expected message. Construction, decryption and plaintext comparison are different checks.

**How does the caller handle repeated records and failures?**

The **Recovery pipeline** dialog shows a cache keyed by `(N, e)`. It reconstructs a private key only when that public key is absent from the cache, but decrypts each ciphertext separately. Failed reconstruction produces `invalid_factor`; failed decryption produces `invalid_ciphertext`. The caller preserves that status and continues to the next record.

**Does the verification button execute Python?**

No. It displays saved results from `artifacts/demo/verification.json` and `artifacts/controls/validation.json`. The live replay on slide six starts fresh Python recovery and compares its outputs with archived verified outputs. The independent evaluation excerpt here shows how the earlier experiment compared recovered messages with ground truth.

**Why compare Base64 strings rather than the displayed text?**

The pipeline encodes recovered bytes into canonical Base64. Comparing those strings with the expected message encoding checks the full byte sequence, including messages that cannot be displayed as UTF-8 text.

**Did this break OAEP or arbitrary RSA-2048?**

No. Related keys expose a shared factor, allowing private-key recovery. The code then performs normal OAEP decryption using that recovered key. The small N = 77 example explains the arithmetic; the actual OAEP experiment uses 2048-bit moduli.

**Why five keys but six messages?**

One affected modulus appears in two public-key records with separate ciphertexts. The recorded experiment has five distinct recovered keys and six verified messages.

## Quick practice without the sheet

1. Given N = 77, p = 7 and e = 17, calculate q, lambda and d. Expected: 11, 30, 23.
2. Explain why p = 2 must be rejected for N = 77. Expected: 2 does not divide 77.
3. Explain why e = 3 fails when lambda = 30. Expected: no modular inverse because the gcd is 3.
4. Point to each of the four checks in the complete function and state what it rejects.
5. Explain why OAEP decryption is a later step and why plaintext verification is a separate step.
