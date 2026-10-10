# SC6104 — RSA 共享素因子检测

**项目题目：弱随机性下 RSA 共享素因子的批量检测与私钥恢复。**

本仓库整合 A 的检测引擎与 B 的数据生成、私钥恢复、OAEP、独立评估、性能实验及完整演示。A 的算法仍在 `rsa_audit/`，B 的 `rsa_lab/detection.py` 只转换接口并调用该引擎。

固定样本包含真实的 2048-bit RSA 模数。扫描器只接收公开的 `id、n、e`，不读取生成时的因子或私钥。完整攻击完成后才由独立评估阶段读取真值。

## 整合版快速入口

先阅读 [开始使用](START_HERE.md) 和 [接口整合记录](docs/INTEGRATION.md)。最终总展示在 [presentation/final.html](presentation/final.html)，原来的三页动画继续保留。

```powershell
python -m pip install -r requirements.txt
python -X utf8 -m rsa_lab demo
python -X utf8 -m rsa_lab validate
python -X utf8 -m unittest discover -s tests -v
```

完整 demo 检测 100 个不同的 2048 位模数，包含 2 条重复记录，恢复 5 个不同模数并验证 6 条 OAEP 密文。`scan` 与 `recover` 在独立进程中运行，只接收公开输入。新密钥更换后重新扫描。`validate` 在 demo 之后运行，验证正常密钥、纯重复记录、孤立弱目标、共享素因子和修复后集合，两种算法共 10 次扫描，并检查错误 OAEP label 与被修改的密文。70 项 Python 测试全部通过。

总展示的 8 页、按钮和补充证据窗口使用英文；页面不含演讲提示。配套 [8 分钟讲稿与现场操作](docs/FINAL_SPEECH.md) 单独存放，包含两人分工、英文口播和中文问答说明。[GitHub 交接清单](docs/GITHUB_HANDOFF.md) 列明上传范围与两人整合步骤。

双击 `run_presentation.cmd`，打开 `http://127.0.0.1:8765/presentation/final.html`。第 6 页的 **Run Python pipeline** 可实际调用原有扫描与恢复模块，显示命令输出、六条明文核对和换钥集合重扫结果；失败会显示错误。现场单次耗时与历史性能图独立呈现。直接打开 HTML 仍可离线查看动画和归档结果；具体说明见 [展示说明](presentation/README.md)。

```powershell
python -X utf8 -m rsa_lab prepare-bench --sizes 100,300,1000,3000
python -X utf8 -m rsa_lab benchmark --sizes 100,300,1000,3000 --repeats 3 --timeout 45 --backend gmpy2
python -X utf8 -m rsa_lab plot
python -X utf8 -m rsa_lab pool-experiment --count 60 --sizes 4,16,64 --repeats 3
.\run_tests.ps1
python -X utf8 -m rsa_lab report
python -X utf8 scripts/export_showcase.py
python -X utf8 scripts/verify_showcase.py
```

本整合版测量见 [实测报告](artifacts/RESULTS.md)。算法计时来自 A 引擎，包含转换、树结构、GCD、回退和结果构造，不包含适配层格式转换、文件 I/O 和之后的私钥恢复。全量随机实验数据保留本地，Git 中归档配置、输入哈希、原始测量与图表。重新生成具有相同结构的数据可复测方法，但随机素数与耗时不保证完全相同。

## 从这里开始

1. 阅读 [A 的演讲与理解材料](docs/A_PRESENTATION.md)，建立整体理解。
2. 运行下面的小样本与 2048-bit 样本。
3. 按演讲材料的阅读顺序看代码。
4. 把 [A/B 接口说明](docs/AB_INTERFACE.md) 发给队友。
5. 阅读 [实现与验证记录](docs/VALIDATION.md)，了解已经验证的范围。

课堂讲解可直接打开 [三页动画 HTML](presentation/index.html)：共享素因子攻击、乘积树／余数树、去重与全重叠回退。支持离线播放、键盘逐步控制、全屏和中文讲解提示；操作说明见 [presentation/README.md](presentation/README.md)。

## 快速运行

需要 Python 3.10 或以上。所有命令都在仓库根目录执行。下面的 A 基础检测命令只使用 Python 标准库，完整 B 实验需要上面的 requirements.txt。

```powershell
python -m rsa_audit examples/toy_public_keys.jsonl
python -m rsa_audit tests/fixtures/rsa2048_public.jsonl --output results/batch.json
python -m rsa_audit tests/fixtures/rsa2048_public.jsonl --method pairwise --output results/pairwise.json
python -m unittest discover -v
```

在仓库内创建 `.venv` 后，可直接使用：

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
- `e`：JSON 整数；A/B 新生成的公开输入统一采用该格式，并保留每条记录各自的指数。
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

`results/、work/、data/、.venv/` 不纳入版本控制。B 已将正式结果归档到 `artifacts/`。运行 `scripts/export_showcase.py` 可根据新结果更新归档及离线展示数据。

## 范围与边界

- 输入预期为标准两素数 RSA 模数；扫描器校验基本格式并验证返回的因子，不负责证明输入一定由两个素数组成。
- 默认回退会尝试拆分所有全重叠候选项；极端情况下回退仍可能带来二次级的两两检查。
- `--timeout` 在大整数运算之间检查时限，不能中断正在执行的单次乘法或求余。正式基准测试需要硬超时时，由 B 使用独立进程控制。
- 固定的 2048-bit 样本用于正确性和接口验证，不能代替 100–3000 个独立模数的正式性能实验。
- 固定 OAEP 挑战继续作为交接测试。完整恢复、数据生成、正式性能分析及演示已在 `rsa_lab/` 中实现。

## 参考资料

- [Heninger et al., Mining Your Ps and Qs, USENIX Security 2012](https://www.usenix.org/conference/usenixsecurity12/technical-sessions/presentation/heninger)
- [论文 PDF，第 3.3 节](https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final228.pdf)
- [gmpy2 大整数 API](https://gmpy2.readthedocs.io/en/stable/mpz.html)
- [PyCryptodome RSA](https://www.pycryptodome.org/src/public_key/rsa)
- [PyCryptodome OAEP](https://www.pycryptodome.org/src/cipher/oaep)
