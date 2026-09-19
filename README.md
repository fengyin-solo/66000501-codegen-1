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