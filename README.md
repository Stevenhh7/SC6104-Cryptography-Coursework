# SC6104 — RSA 共享素因子检测

**项目题目：弱随机性下 RSA 共享素因子的批量检测与私钥恢复。**

本仓库当前完成 A 的部分：两两 GCD、基于乘积树／余数树的批量 GCD、去重、特殊情况回退、统一检测接口、阶段计时、正确性测试和演讲材料。

固定样本包含真实的 2048-bit RSA 模数。扫描器只接收公开的 `id、n、e`，不读取生成时的因子或私钥。B 可接入数据生成、私钥恢复、正式实验和完整演示。

## 从这里开始

1. 阅读 [A 的演讲与理解材料](docs/A_PRESENTATION.md)，建立整体理解。
2. 运行下面的小样本与 2048-bit 样本。
3. 按演讲材料的阅读顺序看代码。
4. 把 [A/B 接口说明](docs/AB_INTERFACE.md) 发给队友。
5. 阅读 [实现与验证记录](docs/VALIDATION.md)，了解已经验证的范围。

课堂讲解可直接打开 [三页动画 HTML](presentation/index.html)：共享素因子攻击、乘积树／余数树、去重与全重叠回退。支持离线播放、键盘逐步控制、全屏和中文讲解提示；操作说明见 [presentation/README.md](presentation/README.md)。

## 快速运行

需要 Python 3.10 或以上。所有命令都在仓库根目录执行。默认后端只使用 Python 标准库，无需安装依赖。

```powershell
python -m rsa_audit examples/toy_public_keys.jsonl
python -m rsa_audit tests/fixtures/rsa2048_public.jsonl --output results/batch.json
python -m rsa_audit tests/fixtures/rsa2048_public.jsonl --method pairwise --output results/pairwise.json
python -m unittest discover -v
```

本机已创建 `.venv`，可直接使用：

```powershell
.\.venv\Scripts\python.exe -m rsa_audit tests/fixtures/rsa2048_public.jsonl --backend gmpy2 --output results/batch.json
.\.venv\Scripts\python.exe -m unittest discover -v
```

其他机器需要可选加速和 OAEP 集成测试时：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-validation.txt
```

`gmpy2` 用于大整数运算；`PyCryptodome` 只用于可选的 OAEP 集成测试。核心检测算法的树结构和控制流程在本仓库实现。

## 输入格式

每行一条 JSON，严格包含以下三个字段：

```json
{"id":"device-001","n":"0xf","e":65537}
```

- `id`：非空字符串，整个输入文件内唯一。
- `n`：十六进制字符串，推荐始终使用 `0x` 前缀。
- `e`：JSON 整数；保留每条记录各自的指数。
- 示例中的 `0xf` 是教学小整数。真实数据见 `tests/fixtures/rsa2048_public.jsonl`。
- 相同模数可以以不同 ID 重复出现，程序先去重，再映射回全部记录。
- 输入包含 `p、q、d` 或其他字段会被拒绝。真值文件应由 B 单独保存。

## 输出与状态

JSON 报告包含 `results、duplicate_groups、summary、timings、operations`。

| 状态 | 含义 |
|---|---|
| `factor_found` | 找到并验证一个非平凡因子；输出 `factor、cofactor` |
| `no_shared_factor` | 当前输入集合中没有发现共享因子，不代表全面安全 |
| `unresolved_full_overlap` | GCD 覆盖整个模数，且尚未完成拆分 |

重复记录通过独立的 `duplicate_groups` 和每条记录的 `duplicate_count` 表示，不与因子状态混为一谈。

```powershell
# 观察三角共享结构在禁用回退时的状态；退出码为 4，报告仍写入。
python -m rsa_audit examples/toy_public_keys.jsonl --max-fallback-checks 0 --output results/unresolved.json

# 为扫描设置协作式时限；超时退出码为 3，不输出不完整的成功报告。
python -m rsa_audit tests/fixtures/rsa2048_public.jsonl --timeout 10
```

退出码：`0` 完成；`2` 输入、配置或 I/O 错误；`3` 超时；`4` 报告仍有未拆分模数。发现因子本身不会触发错误退出码。

**计时范围：** `total_seconds` 包含记录校验、去重、转换、算法、回退和结果构造；不包含后端导入、文件读取、JSON 序列化或输出写盘。两两 GCD 与批量 GCD 的比较必须使用相同后端。

## Python 接口

```python
from rsa_audit import scan_keys
from rsa_audit.io import load_public_keys

keys = load_public_keys("tests/fixtures/rsa2048_public.jsonl")
report = scan_keys(keys, method="batch", backend="python")
for result in report.results:
    if result.status == "factor_found":
        # B 从这里接入私钥恢复；Python 对象中这些字段都是整数。
        n, e, p, q = result.n, result.e, result.factor, result.cofactor
print(report.summary)
```

完整字段、预算与计时说明见 [A/B 接口说明](docs/AB_INTERFACE.md)。

## 文件结构

```text
rsa_audit/
  models.py          输入和结果类型
  scanner.py         去重、两两 GCD、批量 GCD、回退和计时
  trees.py           乘积树与平方模数余数树
  arithmetic.py      Python / gmpy2 后端
  io.py              公开 JSONL 输入和 JSON 输出
  cli.py             命令行入口
tests/
  test_scanner.py     算法、边界、随机交叉验证
  test_io_cli.py      文件与命令行测试
  test_real_size.py   2048-bit 检测和可选 OAEP 集成验证
  fixtures/          固定公钥、预期结果、OAEP 测试密文
examples/
  toy_public_keys.jsonl
docs/
  A_PRESENTATION.md  A 的原理讲解、英文讲稿、配图与问答
  AB_INTERFACE.md    给 B 的接口交接
  VALIDATION.md      验证记录和范围
```

`results/、work/、.venv/` 不纳入版本控制。运行结果应在正式实验时由 B 统一归档。

## 范围与边界

- 输入预期为标准两素数 RSA 模数；扫描器校验基本格式并验证返回的因子，不负责证明输入一定由两个素数组成。
- 默认回退会尝试拆分所有全重叠候选项；极端情况下回退仍可能带来二次级的两两检查。
- `--timeout` 在大整数运算之间检查时限，不能中断正在执行的单次乘法或求余。正式基准测试需要硬超时时，由 B 使用独立进程控制。
- 固定的 2048-bit 样本用于正确性和接口验证，不能代替 100–3000 个独立模数的正式性能实验。
- OAEP 恢复验证位于测试中，作为交接证据；B 仍负责完整恢复模块、数据生成器、正式性能分析及演示整合。

## 参考资料

- [Heninger et al., Mining Your Ps and Qs, USENIX Security 2012](https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/heninger)
- [论文 PDF，第 3.3 节](https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final228.pdf)
- [gmpy2 大整数 API](https://gmpy2.readthedocs.io/en/stable/mpz.html)
- [PyCryptodome RSA](https://www.pycryptodome.org/src/public_key/rsa)
- [PyCryptodome OAEP](https://www.pycryptodome.org/src/cipher/oaep)
