# A 的演讲、原理理解与答辩准备

本材料对应仓库中实际实现的 A 部分。英文段落可作为演讲草稿；中文部分用于理解、准备配图和回答问题。正式演讲前应亲自运行代码，并根据 B 的实验结果调整衔接语。

## 1. 你负责讲什么

整个团队展示为 8 分钟。你负责约 3 分 30 秒至 4 分钟，分散在三个位置：

| 团队时间 | 你负责的内容 | 目标 |
|---|---|---|
| 0:45–1:45 | 共享素因子攻击 | 解释为什么一个 GCD 能泄露私钥 |
| 1:45–3:15 | 两两算法、批量算法和边界情况 | 说明项目的算法深度与工程处理 |
| Demo 中约 15–20 秒 | 指出扫描输入和恢复结果 | 证明程序只使用公开信息 |
| 6:15–7:15 | 修复、局限、性能解释边界 | 表明你理解攻击成立条件 |

核心信息有三条：

1. RSA 模数很大，也不能抵消不同密钥共享素因子带来的问题。
2. 批量 GCD 使用乘积树和余数树，避免直接进行全部两两比较。
3. 重复模数、全重叠结果和检测局限都必须明确处理。

## 2. 先理解攻击为什么成立

一个 RSA 公钥包含 $N$ 和 $e$，其中 $N=pq$，$p$ 与 $q$ 为不同素数。知道 $p,q$ 后，可计算私钥指数：

$$
d=e^{-1}\pmod{\operatorname{lcm}(p-1,q-1)}.
$$

若两个不同模数使用了同一个素数：

$$
N_1=pq_1,\qquad N_2=pq_2,
$$

且 $q_1\ne q_2$，则：

$$
\gcd(N_1,N_2)=p.
$$

直观例子：

$$
77=7\times11,\qquad91=7\times13,\qquad\gcd(77,91)=7.
$$

两个公钥分别看上去不同，但放在一起就暴露了一个素因子。问题来自密钥生成时的共享结构，不要求较小的私钥指数或公钥指数。本项目的真实尺寸测试采用 $e=65537$。

**讲解重点：** 我们利用的是多个公钥之间的关系。不要声称项目能够快速分解任意 2048-bit RSA 模数。

## 3. 为什么需要批量算法

假设有 $m$ 个不同的 RSA 模数。最直接的办法是两两计算 GCD，需要：

$$
\frac{m(m-1)}{2}
$$

次比较。例如 1000 个模数对应 499,500 次 GCD。

这个基础算法容易实现，也可以用来验证批量算法的结果。但当集合变大时，两两比较数量增长很快。

批量算法希望对每个 $N_i$ 求：

$$
\gcd\left(N_i,\prod_{j\ne i}N_j\right).
$$

如果其他模数的乘积中包含 $N_i$ 的一个素因子，GCD 就能暴露这个因子。实现难点是高效得到每个模数所需的信息，避免反复处理完整的巨大乘积。

## 4. 乘积树与余数树：你必须能讲清楚的部分

### 4.1 乘积树

把相邻的数两两相乘，逐层向上。代码中按“叶子到根”的顺序保存各层。

以输入 `15、21、143` 为例：

```text
                 45045
                /     \
              315     143
             /   \     |
           15    21    143
```

叶子数量为奇数时，最后一个值直接传到上一层。它没有被额外乘一次。

根节点得到：

$$
P=\prod_jN_j.
$$

对应代码：`rsa_audit/trees.py` 中的 `product_tree()`。

### 4.2 为什么对模数的平方取余

我们计算：

$$
r_i=P\bmod N_i^2,\qquad
g_i=\gcd\left(N_i,\frac{r_i}{N_i}\right).
$$

设 $Q_i=\prod_{j\ne i}N_j$，则 $P=N_iQ_i$。根据取余定义，存在整数 $k$ 使：

$$
r_i=N_iQ_i-kN_i^2=N_i(Q_i-kN_i).
$$

所以 $r_i$ 一定能被 $N_i$ 整除，而且：

$$
\frac{r_i}{N_i}\equiv Q_i\pmod{N_i}.
$$

最终 GCD 与目标 $\gcd(N_i,Q_i)$ 相同。代码显式检查余数可以整除，避免树计算错误悄悄产生结果。

**为什么不能对 $N_i$ 直接取余？** 因为 $P$ 包含 $N_i$，余数必然是零。

### 4.3 余数树怎样复用计算

从根向下，把父节点的余数继续对每个子节点乘积的平方取模。

若子节点乘积为 $C$、父节点乘积为 $V$，则 $C$ 整除 $V$，所以 $C^2$ 也整除 $V^2$。因此：

$$
(P\bmod V^2)\bmod C^2=P\bmod C^2.
$$

