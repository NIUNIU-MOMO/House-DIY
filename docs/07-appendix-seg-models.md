# 附录：Segmentation 模型（M3）

> 对应 [07-户型解析优化方案与需求](./07-户型解析优化方案与需求.md) Phase 5 / §4.3.1 M3。

## 目标

专用 **墙/房间 segmentation** 用于：

- 彩色营销图：从墙体围合提取候选 polygon，辅助 VLM 贴墙
- CAD 线稿：形态学回退可在无 ONNX 时给出区域参考
- benchmark：对比 VLM 房间数 vs seg 区域数

**注意：** M3 不替代 VLM 与 FR-D 质检；初稿仍以分步 VLM 为主，seg 为辅助与评测。

## 配置

`server/.env`：

```env
# 启用 segmentation（未配置 ONNX 时使用 OpenCV 形态学回退）
HOUSE_DIY_SEG_ENABLED=true

# 将 seg 区域作为 VLM Step2 几何 hint（依赖 SEG_ENABLED）
HOUSE_DIY_SEG_HINT_ENABLED=true

# 可选：ONNX 模型绝对路径（需自行下载/转换）
HOUSE_DIY_SEG_MODEL_PATH=~/models/floorplan-room-seg.onnx
```

依赖：

- 基础：`opencv-python-headless`（已包含）
- ONNX 推理（可选）：`pip install onnxruntime`

## 代码入口

| 模块 | 说明 |
|------|------|
| `server/app/services/floorplan/parser_seg.py` | `extract_room_regions()`、`benchmark_seg_region_count()` |
| `server/app/services/floorplan/seg_hint.py` | seg 区域简化与 Step2 prompt hint 序列化 |
| `scripts/benchmark-floorplan-vlm.sh` | VLM + seg 对比表（`--seg-hint` 注入 hint） |

## 推荐模型选型（评估清单）

| 候选 | 格式 | 体积 | 说明 |
|------|------|------|------|
| DeepLabV3-MobileNet（自训/微调） | ONNX | ~15MB | 房间语义分割，CPU 可跑 |
| U-Net 轻量墙线分割 | ONNX | ~8MB | 二值墙 mask → 形态学填洞 |
| SAM / FastSAM | ONNX | 较大 | 通用分割，需后处理筛房间 |

**选型门禁：** 换模型前后跑 `scripts/benchmark-floorplan-vlm.sh --mock --seg`（离线）及 `--live --seg`（真实 oMLX），对比：

- seg 区域数 vs VLM 房间数
- 解析耗时
- 质检 validation.level 分布

未达标不切换生产 alias。

## Benchmark 用法

```bash
# 离线 mock（CI / 无 oMLX）
./scripts/benchmark-floorplan-vlm.sh --mock

# 含 segmentation 统计
./scripts/benchmark-floorplan-vlm.sh --mock --seg

# 含 seg hint 注入 Step2 + Seg/VLM 交叉校验
./scripts/benchmark-floorplan-vlm.sh --mock --seg-hint

# 真实 oMLX（需 house-vlm-pro 可用）
./scripts/benchmark-floorplan-vlm.sh --live
```

输出列为 TSV：`sample`、`vlm_model`、`rooms`、`validation`、`seg`、`seg_backend`、`seg_hint` 等。

## Seg Hint 与质检

- **Step2 hint**：`seg_hint.py` 将 top-8 seg 区域（≤8 顶点）序列化注入 VLM Step2 prompt，提示模型以墙体线为准、忽略色块/家具。
- **交叉校验**：`parser_validate` 新增 `SEG_VLM_MISMATCH`（warning），当 room 与最近 seg 区域 IoU 低于阈值时告警（cad 0.12 / marketing 0.08）。
- **parse_meta**：`seg_hint_used`、`seg_match_warnings` 记录 hint 是否注入及不一致房间数。
- **零回归**：`HOUSE_DIY_SEG_ENABLED=false` 或 `HOUSE_DIY_SEG_HINT_ENABLED=false` 时行为与 Phase 6 一致。

## 后续集成（非本期阻塞）

- LoRA / 专用小模型（M4）长期边际提升
