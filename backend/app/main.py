import hashlib
import json
import math
import random
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Optimization Visualizer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FUNCTIONS = {
    "rosenbrock": lambda x, y: (1 - x) ** 2 + 100 * (y - x ** 2) ** 2,
    "himmelblau": lambda x, y: (x ** 2 + y - 11) ** 2 + (x + y ** 2 - 7) ** 2,
    "rastrigin": lambda x, y: 20 + x ** 2 - 10 * math.cos(2 * math.pi * x) + y ** 2 - 10 * math.cos(2 * math.pi * y),
    "sphere": lambda x, y: x ** 2 + y ** 2,
    "beale": lambda x, y: (1.5 - x + x * y) ** 2 + (2.25 - x + x * y ** 2) ** 2 + (2.625 - x + x * y ** 3) ** 2,
    "booth": lambda x, y: (x + 2 * y - 7) ** 2 + (2 * x + y - 5) ** 2,
}

GRADIENTS = {
    "rosenbrock": lambda x, y: np.array([-2 * (1 - x) - 400 * x * (y - x ** 2), 200 * (y - x ** 2)]),
    "himmelblau": lambda x, y: np.array([4 * x * (x ** 2 + y - 11) + 2 * (x + y ** 2 - 7), 2 * (x ** 2 + y - 11) + 4 * y * (x + y ** 2 - 7)]),
    "rastrigin": lambda x, y: np.array([2 * x + 20 * math.pi * math.sin(2 * math.pi * x), 2 * y + 20 * math.pi * math.sin(2 * math.pi * y)]),
    "sphere": lambda x, y: np.array([2 * x, 2 * y]),
    "beale": lambda x, y: np.array([
        2 * (1.5 - x + x * y) * (-1 + y) + 2 * (2.25 - x + x * y ** 2) * (-1 + y ** 2) + 2 * (2.625 - x + x * y ** 3) * (-1 + y ** 3),
        2 * (1.5 - x + x * y) * x + 2 * (2.25 - x + x * y ** 2) * (2 * x * y) + 2 * (2.625 - x + x * y ** 3) * (3 * x * y ** 2)
    ]),
    "booth": lambda x, y: np.array([2 * (x + 2 * y - 7) + 4 * (2 * x + y - 5), 4 * (x + 2 * y - 7) + 2 * (2 * x + y - 5)]),
}

HESSIANS = {
    "rosenbrock": lambda x, y: np.array([
        [2 - 400 * y + 1200 * x ** 2, -400 * x],
        [-400 * x, 200]
    ]),
    "sphere": lambda x, y: np.array([[2, 0], [0, 2]]),
    "booth": lambda x, y: np.array([[10, 8], [8, 10]]),
}

ALGORITHMS = {"gradient_descent", "newton", "conjugate_gradient", "simulated_annealing"}

MAX_BATCH_SIZE = 100
MAX_ITERATIONS = 2000


class OptimizationRequest(BaseModel):
    algorithm: str = "gradient_descent"
    functionId: str = "rosenbrock"
    x0: float = -1.5
    y0: float = 2.5
    learningRate: float = 0.01
    iterations: int = 100
    momentum: float = 0.9
    temperature: float = 100.0
    coolingRate: float = 0.95


class BatchOptimizationRequest(BaseModel):
    items: list[OptimizationRequest]


def _ensure_finite(x, y, z, step):
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        raise ValueError(f"数值发散：第 {step} 步出现 NaN/Inf，请降低学习率或调整初始点")


