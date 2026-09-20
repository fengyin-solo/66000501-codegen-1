import math
import random
import threading
import hashlib
import json
import time
import uuid
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

GRAD_TOL = 1e-6
F_TOL = 1e-3
MAX_COORDS = 1e6
MAX_BATCH_ITEMS = 50


class OptimizeError(ValueError):
    """参数非法或计算无法完成，错误信息可直接展示给用户。"""


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


class BatchCreateRequest(BaseModel):
    combinations: list[dict]


def validate_params(p: dict) -> dict:
    """校验并补齐一组参数，非法时抛 OptimizeError（仅影响该组）。"""
    q = dict(p)
    algorithm = q.get("algorithm", "gradient_descent")
    function_id = q.get("functionId", "rosenbrock")
    if algorithm not in ALGORITHMS:
        raise OptimizeError(f"不支持的算法：{algorithm}")
    if function_id not in FUNCTIONS:
        raise OptimizeError(f"不支持的测试函数：{function_id}")

    defaults = {"x0": -1.5, "y0": 2.5, "learningRate": 0.01, "iterations": 100,
                "momentum": 0.9, "temperature": 100.0, "coolingRate": 0.95}
    for key, default in defaults.items():
        q[key] = q.get(key, default)
        if type(q[key]) is bool or not isinstance(q[key], (int, float)):
            raise OptimizeError(f"参数 {key} 必须是数值")
        q[key] = float(q[key]) if key != "iterations" else int(q[key])
        if not math.isfinite(q[key]):
            raise OptimizeError(f"参数 {key} 必须是有限数值")

    x0, y0 = q["x0"], q["y0"]
    if abs(x0) > 1e4 or abs(y0) > 1e4:
        raise OptimizeError("初始位置超出允许范围（±10000）")
    if q["iterations"] < 1 or q["iterations"] > 1000:
        raise OptimizeError("迭代次数需在 1~1000 之间")
    if not (0 < q["learningRate"] <= 10):
        raise OptimizeError("学习率需在 (0, 10] 范围内")
    if not (0 <= q["momentum"] < 1):
        raise OptimizeError("动量需在 [0, 1) 范围内")
    if q["temperature"] <= 0:
        raise OptimizeError("初始温度必须大于 0")
    if not (0 < q["coolingRate"] < 1):
        raise OptimizeError("冷却系数需在 (0, 1) 范围内")
    q["algorithm"] = algorithm
    q["functionId"] = function_id
    return q


def _finite_z(fn, x, y):
    z = fn(x, y)
    if not np.isfinite(z) or abs(z) > 1e12:
        raise OptimizeError("数值发散：目标函数值超出可表示范围，请调小学习率或更换初始点")
    return float(z)


