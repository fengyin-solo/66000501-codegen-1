import math
import random
import numpy as np
from fastapi import FastAPI
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


@app.post("/api/optimize")
def optimize(req: OptimizationRequest):
    fn = FUNCTIONS.get(req.functionId, FUNCTIONS["rosenbrock"])
    grad_fn = GRADIENTS.get(req.functionId)
    g_fn = grad_fn if grad_fn else (lambda x, y: np.array([
        (fn(x + 1e-5, y) - fn(x - 1e-5, y)) / 2e-5,
        (fn(x, y + 1e-5) - fn(x, y - 1e-5)) / 2e-5
    ]))

    x, y = req.x0, req.y0
    path = [{"step": 0, "x": x, "y": y, "z": fn(x, y)}]

    if req.algorithm == "gradient_descent":
        vx, vy = 0.0, 0.0
        for i in range(req.iterations):
            g = g_fn(x, y)
            vx = req.momentum * vx - req.learningRate * g[0]
            vy = req.momentum * vy - req.learningRate * g[1]
            x += vx; y += vy
            path.append({"step": i + 1, "x": x, "y": y, "z": fn(x, y)})

    elif req.algorithm == "newton":
        hess_fn = HESSIANS.get(req.functionId)
        if hess_fn is None:
            # fallback to gradient descent
            for i in range(req.iterations):
                g = g_fn(x, y)
                x -= req.learningRate * g[0]
                y -= req.learningRate * g[1]
                path.append({"step": i + 1, "x": x, "y": y, "z": fn(x, y)})
        else:
            for i in range(req.iterations):
                g = g_fn(x, y)
                H = hess_fn(x, y)
                try:
                    dx = np.linalg.solve(H, -g)
                except np.linalg.LinAlgError:
                    dx = -g * req.learningRate
                x += dx[0]; y += dx[1]
                path.append({"step": i + 1, "x": x, "y": y, "z": fn(x, y)})

    elif req.algorithm == "conjugate_gradient":
        g = g_fn(x, y)
        d = -g.copy()
        for i in range(req.iterations):
            # Line search (simple)
            alpha = req.learningRate
            x_new = x + alpha * d[0]
            y_new = y + alpha * d[1]
            g_new = g_fn(x_new, y_new)
            beta = max(0, (g_new @ g_new) / (g @ g + 1e-10))
            d = -g_new + beta * d
            x, y, g = x_new, y_new, g_new
            path.append({"step": i + 1, "x": x, "y": y, "z": fn(x, y)})

    elif req.algorithm == "simulated_annealing":
        T = req.temperature
        best_x, best_y = x, y
        best_z = fn(x, y)
        for i in range(req.iterations):
            nx = x + random.gauss(0, T / req.temperature * 2)
            ny = y + random.gauss(0, T / req.temperature * 2)
            nz = fn(nx, ny)
            delta = nz - fn(x, y)
            if delta < 0 or random.random() < math.exp(-delta / max(T, 1e-5)):
                x, y = nx, ny
                if fn(x, y) < best_z:
                    best_x, best_y = x, y
                    best_z = fn(x, y)
            T *= req.coolingRate
            path.append({"step": i + 1, "x": x, "y": y, "z": fn(x, y)})

    final = path[-1]
    return {
        "params": req.model_dump(),
        "path": path,
        "finalPoint": [final["x"], final["y"]],
        "finalValue": final["z"],
        "iterations": len(path) - 1,
        "converged": abs(final["z"]) < 1e-3 or len(path) >= req.iterations
    }