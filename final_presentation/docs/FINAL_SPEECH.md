# Final presentation：八分钟讲稿与现场操作

正式页面：`presentation/final.html`，也可从本目录根部的 `final.html` 进入。本文件供两位主讲人排练，时间、分工和口播不显示在网页上。

## 先确认三种展示内容

1. **第 2–4 页：教学动画。** 浏览器以 BigInt 实时计算小整数，用来解释数学。它们不代表现场运行 Python 的 2048-bit 扫描。
2. **正文中的实验结果：已保存、核验过的正式数据。** 100 个不同的真实 2048-bit 模数、102 条公钥记录、5 个恢复的不同密钥、6 条已核对的 OAEP 明文。性能图使用每个条件三次运行的统计结果。
3. **第 6 页 Run Python pipeline：现场执行。** 点击后，服务调用仓库原有的 `rsa_lab scan`、`rsa_lab recover`；后者调用 A 的 `rsa_audit` 引擎及 B 的恢复实现。使用归档的公开样本重新计算，完成后才与归档的核验结果比较，再重新扫描已保存的换钥集合。不是播放旧日志，也不会重新做整套独立真值评估、生成新密钥或跑所有性能实验。

不要把现场的单次扫描耗时与历史三次中位数混用。现场结果和记录结果有独立标识，正文数据不会被现场运行覆盖。

## 启动与排练

在 `final_presentation` 目录双击 `run_presentation.cmd`，保持服务窗口打开，进入：

`http://127.0.0.1:8765/presentation/final.html`

已有本机 `.venv` 时启动器自动使用它；换电脑先安装 `requirements.txt`。手动启动：

```powershell
..\.venv\Scripts\python.exe -X utf8 scripts/presentation_server.py
```

如果 8765 已被旧的静态预览服务使用，可以关闭该服务，或改用：

```powershell
.\run_presentation.cmd --port 8766
```

随后打开 `http://127.0.0.1:8766/presentation/final.html`。普通 `python -m http.server` 只提供静态页面，不能执行现场流水线。

直接双击 HTML 仍可离线讲解八页、动画和归档数据；实际 Python 执行需要上述服务。现场计算失败时页面显示错误，不会改用旧日志伪装成功。

排练前执行一次第 6 页的现场流水线，确认五个步骤通过，点击 **Save run log** 留存记录。运行使用临时目录，不覆盖原实验、不保存新私钥文件。窗口关闭后 Python 服务不会自动停止；服务窗口中按 Ctrl+C 停止。

## 时间与分工

| 页 | 时间 | 主讲 | 重点 |
|---|---|---|---|
| 1 | 0:00–0:35 | A | 问题、公开输入与项目闭环 |
| 2 | 0:35–1:35 | A | 共享素因子如何暴露私钥 |
| 3 | 1:35–3:00 | A | 乘积树、平方模数余数树、最终 GCD |
| 4 | 3:00–4:05 | A | 去重、全重叠、回退和 unresolved |
| 5 | 4:05–5:00 | B | 实测比较及超时口径 |
| 6 | 5:00–6:50 | B | 现场 Python 执行与 OAEP 证据 |
| 7 | 6:50–7:25 | B | 换钥结果与检测范围 |
| 8 | 7:25–8:00 | B | 两人的贡献、弱素数池结果、结论 |

两人都应理解整个流程。A 负责回答树算法和边界状态，B 负责回答数据、恢复、计时和验证；可以相互补充。

## 第 1 页 · Research goal

操作：从第一页开始，不打开补充窗口。

> Our project studies RSA keys that accidentally reuse prime factors. The inputs to the attack are public keys and ciphertexts. We build a batch detector, recover the affected private keys, verify OAEP plaintexts, and rescan the collection after key replacement.
>
> In our controlled experiment, all moduli are actually 2048 bits. From one hundred distinct moduli, we recover five private keys and verify six messages. The weakness is the relationship between keys, rather than a general method for factoring arbitrary RSA moduli.

## 第 2 页 · Shared-prime attack

操作：逐步点击 **Next step**。小整数为 `77 = 7×11`、`91 = 7×13`；动画有六步。解释完除法后推进，不必逐字念右栏。

> Suppose two RSA moduli share the same prime: N one equals p times q one, and N two equals p times q two. Their public values are enough to find p with a greatest common divisor.
>
> Here, Euclid’s algorithm gives seven as the last nonzero remainder. Dividing the two moduli by seven gives eleven and thirteen. Both factorizations are now known.
>
> We can then compute lambda of N, and obtain the private exponent as the inverse of e modulo lambda. For this small example, e is seventeen. Our real experiment uses 65537 and 2048-bit moduli. OAEP recovery is verified separately in Python.

你必须会算：`91 mod 77 = 14`，`77 mod 14 = 7`；`λ(77)=30`，`17×23 mod 30=1`。图中的小整数不能装进实际 RSA-OAEP 消息。