逐层复用父节点余数，最后得到每个叶子的 $r_i$。代码只保存当前一层的余数。

上述小例子的最终结果：

| $N_i$ | $P\bmod N_i^2$ | 除以 $N_i$ | 最终 GCD |
|---|---|---|---|
| 15 | 45 | 3 | 3 |
| 21 | 63 | 3 | 3 |
| 143 | 4147 | 29 | 1 |

对应代码：`rsa_audit/trees.py` 中的 `squared_remainders()`，以及 `rsa_audit/scanner.py` 中的 batch 分支。

## 5. 项目深度：两个容易忽略的情况

### 5.1 重复模数

若两条记录都使用 $N=15$，计算 GCD 得到 15，没有获得非平凡因子。

做法是先按模数去重，保留原记录 ID 和各自的 $e$，完成检测后再映射回去。重复记录单独报告。

**需要准确表达：** 仅有相同模数这一事实，不足以通过共享因子 GCD 完成分解；这不代表重复使用密钥没有其他风险。

### 5.2 去重后仍可能得到整个模数

考虑：

$$
15=3\times5,\quad21=3\times7,\quad35=5\times7.
$$

对 15 而言，其他两个数的乘积同时包含 3 和 5，因此：

$$
\gcd(15,21\times35)=15.
$$

这不是“没有漏洞”，只是批量结果尚未把两个因子分开。

本实现的处理：

1. 把这类结果标记为 full overlap。
2. 与其他不同模数进一步做两两 GCD。
3. 得到非平凡因子后再标记 `factor_found`。
4. 若人为设置回退预算并耗尽，保留 `unresolved_full_overlap`，不标记为正常。

可以现场运行两次进行对照：

```powershell
python -m rsa_audit examples/toy_public_keys.jsonl --max-fallback-checks 0
python -m rsa_audit examples/toy_public_keys.jsonl
```

第一条有 3 个未拆分模数，退出码为 4；第二条完成拆分。这个例子适合作为答辩备用，不一定占用主要 demo 时间。

## 6. 幻灯片应该放什么

你负责 3 张主要 slide，另准备 1 张答辩备用 slide。

| 页面 | 英文标题 | 页面内容 | 讲解重点 |
|---|---|---|---|
| A1 | Shared Primes Break RSA Keys | 两个模数分解式、GCD 公式、77/91 小例子 | 从公开关系得到因子，再恢复私钥 |
| A2 | From Pairwise GCD to Batch GCD | 两两比较次数、乘积树图、批量公式 | 树结构怎样复用计算 |
| A3 | Correctness and Limitations | 去重、full overlap、当前集合限制、随机性与换钥 | 工程边界和结论边界 |
| 备用 | Why Modulo the Square? | $P=N_iQ_i$ 的三行推导；15/21/35 例子 | 回答老师的数学追问 |

不要把整段源码放在 slide 上。需要展示代码时，只截 `product_tree` 的逐层合并、余数向下传播和最后的 GCD 三个关键位置。

## 7. 英文演讲草稿

以下分段对应你出现的三个时间位置。整体约 410 个英文单词，预留公式、指图和切换时间；最终以彩排结果调整。

### A1：攻击原理，约 1 分钟

An RSA public key contains a modulus N and a public exponent e. Normally, N is the product of two secret primes, p and q.

The problem appears when two different keys reuse one prime. If N one equals p times q one, and N two equals p times q two, their greatest common divisor reveals p. We can then divide each modulus to obtain the other prime and reconstruct the private key.

For example, the GCD of 77 and 91 is 7. Our actual validation uses 2048-bit moduli, but the principle is the same. The weakness is the shared prime, so increasing the key size does not remove it.

### A2：算法与边界，约 1 分 30 秒

The baseline compares every pair of distinct moduli. With m moduli, this requires m times m minus one, divided by two, GCD computations.

Our batch implementation uses a product tree and a remainder tree. The product tree combines neighboring moduli until we obtain the total product P.

The remainder tree then computes P modulo each modulus squared. For each modulus, we divide that remainder by the modulus and calculate a GCD. This gives the same shared-factor information as comparing the modulus with the product of all the other moduli.

Using the square is essential. Reducing P directly modulo the modulus would always give zero.

We also handle two important cases. First, identical moduli are deduplicated, while their record IDs are preserved. Second, the batch GCD can equal the entire modulus when both primes appear elsewhere. We use additional pairwise checks to split these cases. If a fallback budget is exhausted, the result remains unresolved instead of being reported as clean.

### Demo 中的补充，约 15–20 秒

The scanner receives only public-key records. The factors shown here were recovered from those records, not loaded from the generator. The separate integration check confirms that these factors can reconstruct a private key and decrypt the OAEP test ciphertext.

