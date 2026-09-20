# 数值优化算法逐帧可视化教学平台

基于Vue 3 + FastAPI的优化算法交互式教学工具，支持梯度下降/牛顿法/共轭梯度/模拟退火四种算法的2D等高线与3D曲面双视图可视化。

## 目标用户
机器学习方向学生、优化理论研究者、算法教学者

## 技术栈
- 前端: Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts + Three.js
- 后端: Python FastAPI + NumPy + SciPy

## 核心功能
1. 四种优化算法实现：梯度下降、牛顿法、共轭梯度、模拟退火
2. 2D函数等高线绘制(Canvas) + 3D曲面(Three.js)双视图同步渲染
3. 步长、动量、初始点等参数实时调节
4. 优化路径逐帧动画播放，显示迭代收敛轨迹
5. 预设6种测试函数(Rosenbrock/Himmelblau/Rastrigin/Sphere/Beale/Booth)
6. 收敛曲线(ECharts)显示每步函数值下降
7. 批量试算：一次提交多组初始位置与参数组合，逐组执行并以并排列表展示最终取值与收敛情况

## 批量试算
- 顶部可在「单组试算 / 批量试算」之间切换；两块视图同时挂载、仅切换显隐，切回单组时上一次结果与动画进度不会被冲掉
- 批量面板可增删/复制任意组参数组合（函数、算法、初始点、学习率、迭代数及算法专属参数）
- 后端后台线程逐组执行：单组参数非法或数值发散时只在该行注明原因，其余组合继续跑完
- 结果并排成表：参数、状态、最终点 (x,y)、最终取值、迭代步数、是否收敛及收敛/失败原因
- 同一批组合重复提交（含行序打乱）按内容指纹幂等，直接返回原批次；批内完全重复的行会在前端折叠
- 批次进度与结果快照写入 localStorage，刷新页面后仍可查看，并自动与服务端轮询对账更新完成情况

### 批量 API
- `POST /api/batches` — `{ "combinations": [OptimizationParams, ...] }`，单次最多 50 组；返回批次（已存在同内容批次时带 `existed: true`）
- `GET /api/batches` / `GET /api/batches/{id}` — 批次列表 / 详情（轮询执行进度）
- `DELETE /api/batches/{id}` — 删除批次（删除后同内容可作为新批次重新提交）

## 项目结构
```
solo-6600050/
├── frontend/         Vue 3 + TypeScript + Vite
│   └── src/components/
│       ├── ContourPlot.vue       # Canvas 2D等高线
│       ├── Surface3D.vue         # Three.js 3D曲面
│       ├── ControlPanel.vue      # 参数面板
│       └── ConvergenceChart.vue  # ECharts收敛曲线
└── backend/          FastAPI + NumPy + SciPy
    └── app/main.py
```