def run_optimization(req: OptimizationRequest) -> dict:
    """执行单组试算，参数非法或数值发散时抛出 ValueError（信息面向教学场景）。"""
    if req.functionId not in FUNCTIONS:
        raise ValueError(f"未知的测试函数：{req.functionId}")
    if req.algorithm not in ALGORITHMS:
        raise ValueError(f"未知的优化算法：{req.algorithm}")
    if req.iterations < 1:
        raise ValueError("迭代次数必须 ≥ 1")
    if req.iterations > MAX_ITERATIONS:
        raise ValueError(f"迭代次数不能超过 {MAX_ITERATIONS}")
    if req.learningRate <= 0:
        raise ValueError("学习率必须为正数")
    if not (math.isfinite(req.x0) and math.isfinite(req.y0)):
        raise ValueError("初始点坐标必须是有限数值")
    if req.algorithm == "simulated_annealing" and req.temperature <= 0:
        raise ValueError("模拟退火的初始温度必须为正数")

    fn = FUNCTIONS[req.functionId]
    grad_fn = GRADIENTS.get(req.functionId)
    g_fn = grad_fn if grad_fn else (lambda x, y: np.array([
        (fn(x + 1e-5, y) - fn(x - 1e-5, y)) / 2e-5,
        (fn(x, y + 1e-5) - fn(x, y - 1e-5)) / 2e-5
    ]))

    x, y = req.x0, req.y0
    z = fn(x, y)
    _ensure_finite(x, y, z, 0)
    path = [{"step": 0, "x": x, "y": y, "z": z}]

    if req.algorithm == "gradient_descent":
        vx, vy = 0.0, 0.0
        for i in range(req.iterations):
            g = g_fn(x, y)
            vx = req.momentum * vx - req.learningRate * g[0]
            vy = req.momentum * vy - req.learningRate * g[1]
            x += vx; y += vy
            z = fn(x, y)
            _ensure_finite(x, y, z, i + 1)
            path.append({"step": i + 1, "x": x, "y": y, "z": z})

    elif req.algorithm == "newton":
        hess_fn = HESSIANS.get(req.functionId)
        if hess_fn is None:
            # fallback to gradient descent
            for i in range(req.iterations):
                g = g_fn(x, y)
                x -= req.learningRate * g[0]
                y -= req.learningRate * g[1]
                z = fn(x, y)
                _ensure_finite(x, y, z, i + 1)
                path.append({"step": i + 1, "x": x, "y": y, "z": z})
        else:
            for i in range(req.iterations):
                g = g_fn(x, y)
                H = hess_fn(x, y)
                try:
                    dx = np.linalg.solve(H, -g)
                except np.linalg.LinAlgError:
                    dx = -g * req.learningRate
                x += dx[0]; y += dx[1]
                z = fn(x, y)
                _ensure_finite(x, y, z, i + 1)
                path.append({"step": i + 1, "x": x, "y": y, "z": z})

    elif req.algorithm == "conjugate_gradient":
        g = g_fn(x, y)
        d = -g.copy()
        for i in range(req.iterations):
            # Line search (simple)
            alpha = req.learningRate
            x_new = x + alpha * d[0]
            y_new = y + alpha * d[1]
            z_new = fn(x_new, y_new)
            _ensure_finite(x_new, y_new, z_new, i + 1)
            g_new = g_fn(x_new, y_new)
            beta = max(0, (g_new @ g_new) / (g @ g + 1e-10))
            d = -g_new + beta * d
            x, y, g = x_new, y_new, g_new
            path.append({"step": i + 1, "x": x, "y": y, "z": z_new})

    elif req.algorithm == "simulated_annealing":
        T = req.temperature
        best_x, best_y = x, y
        best_z = fn(x, y)
        for i in range(req.iterations):
            nx = x + random.gauss(0, T / req.temperature * 2)
            ny = y + random.gauss(0, T / req.temperature * 2)
            nz = fn(nx, ny)
            if not math.isfinite(nz):
                continue
            delta = nz - fn(x, y)
            if delta < 0 or random.random() < math.exp(-delta / max(T, 1e-5)):
                x, y = nx, ny
                if fn(x, y) < best_z:
                    best_x, best_y = x, y
                    best_z = fn(x, y)
            T *= req.coolingRate
            path.append({"step": i + 1, "x": x, "y": y, "z": fn(x, y)})

    final = path[-1]
    prev = path[-2] if len(path) > 1 else None
    converged = bool(abs(final["z"]) < 1e-6 or (prev is not None and abs(final["z"] - prev["z"]) < 1e-9))
    return {
        "params": req.model_dump(),
        "path": path,
        "finalPoint": [final["x"], final["y"]],
        "finalValue": final["z"],
        "iterations": len(path) - 1,
        "converged": converged
    }


def combo_key(req: OptimizationRequest) -> str:
    """参数组合指纹：同一批或重复提交中用于去重。"""
    payload = json.dumps(req.model_dump(), sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:12]


@app.post("/api/optimize")
def optimize(req: OptimizationRequest):
    try:
        return run_optimization(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/optimize/batch")
def optimize_batch(req: BatchOptimizationRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="批量任务至少包含一组参数组合")
    if len(req.items) > MAX_BATCH_SIZE:
        raise HTTPException(status_code=400, detail=f"单批最多提交 {MAX_BATCH_SIZE} 组参数组合")

    results = []
    seen = set()
    duplicates = 0
    # 逐组执行：单组失败只记录该组原因，其余组合继续跑完
    for item in req.items:
        key = combo_key(item)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        try:
            res = run_optimization(item)
            results.append({
                "key": key,
                "status": "ok",
                "params": item.model_dump(),
                "finalPoint": res["finalPoint"],
                "finalValue": res["finalValue"],
                "iterations": res["iterations"],
                "converged": res["converged"],
            })
        except Exception as e:
            results.append({
                "key": key,
                "status": "error",
                "params": item.model_dump(),
                "error": str(e),
            })

    succeeded = sum(1 for r in results if r["status"] == "ok")
    return {
        "total": len(req.items),
        "deduplicated": duplicates,
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    }