## 第 3 页 · Batch GCD

操作：按八步展示叶子 → 中间乘积 → 根 → 根余数 → 中间余数 → 叶子余数 → 整除 → GCD。遇到公式停一下。

> Pairwise GCD is a useful baseline, but one thousand distinct moduli require 499,500 pair comparisons. Batch GCD reuses large-integer work.
>
> First, we multiply the moduli upward in a product tree. An unpaired node is carried to the next level once. The root contains the product P of all moduli.
>
> Next, we propagate remainders downward, using the square of each node’s product as the modulus. At each leaf, we obtain r i equal to P modulo N i squared.
>
> Since P contains N i, the remainder is exactly divisible by N i. Dividing gives the product of the other moduli, reduced modulo N i. Taking its GCD with N i reveals a shared factor.
>
> In this example, the final results are three, three and one. The last result means no shared factor was found for 143 within this collection. We measure performance separately using actual 2048-bit inputs.

核心推导，答辩时可写：

```text
P = N_i × Q_i
r_i = P mod N_i² = N_i × (Q_i mod N_i)
r_i / N_i = Q_i mod N_i
gcd(N_i, r_i / N_i) = gcd(N_i, Q_i)
```

不能用 `P mod N_i`，因为那总是零。根节点余数为 `P mod P² = P`。这里的树复用计算不意味着所有输入都一定快，也不意味着回退没有成本。

## 第 4 页 · Correctness and edge cases

操作：展示四条记录去重成三个模数；进入全重叠和回退；在第 4 步关闭再打开 **Enable pairwise fallback**，最后映射结果。

> Two cases require special handling. First, duplicate records do not by themselves reveal a proper factor. We deduplicate the arithmetic input, but preserve record IDs and each record’s exponent for reporting and recovery.
>
> Second, consider fifteen, twenty-one and thirty-five. Both prime factors of fifteen occur elsewhere, so its batch GCD is fifteen itself. This is full overlap, not a completed factorization.
>
> Our fallback performs additional pairwise checks on these candidates. With fallback disabled, the result remains explicitly unresolved; it must never be reported as clean. With fallback enabled, we split the factors and map them back to every original record.
>
> This completes the detection engine. My teammate will show the measured performance and the end-to-end recovery.

注意右侧验证区是**正式归档实验**，不随小整数开关改成“未通过”。开关改变的是当前教学示例。正式实验有 3 个全重叠候选、9 次回退 GCD；A 的旧测试 fixture 为 14 个不同模数、6 个可分解模数，是另一套数据，正式页面已统一到 100/5/6。

## 第 5 页 · Measured performance

操作：指图和表。时间紧就不打开 **Stage breakdown**；问到瓶颈再打开。

> We compare both algorithms on the same inputs and GMP backend, using three runs per condition. The table shows median scanner time, and the plot also shows the observed range.
>
> At one thousand moduli, batch GCD takes about 0.193 seconds, compared with 6.318 seconds for pairwise GCD: approximately 32.8 times faster. At three thousand moduli, batch takes 0.780 seconds. All three pairwise workers exceed the 45-second limit, so we do not claim a measured speedup at that size.
>
> These times include validation, deduplication, arithmetic and fallback, but exclude file operations, key generation and decryption. The remainder tree is the largest measured batch component.

## 第 6 页 · Public-input attack / 现场代码运行

操作顺序：

1. 用页面四阶段按钮快速点到 **Independent verification**，显示记录结果。
2. 打开 **Run Python pipeline**，确认状态为 Ready，点击 **Run pipeline**。
3. 五个阶段由真正执行进度推动，没有人为等待或伪进度。命令先显示，进程结束后显示它的 stdout；执行很快时不必等每一段才讲。
4. 指出扫描 `factor_found: 5`、`fallback_candidates: 3`、`fallback_gcd_calls: 9`，以及恢复 `decrypted_records: 6`；最终绿色结果和 `MATCH` 行出现才说通过。
5. 运行完成后滚动查看命令和结果，必要时保存日志，再关闭窗口。

> The dataset contains 102 public-key records but only one hundred distinct moduli. Two records are duplicates. The recorded experiment recovered five distinct keys and verified six messages, because one affected key appears in two records.
>
> I will now execute the repository code on this machine. The first Python process scans only the public keys. The second uses the newly recovered factors and public ciphertexts to reconstruct private keys and decrypt OAEP. No original private key is supplied.
>
> Here are the actual command outputs. The scanner finds five factorable moduli, including three full-overlap candidates. The recovery process decrypts six messages.
>
> Only after recovery do we compare the fresh results with the archived, previously verified outputs. The six plaintexts match. Finally, a new scan of the saved replacement-key collection finds no shared factors.
>
> This live replay proves that the attack code still runs. Our separate ground-truth evaluation and ten control scans provide the broader correctness evidence. This is a compromised-key demonstration, not a break of OAEP itself.

