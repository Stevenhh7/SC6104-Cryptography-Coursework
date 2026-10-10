# A 核心代码页：理解与答辩准备

页面：`a-key-implementation.html`。这一页沿用 `b-key-implementation.html` 的双栏代码格式，独立审阅版本保留在本目录；正式十页展示中的第 9 页使用它的嵌入副本，第 10 页是 B 的私钥重建页。

页面英文用于投影，本文件中文用于理解；讲述稿和操作说明放在这里。代码来自项目实际实现，页面里的行号对应源码，没有改写为伪代码。

## 你这一页需要讲清楚什么

**我实现了平方模数余数树，让批量检测复用计算；再将叶子余数转换为 GCD，区分找到因子与仍需回退的情况。**

选中的核心函数是 `rsa_audit/trees.py` 的 `squared_remainders()`，完整函数在第 34–53 行。页面左栏为第 44–53 行函数体，右栏为 `rsa_audit/scanner.py` 第 138–148 行消费这些余数的代码。

这段代码属于你负责的 A 检测引擎。它输出因子及检测状态，后续私钥构造和 OAEP 解密由 B 的模块完成。不要把调用 GCD 或大整数库说成自己重新实现了那些底层数学原语；你实现的是树结构、传播过程、检测控制和边界处理。

## 先记住五个变量

| 名称 | 含义 |
|---|---|
| `numbers` | 已去重的不同公钥模数；值可能是 Python int 或 GMP 的 mpz |
| `tree` | 乘积树，按叶子到根的顺序保存各层 |
| `P` | 所有不同模数的乘积，保存在 `tree[-1][0]` |
| `remainders` | 当前层的余数；最终成为每个叶子的 `P mod N_i²` |
| `quotient`、`g` | `r_i / N_i`，以及 `gcd(N_i, quotient)` |

输入是公开的模数，没有私钥或生成时的秘密因子。去重在这段代码之前完成，重复记录的 ID、指数和映射仍保留在扫描器中。

## 左栏逐行解释

| 行号 | 原代码 | 你应该怎样理解 |
|---|---|---|
| 44–45 | `if not tree: return []` | 空输入没有叶子余数，直接返回空列表。 |
| 46 | `remainders = [tree[-1][0]]` | 初始化根余数为 P。根的模数是 P²，而 `P mod P² = P`。 |
| 47 | `for children in reversed(tree[:-1]):` | 排除已经处理的根；树原本按叶子到根存储，反转后就从根的下一层往叶子走。 |
| 48 | `next_remainders = []` | 为下一层准备一个新列表；不用保存全部层的余数。乘积树本身仍保留。 |
| 49 | `for index, value in enumerate(children):` | 遍历下一层节点，`value` 是该节点所代表的子树乘积。到了叶子时，就是一个公钥模数 N。 |
| 50 | `check("remainder_tree")` | 调用扫描器的检查回调，检测协作式时限。它不计算余数，也不证明素性；默认回调什么都不做。 |
| 51 | `next_remainders.append(remainders[index // 2] % (value * value))` | 取当前节点的父余数，对当前节点乘积的平方取模。`index // 2` 把两个相邻孩子映射到同一父节点。 |
| 52 | `remainders = next_remainders` | 下一层成为当前层，继续向下。 |
| 53 | `return remainders` | 返回叶子层余数，与输入模数的顺序一致。 |

最值得指着讲的是 **第 51 行**：`父节点余数 % 当前节点乘积的平方`。它同时体现父子映射和平方模数这两个关键点。

## 为什么父余数还能继续向下取模

每个节点满足这个不变量：

```text
节点乘积为 V 时，该节点余数 R = P mod V²。
```

假设父节点乘积为 U，孩子乘积为 V。V 整除 U，因此 V² 整除 U²。如果父余数为 `R_parent = P mod U²`，那么 P 与父余数之差是 U² 的整数倍，也必然是 V² 的整数倍，所以：

```text
R_parent mod V² = P mod V²
```

这正是第 51 行的数学依据。代码没有在每个叶子重新对完整的 P 做一次独立巨大除法，而是沿树复用父层结果。实际是否更快仍由同输入、同后端的性能实验衡量。

### `index // 2` 为什么正确

乘积树按相邻节点配对：

```text
孩子下标：0  1  2  3  4
父亲下标：0  0  1  1  2
```

最后一个孩子没有搭档时，乘积树把它原样带到上一层。此时父乘积和子乘积相同，整除关系仍成立，因此同样可以向下取模。

## 为什么要模 N²，不能只模 N