### A3：修复与局限，约 1 分钟

There are two limits to our conclusions. A clean scan only means that no shared factor was found in the current collection. A matching vulnerable key could exist outside it.

Also, the small 2048-bit fixture validates correctness, not large-scale performance. Performance comparisons must use the same data and arithmetic backend, and include fallback work.

OAEP does not fix this weakness because the attacker has recovered the private key itself. The appropriate response is to fix the randomness used during key generation and replace affected keys. Batch scanning can support that process by detecting shared-factor relationships across the available public keys.

## 8. 答辩问题与回答要点

| 问题 | 回答要点 |
|---|---|
| Why does this work on 2048-bit RSA? | 共享因子使 GCD 能直接暴露因子，攻击不依赖一般大整数分解。 |
| Does it require a small exponent? | 不需要。本项目真实尺寸样本采用 $e=65537$。 |
| Why do you need multiple keys? | 我们检测的是模数之间的共享关系；单个模数没有可对照对象。 |
| Why not compute GCD with the total product? | 总乘积包含目标模数自己，GCD 必然是整个目标模数。 |
| Why reduce modulo the square? | 平方模数保留了除以 $N_i$ 后与“其他模数乘积”同余的信息。 |
| Why use trees? | 逐层复用乘法和求余，避免大量独立的大整数处理。 |
| Is batch GCD linear? | 不能简单这样说；取决于总输入位数、底层大整数算法和回退成本。 |
| Why is GCD equal to N not a clean result? | 两个素因子可能分别出现在其他模数里，需继续拆分。 |
| Does deduplication lose information? | 分解只需每个不同模数一次；原记录 ID 和指数仍保留并映射回来。 |
| Why keep each record's e? | 同模数记录可能有不同公钥指数；恢复私钥指数时必须用该记录自己的 e。 |
| Are the returned factors proven prime? | 扫描器验证非平凡因子和乘积；输入预期为两素数 RSA，私钥构造另做一致性检查。 |
| Can OAEP prevent the attack? | 不能，正确填充不能修复已泄露的私钥。 |
| Does no_shared_factor prove security? | 仅排除当前集合中被该检测方法发现的共享关系。 |
| How did you verify correctness? | 边界样例、独立两两 oracle、随机样例、两种后端、2048-bit 样本和 OAEP 集成测试。 |
| What is the main memory cost? | 保存乘积树的各层大整数；余数实现只保留当前层。对象开销也影响实际内存。 |
| What happens on timeout? | 协作式超时会抛出异常，不返回部分成功报告；单次大整数操作不能立即中断。 |
| What is still B's responsibility? | 大规模数据生成、正式基准实验与图表、恢复模块和完整 demo。 |

若老师追问复杂度，可说明：两两算法有 $m(m-1)/2$ 次 GCD；树算法在快速算术模型下可按总输入位数讨论接近线性的增长及对数因子，但不能把这一理论直接当作当前 Python 实现的实测表现。极端全重叠输入的回退仍可能需要二次级比较。

## 9. 演讲前的代码阅读顺序

1. `examples/toy_public_keys.jsonl`：手算哪些模数共享素数。
2. `rsa_audit/models.py`：理解公钥、单条结果和报告。
3. `rsa_audit/scanner.py` 的 pairwise 分支：从最直接算法入手。
4. `rsa_audit/trees.py`：画出一组 3 个或 5 个输入的树。
5. `rsa_audit/scanner.py` 的 batch 分支：把公式与代码逐句对应。
6. `tests/test_scanner.py`：理解为什么需要这些边界测试。
7. `tests/test_real_size.py`：理解因子怎样连接到私钥和 OAEP。

建议亲自完成三个小练习：

- 修改一个教学样本，预测哪些记录的结果会变化，再运行核对。
- 禁用回退，解释三角结构的状态和退出码为何变化。
- 在小样本中增加重复记录，解释记录数、不同模数数与恢复记录数的区别。

## 10. 应避免的说法

| 不准确的说法 | 更准确的表达 |
|---|---|
| We broke RSA-2048. | We recovered keys from 2048-bit RSA moduli that share prime factors. |
| No shared factor means the key is secure. | No shared factor was found in this dataset. |
| Batch GCD is always faster. | We compare the methods under the same conditions and report the observed results. |
| Duplicate keys immediately reveal the factors. | Duplicate moduli are reported separately and do not by themselves give a nontrivial factor. |
| OAEP protects against weak key generation. | OAEP cannot repair a private key recovered through factorization. |

背景和算法参考：[Mining Your Ps and Qs，尤其第 3.3 节](https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final228.pdf)。本材料的具体输入、状态和回退逻辑以本仓库实现为准。
