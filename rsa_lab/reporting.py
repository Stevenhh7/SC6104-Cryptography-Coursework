"""Create a Chinese report and speaking notes from completed experiment files."""

from pathlib import Path
from .models import read_json
from .plots import read_csv


def build_report(root):
    root = Path(root)
    demo = read_json(root / "results/demo/verification.json")
    repaired = read_json(root / "results/demo/scan_repaired.json")
    summary = read_csv(root / "results/benchmark/summary.csv")
    env = read_json(root / "results/benchmark/environment.json")
    raw = read_csv(root / "results/benchmark/raw_results.csv")
    manifest = read_json(root / "data/bench/corpus/manifest.json")
    pairs = {int(row["unique_moduli"]): row for row in summary if row["algorithm"] == "pairwise"}
    batch = {int(row["unique_moduli"]): row for row in summary if row["algorithm"] == "batch"}
    table = []
    for size in sorted(batch):
        left, right = pairs[size], batch[size]
        a = float(left["median_seconds"]) if left["median_seconds"] else None
        b = float(right["median_seconds"]) if right["median_seconds"] else None
        speedup = f"{a / b:.2f} 倍" if a is not None and b is not None else "不计算"
        first = f"{a:.6f}" if a is not None else f"{left['timeouts']}/{left['total_runs']} 次超时"
        second = f"{b:.6f}" if b is not None else f"{right['timeouts']}/{right['total_runs']} 次超时"
        weak = read_json(root / f"data/bench/n-{size}/manifest.json")["actual_vulnerable_moduli"]
        table.append(f"| {size} | {weak} | {first} | {second} | {speedup} |")
    successful = [row for row in raw if row["status"] == "ok"]
    report = f"""# 本机实测结果

所有数字来自交付中的原始 CSV 和 JSON。没有用估算填补超时结果。

## 攻击与修复

- 演示输入为 100 个不同的实际 2048-bit 模数，共 102 条记录。
- 独立预期可恢复 {demo['expected_recoverable_moduli']} 个不同模数，实际正确分解 {demo['correctly_factored_moduli']} 个。
- OAEP 明文通过验证的不同模数为 {demo['verified_decryption_moduli']} 个，密文记录为 {demo['verified_decryption_records']} 条。
- 误报 {demo['false_positives']}，遗漏 {demo['false_negatives']}，错误因子 {demo['invalid_factors']}。
- 密钥更换后，当前集合检测到的可分解模数为 {repaired['summary']['factor_found']} 个。
- 三角结构触发回退，原始扫描细节保存在 results/demo/scan_batch.json。

## 性能

两算法调用同一 rsa_audit.scan_keys 引擎，使用相同固定数据与 {env['backend']} 后端，每条件 3 次，全新进程运行。计时采用 A 引擎的 total_seconds，包含记录校验、去重、后端转换、主算法、回退及结果组装。扫描计时不包含 B 接口转换、生成、I/O、恢复和评估。

| 不同模数数 | 实际可恢复数 | 两两 GCD 中位秒数 | 批量 GCD 中位秒数 | 两两/批量耗时比 |
|---|---|---|---|---|
{chr(10).join(table)}

完成的 {len(successful)} 次扫描均执行独立因子和 OAEP 明文验证。3000 规模的两两算法若显示超时，表示整个工作进程超过 45 秒限额，不代表它的完整扫描恰好耗时 45 秒。超时结果不进入中位数，也不计算对应提升倍数。

小规模真实弱比例见 data/bench/n-*/manifest.json 和 raw_results.csv。共享关系以整对安排，100 和 300 的比例略高于 5%，1000 与 3000 为 5%。每个规模两算法使用相同集合。

corpus 的素数及密钥构造用时约 {manifest['generation_seconds']:.2f} 秒，单独记录。这个时间不包括随后的所有文件保存和 OAEP 密文制作，因此不是整个数据准备命令的总墙钟耗时。

![扫描耗时](results/figures/scan_times.png)

![批量阶段耗时](results/figures/batch_stages.png)

误差条表示三次观察值的最小与最大范围，不是置信区间。阶段图采用各阶段分别的中位数，分量中位数之和不一定等于总耗时中位数。

## 运行环境

- Python：{env['python'].splitlines()[0]}
- 平台：{env['platform']}
- CPU：{env['cpu']}，逻辑核数 {env['logical_cpus']}
- 物理内存：{env.get('physical_memory_bytes', 0) / 1024**3:.2f} GiB
- 依赖版本：{env['packages']}
- 峰值 RSS：操作系统对整个扫描工作进程的记录，包含导入和输入，详见 CSV。

## 结论的边界

实验使用受控的本地弱密钥，不声称这些样本比例对应现实设备。提升倍数只对应当前数据、硬件和实现。重新扫描无共享因子只验证了当前集合的这一类关系。OAEP 解密说明私钥恢复后的影响，没有说明 OAEP 本身失效。
"""
    pool_file = root / "results/pool/pool_results.csv"
    if pool_file.exists():
        from statistics import median
        from collections import defaultdict
        groups = defaultdict(list)
        for row in read_csv(pool_file):
            groups[int(row["pool_size"])].append(float(row["vulnerable_fraction"]))
        report += "\n## 弱素数池扩展\n\n固定每集合 60 把公钥，各条件实际结果如下。种子只控制选池槽位。\n\n| 素数池大小 | 实际可恢复比例中位数 |\n|---|---|\n"
        report += "\n".join(f"| {size} | {median(groups[size]):.1%} |" for size in sorted(groups))
        report += "\n\n![素数池实验](results/pool/weak_pool.png)\n"
    controls_file = root / "results/controls/validation.json"
    if controls_file.exists():
        controls = read_json(controls_file)
        report += "\n## 正负对照与覆盖范围\n\n每种集合分别通过批量与两两检测，再独立核验因子和明文。\n\n| 集合 | 算法 | 记录/不同模数 | 正确分解 | 验证明文 | 误报/遗漏 | 通过 |\n|---|---|---|---|---|---|---|\n"
        report += "\n".join(
            f"| {row['case']} | {row['algorithm']} | {row['records']}/{row['unique_moduli']} | {row['correctly_factored']} | {row['verified_messages']} | {row['false_positives']}/{row['false_negatives']} | {row['passed']} |"
            for row in controls["cases"])
        report += f"\n\n这些集合的实际模数长度均为 {controls['summary']['bits']} 位。错误 OAEP label 和被修改的密文均被拒绝，{controls['summary']['oaep_negative_checks']} 项负向检查通过。孤立目标的零恢复结果说明攻击依赖其他公钥覆盖共享关系。两种算法共 {controls['summary']['scan_runs']} 次扫描，整体通过：{controls['summary']['passed']}。\n"
    (root / "RESULTS.md").write_text(report, encoding="utf-8", newline="\n")

    from .presentation_notes import write_notes
    write_notes(root)
    return str(root / "RESULTS.md")