对某个公钥模数 N_i，把其他模数的乘积记为 Q_i。注意：**Q_i 是其他所有模数的乘积，不是 RSA 的另一个素因子 q。**

```text
P = N_i × Q_i
Q_i = k × N_i + t，其中 0 ≤ t < N_i
P = k × N_i² + N_i × t
r_i = P mod N_i² = N_i × t
r_i / N_i = t = Q_i mod N_i
```

所以：

```text
gcd(N_i, r_i / N_i) = gcd(N_i, Q_i)
```

这让我们得到“当前 N 与其他模数乘积是否共享因子”的信息。如果只计算 `P mod N_i`，结果总是 0，因为 N_i 本来就是 P 的一个因子；这种结果没有保留下除以 N_i 后所需的信息。

## 右栏逐行解释

| 行号 | 代码要点 | 含义 |
|---|---|---|
| 138 | `enumerate(zip(numbers, remainders))` | 按相同顺序配对每个不同模数及其叶子余数。 |
| 139 | `check("gcd")` | 同样检查协作式时限。 |
| 140 | `quotient, residual = divmod(remainder, n)` | 同时求商和余数；数学上 r 必须被 N 整除。 |
| 141–142 | `if residual != 0: raise ArithmeticError(...)` | 验证数学不变量。若树实现、输入顺序或传播出错，不能继续输出看似正常的结果。 |
| 143 | `g = int(arithmetic.gcd(n, quotient))` | 用选择的算术后端求 GCD，再转为普通 int，统一后续结果类型。 |
| 144 | `operations["batch_gcd_checks"] += 1` | 记录实际执行的叶子 GCD 次数，用于操作统计。 |
| 145–146 | `if g == unique_moduli[index]: full_overlap.append(index)` | GCD 是整个模数，因子尚未拆分，登记为全重叠候选。 |
| 147–148 | `elif g > 1: save_factor(index, g)` | 在前一个分支之后，这里的 g 已小于 N，是非平凡因子。保存前还会校验范围和整除。 |

`g == 1` 没有进入这两个分支：没有找到当前集合中的共享因子。后面构造结果时会得到 `no_shared_factor`。

`save_factor()` 会检查 `1 < divisor < N` 和 `N % divisor == 0`，并统一因子与余因子的输出顺序。这个函数验证的是非平凡整除因子；恢复模块还会检查两个不同素因子、指数可逆和 RSA 密钥一致性。

## 手算页面里的例子

输入为 `[15, 21, 143]`：

```text
乘积树：
                  45045
                 /     \
               315     143
              /   \     |
            15    21    143
```

对 N=15：

```text
P = 15 × 21 × 143 = 45045
15² = 225
r = 45045 mod 225 = 45
divmod(45, 15) = (3, 0)
gcd(15, 3) = 3
```

3 是 15 的非平凡因子，另一个因子为 5。全体结果：

| N | N² | r=P mod N² | r/N | gcd(N,r/N) | 意义 |
|---|---|---|---|---|---|
| 15 | 225 | 45 | 3 | 3 | 找到非平凡因子 |
| 21 | 441 | 63 | 3 | 3 | 找到非平凡因子 |
| 143 | 20449 | 4147 | 29 | 1 | 当前集合未发现共享因子 |

143=11×13，但本例中没有其他模数包含 11 或 13，批量检测没有借此得到它的因子。不能把最后一项说成“证明 143 安全”。

## 必须理解的全重叠例子

输入 `[15, 21, 35]`：15=3×5、21=3×7、35=5×7。每个模数的两个素因子都在别的模数中出现。

```text
P = 11025
所有叶子余数都是 0
所有 quotient 都是 0
gcd(N, 0) = N
最终 g 为 [15, 21, 35]
```

余数为 0 不违反整除不变量。它说明剩余乘积同时覆盖了 N 的两个因子，当前 GCD 尚不能区分它们，因此先进入 `full_overlap`。

扫描器随后执行针对候选项的两两回退，例如 `gcd(15, 21)=3`，再恢复 15=3×5。如果回退预算为 0 或耗尽，尚未拆分的项保留 `unresolved_full_overlap`，不能归为 clean。

**两套数字不能混用：** 教学三角例子默认只需要 3 次回退 GCD；正式 100 个不同模数的 2048-bit 实验中有 3 个候选、共 9 次回退检查，因为候选需要在更大的集合中寻找相关项。页面引用的是正式归档结果，不是浏览器现场运行的扫描结果。

## 约 75–90 秒英文讲述稿

