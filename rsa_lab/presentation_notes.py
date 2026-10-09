"""English speaking notes linked to measured results, not preset performance claims."""

from pathlib import Path
from .models import read_json
from .plots import read_csv


def write_notes(root):
    root = Path(root)
    demo = read_json(root / "results/demo/verification.json")
    rows = read_csv(root / "results/benchmark/summary.csv")
    batch = {int(row["unique_moduli"]): row for row in rows if row["algorithm"] == "batch"}
    pair = {int(row["unique_moduli"]): row for row in rows if row["algorithm"] == "pairwise"}
    largest = max(batch)
    seconds = float(batch[largest]["median_seconds"])
    comparable = max(size for size in batch if pair[size]["median_seconds"])
    ratio = float(pair[comparable]["median_seconds"]) / float(batch[comparable]["median_seconds"])
    notes = f"""# English presentation script and rehearsal guide

Eight minutes includes the live demo. Reserve the following two minutes for questions. Main slides are all in English. Supplemental evidence opens in dialogs and is mainly for Q&A.

| Time | Slide | Speaker |
|---|---|---|
| 0:00–0:45 | 1. Research goal | B |
| 0:45–1:45 | 2. Shared-prime attack | A |
| 1:45–2:45 | 3. Batch GCD | A |
| 2:45–3:15 | 4. Duplicates and full overlap | A |
| 3:15–4:30 | 5. Measured performance | B |
| 4:30–6:15 | 6. Public-input attack demo | B operates, A explains OAEP |
| 6:15–7:15 | 7. Key replacement | A |
| 7:15–8:00 | 8. Contributions and conclusion | B |

## 1. Research goal — B, 45 seconds

“Our project studies RSA keys that reuse a prime factor. Even when the modulus is 2048 bits long, a relationship between public keys can reveal the private keys. We implemented batch detection, reconstructed the affected keys, and verified real RSA-OAEP decryption. We also compared batch GCD with the pairwise baseline and checked the results using separate ground truth. All experiments use locally generated keys. Our question is how prime reuse changes RSA security, and how efficiently we can detect it.”

## 2. Shared-prime attack — A, 60 seconds

Advance the animation manually from the public moduli to the factors and private exponents.

“Suppose two public moduli are p times q-one and p times q-two. They reuse p, while the other factors differ. Their greatest common divisor reveals p. We then recover q by integer division. With both primes known, we calculate lambda of n as the least common multiple of p minus one and q minus one. The private exponent d is the modular inverse of e modulo lambda. Our recovery code checks the factorization, prime conditions and key consistency. The animation uses small integers to explain the mechanism. The actual attack and OAEP decryption use 2048-bit RSA.”

## 3. Batch GCD — A, 60 seconds

Advance through the product tree, squared remainder tree, exact division and final GCDs.

“For m distinct moduli, the baseline computes m times m minus one divided by two pairwise GCDs. Batch GCD reuses intermediate arithmetic. A product tree calculates the total product P. A remainder tree computes P modulo each modulus squared. Dividing this remainder by the modulus gives the value needed for the final GCD. If we used the modulus itself, every remainder would be zero. Squaring preserves the information needed after division. We carry odd leaves once, and verify that division is exact. Batch performance still depends on the size of the integers and the fallback work, so we do not describe it as simply linear.”

## 4. Edge cases — A, 30 seconds

“Identical moduli are duplicates, and their GCD does not reveal a proper factor. We deduplicate the arithmetic input while keeping every original record. A different issue occurs when both primes of one modulus appear elsewhere. The batch GCD then equals the whole modulus. Our triangle example triggers this case. Pairwise fallback splits these candidates. If a budget prevents that split, the result remains explicitly unresolved.”

## 5. Performance — B, 75 seconds

“We tested 100, 300, 1,000 and {largest:,} distinct 2048-bit moduli. Both algorithms use the same saved inputs and the same GMP backend. Each condition runs three times in a fresh process. The chart shows median scan time and the observed minimum and maximum. Scanning includes preprocessing, the main algorithm, fallback and result construction. Key generation, file input and decryption are outside this timer. At {comparable:,} moduli, batch GCD is about {ratio:.1f} times faster on this machine. At {largest:,}, its median is {seconds:.3f} seconds. All three pairwise workers exceeded the 45-second process limit, so we show timeouts and do not calculate a speedup at that size. Every completed scan also passed independent factor and OAEP verification.”

Optional Q&A: open **Stage breakdown**. Explain the measured largest component without claiming that the separately calculated stage medians sum to the median total.

## 6. Live attack — B operates, 105 seconds

Run `run_demo.cmd` before class once to confirm the environment. During the talk, run it again from the repository root. The browser buttons display saved evidence and do not launch Python.

“This collection contains 102 public-key records and 100 distinct moduli. Two records are duplicates. The attack receives public keys and OAEP ciphertexts. It does not receive the factors or the original private keys. Batch detection finds {demo['correctly_factored_moduli']} factorable moduli: one shared-prime pair and a triangle where both factors occur elsewhere. The triangle needs fallback. We reconstruct the private keys and decrypt the ciphertexts. The result is {demo['verified_decryption_records']} messages from {demo['verified_decryption_moduli']} distinct keys. One weak key has a duplicate record, which explains the extra message. After recovery, a separate evaluation process reads ground truth. All recovered plaintexts match, with zero false positives and zero false negatives. We also ran negative controls: independent primes, duplicates alone, and the same weak target without its related public keys. These collections yielded no recoverable keys.”

A adds: “We use OAEP with SHA-256 and MGF1-SHA-256. Once we recover the private key, ordinary OAEP decryption works. This does not break OAEP itself.”

If the terminal cannot run, say **“We will show the saved experimental results”** and use the page buttons. Open **Key reconstruction** if asked how B's code derives d.

## 7. Replacement and limits — A, 60 seconds

“We replaced the five affected keys using fresh cryptographic randomness, while retaining the original record mapping. Six new messages passed legitimate OAEP round trips. Rescanning the repaired collection found no shared factors, and the public-input attack recovered no new messages. This conclusion applies to the current collection and this weakness. It does not prove that every key is secure against every attack. Coverage also matters: when we isolate a vulnerable target without its related public keys, this detector cannot find a shared factor. Replacing keys cannot restore the confidentiality of messages that were already exposed under the old keys.”

## 8. Conclusion — B, 45 seconds

“A implemented the detection engine, tree algorithms and edge cases. B implemented the datasets, private-key reconstruction, OAEP validation and experimental pipeline. We integrated them through one detection interface and preserved reproducible results. Our main conclusion is that key length cannot compensate for shared primes. RSA also needs reliable, independent prime generation. The weak-prime pool extension shows how a smaller pool increases the observed recoverable fraction in our controlled model. The source, public samples, measured CSV records and replay instructions are included.”

## Two-minute Q&A preparation

| Question | Concise answer |
|---|---|
| Why is 2048-bit RSA factorable here? | GCD reveals an intentionally shared prime. We avoid general-purpose factorization. |
| Why modulo n squared? | It preserves the information needed after exact division by n. Modulo n would always give zero. |
| Why are duplicates insufficient? | gcd(n,n) gives n itself, not a proper factor. |
| Why does batch GCD sometimes return n? | Both prime factors can occur in other moduli. Fallback must split the result. |
| How does B reconstruct d? | q=n/p, lambda=lcm(p−1,q−1), and d=e inverse modulo lambda. |
| Why can either returned factor be accepted? | Swapping p and q preserves the factorization and valid private-key behavior. |
| Did OAEP fail? | No. The recovered private key permits legitimate OAEP decryption. Wrong labels and corrupted ciphertexts are rejected. |
| Where is ground truth used? | Only in evaluation after scanning and recovery. Attack inputs contain public records and ciphertexts. |
| Does zero detection prove security? | No. It checks shared-factor relationships within the supplied collection. |
| What does a timeout mean? | The whole worker exceeded 45 seconds, including startup and I/O. Its completed scan time is unknown. |
| What does the weak pool experiment model? | Reuse of one prime from a small pool. It is not a full reproduction of a device RNG failure. |

## B's rehearsal priorities

Explain the modular inverse and the OAEP parameters without reading the code. State why six messages correspond to five distinct keys. Distinguish a completed scan timer from a worker timeout. Prepare the terminal and saved-evidence fallback before presenting. Use **Validation controls**, **Stage breakdown** and **Weak-prime pool experiment** only when the timing permits or a question calls for them.
"""
    target = root / "docs/PRESENTATION.md"
    target.write_text(notes, encoding="utf-8", newline="\n")
    return target