def run_algorithm(raw: dict) -> dict:
    """执行一次试算，返回最终取值与收敛信息；失败时抛 OptimizeError。"""
    req = validate_params(raw)
    fn = FUNCTIONS[req["functionId"]]
    grad_fn = GRADIENTS.get(req["functionId"])

    def g_fn(x, y):
        if grad_fn is not None:
            g = grad_fn(x, y)
        else:
            g = np.array([
                (fn(x + 1e-5, y) - fn(x - 1e-5, y)) / 2e-5,
                (fn(x, y + 1e-5) - fn(x, y - 1e-5)) / 2e-5
            ])
        if not np.all(np.isfinite(g)) or np.max(np.abs(g)) > MAX_COORDS:
            raise OptimizeError("数值发散：梯度超出可表示范围，请调小学习率或更换初始点")
        return g

    x, y = req["x0"], req["y0"]
    path = [{"step": 0, "x": x, "y": y, "z": _finite_z(fn, x, y)}]
    iterations = req["iterations"]
    algorithm = req["algorithm"]
    converged = False
    convergence_reason = ""
    # 模拟退火维护当前找到的最优点
    best_x, best_y, best_z = x, y, path[0]["z"]

    try:
        if algorithm == "gradient_descent":
            vx = vy = 0.0
            for i in range(iterations):
                g = g_fn(x, y)
                vx = req["momentum"] * vx - req["learningRate"] * g[0]
                vy = req["momentum"] * vy - req["learningRate"] * g[1]
                x += float(vx); y += float(vy)
                if abs(x) > MAX_COORDS or abs(y) > MAX_COORDS:
                    raise OptimizeError("数值发散：迭代位置超出可表示范围，请调小学习率或更换初始点")
                z = _finite_z(fn, x, y)
                path.append({"step": i + 1, "x": x, "y": y, "z": z})
                if np.linalg.norm(g) < GRAD_TOL:
                    converged = True
                    convergence_reason = f"梯度范数 {np.linalg.norm(g):.2e} < {GRAD_TOL:.0e}"
                    break
                if abs(z) < F_TOL:
                    converged = True
                    convergence_reason = f"函数值 {z:.2e} 的绝对值 < {F_TOL:.0e}"
                    break

        elif algorithm == "newton":
            hess_fn = HESSIANS.get(req["functionId"])
            for i in range(iterations):
                g = g_fn(x, y)
                if hess_fn is None:
                    dx = -req["learningRate"] * g
                else:
                    H = hess_fn(x, y)
                    try:
                        dx = np.linalg.solve(H, -g)
                    except np.linalg.LinAlgError:
                        dx = -g * req["learningRate"]
                x += float(dx[0]); y += float(dx[1])
                if abs(x) > MAX_COORDS or abs(y) > MAX_COORDS:
                    raise OptimizeError("数值发散：迭代位置超出可表示范围，请检查该函数是否适合牛顿法")
                z = _finite_z(fn, x, y)
                path.append({"step": i + 1, "x": x, "y": y, "z": z})
                if np.linalg.norm(g) < GRAD_TOL:
                    converged = True
                    convergence_reason = f"梯度范数 {np.linalg.norm(g):.2e} < {GRAD_TOL:.0e}"
                    break
                if np.linalg.norm(dx) < GRAD_TOL:
                    converged = True
                    convergence_reason = f"更新步长 {np.linalg.norm(dx):.2e} < {GRAD_TOL:.0e}"
                    break

        elif algorithm == "conjugate_gradient":
            g = g_fn(x, y)
            d = -g.copy()
            for i in range(iterations):
                alpha = req["learningRate"]
                x_new = x + alpha * d[0]
                y_new = y + alpha * d[1]
                if abs(x_new) > MAX_COORDS or abs(y_new) > MAX_COORDS:
                    raise OptimizeError("数值发散：迭代位置超出可表示范围，请调小学习率或更换初始点")
                z = _finite_z(fn, x_new, y_new)
                g_new = g_fn(x_new, y_new)
                beta = max(0.0, float((g_new @ g_new) / (g @ g + 1e-10)))
                d = -g_new + beta * d
                x, y, g = x_new, y_new, g_new
                path.append({"step": i + 1, "x": x, "y": y, "z": z})
                if np.linalg.norm(g) < GRAD_TOL:
                    converged = True
                    convergence_reason = f"梯度范数 {np.linalg.norm(g):.2e} < {GRAD_TOL:.0e}"
                    break
                if abs(z) < F_TOL:
                    converged = True
                    convergence_reason = f"函数值 {z:.2e} 的绝对值 < {F_TOL:.0e}"
                    break

        elif algorithm == "simulated_annealing":
            T = req["temperature"]
            for i in range(iterations):
                nx = x + random.gauss(0, T / req["temperature"] * 2)
                ny = y + random.gauss(0, T / req["temperature"] * 2)
                if abs(nx) > MAX_COORDS or abs(ny) > MAX_COORDS:
                    # 跳到了不可表示的位置，视为被拒绝，继续降温
                    nx, ny = x, y
                nz = fn(nx, ny)
                if not np.isfinite(nz) or abs(nz) > 1e12:
                    nx, ny, nz = x, y, fn(x, y)
                cur_z = fn(x, y)
                delta = nz - cur_z
                if delta < 0 or (T > 1e-5 and random.random() < math.exp(-delta / max(T, 1e-5))):
                    x, y = nx, ny
                    if fn(x, y) < best_z:
                        best_x, best_y = x, y
                        best_z = float(fn(x, y))
                T *= req["coolingRate"]
                z = float(fn(x, y))
                path.append({"step": i + 1, "x": x, "y": y, "z": z})
            converged = abs(best_z) < F_TOL
            if converged:
                convergence_reason = f"历史最优点函数值 {best_z:.2e} 的绝对值 < {F_TOL:.0e}"
            else:
                convergence_reason = f"达到最大迭代次数 {iterations}，历史最优函数值 {best_z:.4g} 未满足容差"
    except OverflowError as exc:
        raise OptimizeError("数值溢出，无法完成计算，请调小学习率或更换初始点") from exc

    final = path[-1]
    used_steps = len(path) - 1
    if algorithm != "simulated_annealing" and not converged:
        convergence_reason = f"达到最大迭代次数 {iterations}，梯度范数 {np.linalg.norm(g):.4g} 未满足容差"

    if algorithm == "simulated_annealing":
        final_point = [float(best_x), float(best_y)]
        final_value = float(best_z)
    else:
        final_point = [float(final["x"]), float(final["y"])]
        final_value = float(final["z"])

    return {
        "params": req,
        "path": path,
        "finalPoint": final_point,
        "finalValue": final_value,
        "iterations": used_steps,
        "converged": converged,
        "convergenceReason": convergence_reason
    }


@app.post("/api/optimize")
def optimize(req: OptimizationRequest):
    try:
        return run_algorithm(req.model_dump())
    except OptimizeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------- 批量试算 ----------------