默认只讲主页面；完整函数和第二个算例可以留给提问时使用。

> This is the core of my batch GCD detector. The caller first deduplicates the public moduli and builds a product tree. The root contains their total product, P.
>
> On the left, I propagate remainders from the root down to the leaves. At every node, the invariant is P modulo the square of that node’s product. The expression index divided by two selects the parent. Reducing the parent remainder again is valid because the child’s squared product divides the parent’s squared product.
>
> At a leaf, the result is r i equal to P modulo N i squared. Since P contains N i, r i is exactly divisible by N i. On the right, divmod checks this before computing the GCD.
>
> For N equal to fifteen, the remainder is forty-five, the quotient is three, and the GCD exposes factor three. A GCD equal to the whole modulus requires fallback; it does not complete the factorization.
>
> This code turns shared relationships between public moduli into validated factors, which are then passed to the recovery module.

如果只有 30 秒：

> My core implementation propagates P modulo squared node products down the remainder tree. At each leaf, I verify exact division by N, then compute the GCD to detect a shared factor. A nontrivial divisor is saved; a GCD equal to N is queued for fallback. This preserves the difference between a recovered factor and an unresolved full-overlap case.

## 这一页怎么操作

- 双击 `a-key-implementation.html`，打开独立一页。
- 指第 51 行讲“父余数对孩子乘积的平方取模”。
- 指第 140、143 行讲“精确整除，再求 GCD”。
- 指第 145 行讲“等于 N 仍需回退”。
- **Full function**：显示原函数和扫描器循环的完整源码。
- **Arithmetic trace**：切换普通共享素因子与全重叠三角例子，查看真实 Python 函数算出的表格。
- **Full screen**：整页全屏；补充窗口用 Close 或 Esc 关闭。

这些是你的排练说明，不出现在投影页面中。正式 `final.html` 的第 9 页已加入这页代码及其补充窗口。

## 高频问答

| 问题 | 回答要点 |
|---|---|
| 为什么不是 P mod N？ | 它一定为 0；模 N² 保留除以 N 后的其他模数乘积信息。 |
| 第 51 行为什么能复用父余数？ | 孩子乘积平方整除父乘积平方，因此连续取模等价于直接对 P 取模。 |
| 为什么用 `index // 2`？ | 乘积树将相邻两个孩子合为一个父节点，两个下标除以 2 得到同一个父下标。 |
| 奇数个节点会坏吗？ | 不会；最后一个原样携带，父子乘积相同，不变量仍成立。 |
| `check()` 是素性测试吗？ | 不是，是协作式时限检查回调；不能中断正在执行的单次大整数运算。 |
| 为什么用 divmod，不直接 //？ | 显式检查理论上的精确整除条件，防止错误余数被静默截断。 |
| r=0 说明代码错了吗？ | 不一定；三角全重叠就会如此，商为 0，GCD 等于 N，应进入回退。 |
| g=N 是否得到私钥？ | 尚未拆分 p 和 q，需要额外回退；预算不够时明确报告 unresolved。 |
| 算法是否在所有输入下都更快？ | 不能保证；大整数成本、后端和回退都影响时间，应看实测。 |
| 自己实现了什么？ | 乘积树、平方余数传播、去重、分类、回退、输出及计时；int/GMP 提供算术原语。 |
| 这段代码的输出能直接解密吗？ | 因子交给 B 重建私钥，检查密钥后才能正常 OAEP 解密。 |

## 建议你自己运行一次

在课程项目根目录打开 Python：

```powershell
.\.venv\Scripts\python.exe
```

粘贴：

```python
from math import gcd
from rsa_audit.trees import product_tree, squared_remainders

values = [15, 21, 143]
tree = product_tree(values)
remainders = squared_remainders(tree)
print(tree)
print(remainders)
print([divmod(r, n) for n, r in zip(values, remainders)])
print([gcd(n, r // n) for n, r in zip(values, remainders)])
```

预期结果：

```text
[[15, 21, 143], [315, 143], [45045]]
[45, 63, 4147]
[(3, 0), (3, 0), (29, 0)]
[3, 3, 1]
```

再把 `values` 改成 `[15, 21, 35]`，重算后会得到余数 `[0, 0, 0]` 和 GCD `[15, 21, 35]`。试着不看稿回答为什么它们仍不能直接报告因子。

页面里的算例由实际 Python 函数生成，来源校验与例子保存在 `a-code-evidence.json`。行号按整理时的源码定位；若以后修改源码，请同步这页及讲解材料。
