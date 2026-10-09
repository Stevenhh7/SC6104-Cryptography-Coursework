# A/B 接口交接

## 1. 当前分工边界

A 已提供公共密钥检测引擎、命令行、正确性测试和算法阶段计时。

B 接下来实现：数据生成与真值、私钥恢复模块、实验运行器、绘图、正式 OAEP 演示、修复对照。测试中的 OAEP 恢复代码可以作为接口示例。

## 2. 公共输入

```python
from rsa_audit import PublicKey, scan_keys
from rsa_audit.io import write_public_keys

keys = [PublicKey("device-001", n, e)]
write_public_keys("public_keys.jsonl", keys)
report = scan_keys(keys, method="batch", backend="python")
```

在 Python API 中，`n、e` 必须是 Python `int`，如使用 `gmpy2.mpz` 生成数据，先转为 `int`。文件中的 `n` 使用十六进制字符串，`e` 使用整数。

基础校验：非空且唯一的字符串 ID、奇数 `n > 1`、奇数 `e >= 3`。小整数教学样例允许 `e >= n`。生成真实 RSA 密钥时由 B 保证完整 RSA 参数条件，包括不同素因子、指数互素、目标位数。

扫描器不接收 `p、q、d`。把真值放在独立文件中，仅在评估阶段读取。

## 3. 调用参数

```python
report = scan_keys(
    keys,
    method="batch",             # 或 "pairwise"
    backend="python",           # 或 "gmpy2"
    max_fallback_checks=None,    # None: 完整回退；0: 不做回退；正整数: 全局 GCD 次数预算
    timeout_seconds=None,       # 正数：协作式超时
)
```

- 默认不会因 `g_i=N_i` 就丢弃记录，而是尝试回退拆分。
- `max_fallback_checks` 只影响 batch，预算在整个扫描中共享，不是每条记录一个预算。
- 输入／配置问题抛出 `ValueError`；超时抛出 `ScanTimeout`，其 `stage` 表示发生阶段。
- 超时不返回残缺的成功报告。没有超时但预算不足时，返回带 `unresolved_full_overlap` 的完整状态报告。

## 4. 每条检测结果

`report.results` 为保持原始输入顺序的元组，每项有：

| 字段 | Python 类型 | 说明 |
|---|---|---|
| `id` | str | 原记录 ID |
| `n` | int | 原模数 |
| `e` | int | 原记录自己的公钥指数 |
| `modulus_index` | int | 去重后首次出现顺序中的索引 |
| `status` | str | 三种状态之一 |
| `factor` | int 或 None | 非平凡因子，规范为两个因子中较小的一个 |
| `cofactor` | int 或 None | `n // factor` |
| `duplicate_count` | int | 同模数的其他记录数量，不含自己 |

JSON 报告中 `n、factor、cofactor` 改用 `0x` 前缀的十六进制字符串；空因子为 `null`。B 若读取 JSON，使用 `int(value, 16)` 转换。

对有效的两素数 RSA 数据，`factor` 与 `cofactor` 就是恢复私钥需要的两个素因子。扫描器只保证因子非平凡且乘积正确，私钥构造阶段还应使用密码库的一致性检查。

### 私钥恢复连接点

```python
import math
from Crypto.PublicKey import RSA

for row in report.results:
    if row.status != "factor_found":
        continue
    p, q = row.factor, row.cofactor
    lam = math.lcm(p - 1, q - 1)
    d = pow(row.e, -1, lam)
    key = RSA.construct((row.n, row.e, d, p, q), consistency_check=True)
    # 在 B 的模块中导出密钥、解密或验证。
```

相同模数可能对应不同 `e`，不能直接复用其他记录的 `d`。

## 5. 去重结果与统计口径

`report.duplicate_groups` 只包含有重复的组，每组提供 `modulus_index、n、record_ids`。避免为每条记录重复输出整个 ID 列表，防止大量重复密钥导致输出膨胀。

| summary 字段 | 含义 |
|---|---|
| `record_count` | 输入记录数 |
| `unique_modulus_count` | 按 `n` 去重后的模数数 |
| `duplicate_record_count` | 记录数减去不同模数数 |
| `duplicate_group_count` | 具有重复记录的模数组数 |
| `factored_unique_moduli` | 已成功分解的不同模数数 |
| `factored_records` | 映射回原始记录后，具有因子的记录数 |
| `no_shared_factor_unique_moduli` | 当前集合中没有检测出共享因子的不同模数数 |
| `unresolved_unique_moduli` | 尚未完成拆分的不同模数数 |
| `batch_full_overlap_count` | batch 阶段出现 `g_i=N_i` 的数量；pairwise 中为 0 |
| `fallback_limit_reached` | 是否因预算用尽而停止回退 |

三种模数状态计数之和应等于 `unique_modulus_count`。`factored_*` 只表示分解，不表示已经生成私钥或成功解密。

## 6. 时间与操作次数

`report.timings` 单位为秒：

- `preprocess_seconds`：输入记录验证、去重和映射。
- `conversion_seconds`：转换至所选算术后端。
- `pairwise_seconds`：两两算法主循环。
- `product_tree_seconds`：乘积树。
- `remainder_tree_seconds`：平方模数余数树。
- `gcd_seconds`：batch 叶节点整除与 GCD。
- `fallback_seconds`：batch 的额外拆分检查。
- `result_seconds`：逐记录结果、重复分组和统计构造。
- `total_seconds`：完整扫描耗时。

不适用的阶段为 0。`total_seconds` 包含少量阶段切换开销，不要求与阶段和逐位相等。后端导入／初始化、文件解析、JSON 序列化和写盘不计入扫描时间。

`report.operations` 包含：`pairwise_gcd_checks、batch_gcd_checks、fallback_gcd_checks`。这些是 GCD 调用次数，不是 CPU 指令数或总复杂度。

### B 的基准测试建议

1. 预先生成并缓存数据，记录数据文件哈希和真实标签。
2. 两种算法使用相同数据和同一后端，分别测试 Python 和 gmpy2 时分组报告。
3. 使用多个输入规模、重复 3–5 次，保存每次原始测量，再计算中位数。
4. 使用 `total_seconds` 作主比较，阶段耗时用于解释瓶颈。
5. 同时保存未解决数量与回退数量，避免将不完整检测当作完整扫描加速。
6. 硬超时使用独立进程；超时样本标注 timeout，不填入猜测值。
7. 基础性能实验保持弱模数比例和共享结构一致，特殊三角结构单独分析。

## 7. 固定交接样本

```powershell
python -m rsa_audit tests/fixtures/rsa2048_public.jsonl --output results/handoff.json
```

样本有 16 条记录、14 个不同的 2048-bit 模数，预期恢复 6 个不同模数／7 条记录。包含 2 组重复记录，以及 4 个需要 batch 回退的模数。

`tests/fixtures/rsa2048_oaep_challenge.json` 是给接口验证使用的公开密文：OAEP-SHA-256，MGF1-SHA-256，空 label。扫描目标公钥并恢复因子后可以解密，使用 `plaintext_sha256` 核对结果，不需要生成时的私钥。

此样本用于正确性和联调；正式性能实验需使用 B 生成的更大数据集。