如果失败：如实说现场执行未完成，保留错误，回到标注 **Recorded experiment** 的已核验结果。不要把归档结果说成刚刚跑出的结果。无需现场重跑 3000 个模数的性能实验。

## 第 7 页 · Replacement and limits

> Replacing five distinct keys affects six records. The repaired collection has no detected shared factors, and all six new messages pass legitimate OAEP round trips.
>
> There are three limits. Detection depends on having related public keys in the collection. A clean result covers this particular weakness, not every possible attack. And replacing a key does not restore the secrecy of previously compromised messages. The underlying randomness problem must also be addressed.

这里的换钥和六次合法 round trip 是原完整实验的结果。现场窗口只对保存的替换密钥重新扫描，没有现场重新生成密钥或重复合法 round trip。

## 第 8 页 · Results and contributions

> Our implementation combines the detection engine with recovery and evaluation: the tree algorithms, duplicate handling and explicit unresolved states on one side; real-size datasets, private-key recovery, OAEP checks and repeated experiments on the other.
>
> Ten control scans and two OAEP negative checks pass. In our weak-prime-pool experiment, smaller pools produce higher recoverable fractions: one hundred percent, 96.7 percent and 55 percent for pool sizes four, sixteen and sixty-four.
>
> Our conclusion is that key length cannot compensate for shared primes. Independent, reliable prime generation is essential.

弱池模型每套 60 个不同模数、每个池大小 3 套；每个模数一个素因子取自有限池，另一个新生成。不要泛化成真实设备的失效率或整个随机数发生器的完整模拟。**Shared-factor graph** 和 **Validation evidence** 留给问答使用。

## 两分钟问答：两人都要会的答案

| 可能的问题 | 答案要点 |
|---|---|
| 为什么 2048-bit RSA 仍被分解？ | 共享素因子提供额外结构，只需求 GCD；没有分解任意安全生成的 RSA-2048。 |
| 为什么要平方模数？ | 保留可以被 N 整除、除完仍含其他模数乘积信息的余数；模 N 会全为 0。 |
| 为什么先去重？ | 重复 N 会把 N 整体带入“其他模数乘积”，污染共享因子的判断；ID 和 e 仍保留。 |
| g=1、1<g<N、g=N 分别是什么？ | 当前集合未发现共享因子；发现非平凡因子；全重叠且仍需拆分。 |
| g=N 就是安全的吗？ | 不是。可能两个因子分别在别处出现，应回退或保留 unresolved。 |
| 回退一定很快吗？ | 不一定，极端情况下仍可能有二次级检查成本；正式计时包含回退。 |
| 为什么 5 把密钥、6 条明文？ | 一个脆弱模数出现两条不同记录，各有自己的密文。 |
| 密钥怎么恢复？ | q=N/p；校验不同素因子；λ=lcm(p−1,q−1)；d=e⁻¹ mod λ；再做 RSA 一致性和 OAEP 校验。 |
| 是否依赖 ground truth 来攻击？ | 不依赖。scan/recover 只接收公开输入及刚算出的因子；完整实验的评估在攻击后读真值。现场重放则在攻击后比较归档核验结果。 |
| 为什么不用 φ(N)？ | 用 φ 也能构造有效指数；实现采用 λ(N)，并检查模逆条件。 |
| OAEP 被破解了吗？ | 没有。私钥恢复后使用正常 OAEP 解密。错误 label 和损坏密文应被拒绝。 |
| 没找到共享因子是否说明安全？ | 只对当前输入集合和这种弱点作结论；孤立目标对照说明覆盖限制。 |
| 3000 个模数快了多少倍？ | pairwise 三次均在 45 秒终止，没有完整扫描时间，不能给出实测速比。 |
| 哪些是自己实现的？ | A 实现树、去重、检测、回退、状态和计时；B 实现数据及实验流程、恢复连接、独立核验。GMP 提供大整数原语，PyCryptodome 提供 RSA/OAEP 基础操作。 |

## 实现定位

- A：`rsa_audit/scanner.py`、`rsa_audit/trees.py`、`rsa_audit/arithmetic.py`。
- B：`rsa_lab/detection.py` 适配、`rsa_lab/crypto.py` 恢复、`rsa_lab/evaluation.py` 独立核验、`rsa_lab/cli.py` 完整实验入口。
- 现场网页：`scripts/presentation_server.py` 只编排固定命令；`presentation/assets/live.js` 展示实际输出。没有另写一套检测算法。
- 正式图表与数据：`artifacts/`、`presentation/assets/final-data.js`。

老师要求理解并能解释自己完成的代码。排练时请两人各自读完所负责模块，并能不依赖稿子推导上面的关键公式。