_batches: dict[str, dict] = {}
_batches_lock = threading.Lock()
# 内容指纹 -> 批次 id，同一批组合重复提交只保留一次结果
_fingerprint_index: dict[str, str] = {}


def _combo_fingerprint(combo: dict) -> str:
    try:
        norm = validate_params(combo)
    except OptimizeError:
        # 参数非法的组合也需要稳定指纹，用原始键值对归一化排序
        norm = {k: combo.get(k) for k in sorted(combo.keys())}
    blob = json.dumps(norm, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _batch_fingerprint(combinations: list[dict]) -> str:
    # 组合排列顺序不影响批次身份；组合内重复项作为多重集参与
    parts = sorted(_combo_fingerprint(c) for c in combinations)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _run_batch(batch_id: str, combinations: list[dict]) -> None:
    """后台逐组执行：单组失败只记录该组原因，其余继续跑完。"""
    for idx in range(len(combinations)):
        with _batches_lock:
            item = _batches[batch_id]["items"][idx]
            if item["status"] == "failed":
                continue  # 提交前预校验已确定原因的组合
            item["status"] = "running"
        started = time.time()
        try:
            res = run_algorithm(combinations[idx])
            outcome = {
                "status": "success",
                "finalPoint": res["finalPoint"],
                "finalValue": res["finalValue"],
                "iterations": res["iterations"],
                "converged": res["converged"],
                "convergenceReason": res["convergenceReason"],
                "durationMs": int((time.time() - started) * 1000),
            }
        except OptimizeError as exc:
            outcome = {"status": "failed", "error": str(exc),
                       "durationMs": int((time.time() - started) * 1000)}
        except Exception as exc:  # 防御性兜底，绝不让单组异常中断整批
            outcome = {"status": "failed", "error": f"计算失败：{type(exc).__name__}",
                       "durationMs": int((time.time() - started) * 1000)}
        with _batches_lock:
            _batches[batch_id]["items"][idx].update(outcome)

    with _batches_lock:
        batch = _batches[batch_id]
        batch["status"] = "completed"
        batch["finishedAt"] = time.time()
        batch["summary"] = {
            "total": len(batch["items"]),
            "succeeded": sum(1 for it in batch["items"] if it["status"] == "success"),
            "failed": sum(1 for it in batch["items"] if it["status"] == "failed"),
            "converged": sum(1 for it in batch["items"] if it.get("converged")),
        }


def _public_batch(batch: dict) -> dict:
    return dict(batch)


@app.post("/api/batches")
def create_batch(req: BatchCreateRequest):
    combinations = req.combinations
    if not combinations:
        raise HTTPException(status_code=422, detail="至少提交一组参数组合")
    if len(combinations) > MAX_BATCH_ITEMS:
        raise HTTPException(status_code=422, detail=f"单次批量试算最多 {MAX_BATCH_ITEMS} 组")

    fingerprint = _batch_fingerprint(combinations)
    with _batches_lock:
        existing_id = _fingerprint_index.get(fingerprint)
        if existing_id and existing_id in _batches:
            return _public_batch(_batches[existing_id]) | {"existed": True}

        batch_id = uuid.uuid4().hex[:12]
        # 参数在执行前完成校验：非法组合直接标记失败原因，不进入算法循环
        items = []
        validated = []
        for combo in combinations:
            try:
                norm = validate_params(combo)
                validated.append(norm)
                items.append({"index": len(items), "params": norm, "status": "pending"})
            except OptimizeError as exc:
                validated.append(combo)
                items.append({"index": len(items), "params": dict(combo),
                              "status": "failed", "error": str(exc), "durationMs": 0})

        batch = {
            "id": batch_id,
            "status": "running",
            "createdAt": time.time(),
            "finishedAt": None,
            "fingerprint": fingerprint,
            "items": items,
            "summary": {"total": len(items), "succeeded": 0, "failed": 0, "converged": 0},
        }
        _batches[batch_id] = batch
        _fingerprint_index[fingerprint] = batch_id

    thread = threading.Thread(target=_run_batch, args=(batch_id, validated), daemon=True)
    thread.start()
    return _public_batch(batch) | {"existed": False}


@app.get("/api/batches")
def list_batches():
    with _batches_lock:
        return [_public_batch(b) for b in sorted(_batches.values(), key=lambda b: b["createdAt"], reverse=True)]


@app.get("/api/batches/{batch_id}")
def get_batch(batch_id: str):
    with _batches_lock:
        batch = _batches.get(batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="批量任务不存在或已被删除")
        return _public_batch(batch)


@app.delete("/api/batches/{batch_id}")
def delete_batch(batch_id: str):
    with _batches_lock:
        batch = _batches.pop(batch_id, None)
        if batch is None:
            raise HTTPException(status_code=404, detail="批量任务不存在或已被删除")
        _fingerprint_index.pop(batch["fingerprint"], None)
    return {"ok": True}
